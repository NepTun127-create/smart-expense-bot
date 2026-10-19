"""Гібридний OCR чеків: pdfplumber для цифрових PDF і Vision-LLM для фото.

За відсутності API-ключа або при помилках повертає fallback
(``amount=0.00``), щоб хендлер запропонував ручне введення.
"""

import base64
import io
import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, TypedDict

import pdfplumber
from aiogram import Bot
from json_repair import repair_json
from openai import AsyncOpenAI
from pdf2image import convert_from_bytes
from PIL import Image

from src.config import get_settings

logger = logging.getLogger(__name__)

# Максимальна довжина сторони зображення (px) для захисту від OOM.
_MAX_IMAGE_SIDE = 3000

# Системний промпт для Vision-LLM моделі.
_SYSTEM_PROMPT = (
    "You are an expert receipt parser. Analyze this receipt image/text. "
    "Extract the total purchase amount (Numeric float), merchant name (string), "
    "and suggested expense category (e.g. 'Продукти', 'Транспорт', 'Кафе', "
    "'Розваги', 'Електроніка', 'Інше'). Return STRICTLY valid JSON with no "
    'markdown block markers: {"amount": float or null, '
    '"merchant": string or null, "category": string or null}.'
)


class ReceiptParseResult(TypedDict):
    """Типізований результат розпізнавання чека.

    Attributes:
        amount: Загальна сума покупки (``0.00`` у разі помилки розпізнавання).
        merchant: Назва магазину (або ``None``).
        category: Запропонована категорія витрати (або ``None``).
    """

    amount: Decimal
    merchant: str | None
    category: str | None


class OcrService:
    """Фасад гібридного OCR: PDF-текст + Vision-LLM через OpenRouter.

    Інкапсулює весь життєвий цикл розпізнавання чека: завантаження файлу,
    підготовку контенту (текст/зображення), виклик LLM та нормалізацію
    результату. Клієнт OpenRouter кешується на рівні класу.
    """

    _client: AsyncOpenAI | None = None

    @classmethod
    def _get_client(cls) -> AsyncOpenAI:
        """Повертає закешований асинхронний клієнт OpenAI (OpenRouter).

        Returns:
            AsyncOpenAI: Клієнт, налаштований на OpenRouter base URL.
        """
        if cls._client is None:
            settings = get_settings()
            cls._client = AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
            )
        return cls._client

    @classmethod
    async def process_receipt(
        cls,
        bot: Bot,
        file_id: str,
        is_photo: bool,
    ) -> ReceiptParseResult:
        """Розпізнає чек: завантажує файл, витягує контент, звертається до LLM.

        Args:
            bot: Екземпляр бота для завантаження файлу з Telegram.
            file_id: Ідентифікатор файлу або фото в Telegram.
            is_photo: ``True`` для фото, ``False`` для PDF-документа.

        Returns:
            ReceiptParseResult: Розпізнані сума, магазин та категорія.
        """
        settings = get_settings()
        if not settings.openrouter_api_key:
            logger.warning("OpenRouter API-ключ відсутній — повертаю fallback.")
            return cls._fallback()

        try:
            raw_bytes = await cls._download_file(bot, file_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Не вдалося завантажити файл %s: %s", file_id, exc)
            return cls._fallback()

        text: str | None = None
        image_data_url: str | None = None

        if is_photo:
            image_data_url = cls._bytes_to_jpeg_data_url(raw_bytes)
        else:
            text = cls._extract_pdf_text(raw_bytes)
            if not text:
                logger.info("PDF без текстового шару — конвертую у зображення.")
                try:
                    jpeg_bytes = cls._pdf_first_page_to_jpeg(raw_bytes)
                    image_data_url = cls._bytes_to_jpeg_data_url(jpeg_bytes)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Не вдалося конвертувати PDF: %s", exc)

        if image_data_url is None and text is None:
            logger.warning("Не вдалося видобути контент із чека.")
            return cls._fallback()

        try:
            raw_response = await cls._call_llm(
                text=text,
                image_data_url=image_data_url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Помилка OpenRouter/LLM: %s", exc)
            return cls._fallback()

        return cls._parse_response(raw_response)

    # ------------------------------------------------------------------
    # Внутрішні допоміжні методи
    # ------------------------------------------------------------------
    @staticmethod
    async def _download_file(bot: Bot, file_id: str) -> bytes:
        """Завантажує файл із Telegram у пам'ять.

        Args:
            bot: Екземпляр бота.
            file_id: Ідентифікатор файлу.

        Returns:
            bytes: Вміст завантаженого файлу.

        Raises:
            ValueError: Якщо у файлу відсутній шлях для завантаження.
        """
        file = await bot.get_file(file_id)
        if file.file_path is None:
            raise ValueError(f"Файл {file_id} не має шляху для завантаження")
        downloaded = await bot.download_file(file.file_path)
        return downloaded.read()

    @staticmethod
    def _extract_pdf_text(data: bytes) -> str:
        """Видобуває текст з усіх сторінок PDF через pdfplumber.

        Args:
            data: Байтовий вміст PDF.

        Returns:
            str: Об'єднаний текст (порожній рядок для сканованих PDF).
        """
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages_text).strip()

    @staticmethod
    def _pdf_first_page_to_jpeg(data: bytes) -> bytes:
        """Рендерить першу сторінку PDF у JPEG з обмеженням розміру.

        Args:
            data: Байтовий вміст PDF.

        Returns:
            bytes: JPEG-зображення першої сторінки.

        Raises:
            ValueError: Якщо PDF не містить жодної сторінки.
        """
        images = convert_from_bytes(data, first_page=1, last_page=1, dpi=120)
        if not images:
            raise ValueError("PDF не містить жодної сторінки")
        image = images[0].convert("RGB")
        image.thumbnail((_MAX_IMAGE_SIDE, _MAX_IMAGE_SIDE))
        return OcrService._pil_to_jpeg(image)

    @staticmethod
    def _bytes_to_jpeg_data_url(data: bytes) -> str:
        """Конвертує байти зображення у base64 data URL (JPEG).

        Args:
            data: Байтовий вміст зображення.

        Returns:
            str: Рядок вигляду ``data:image/jpeg;base64,...``.
        """
        image = Image.open(io.BytesIO(data)).convert("RGB")
        image.thumbnail((_MAX_IMAGE_SIDE, _MAX_IMAGE_SIDE))
        jpeg_bytes = OcrService._pil_to_jpeg(image)
        encoded = base64.b64encode(jpeg_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    @staticmethod
    def _pil_to_jpeg(image: Image.Image) -> bytes:
        """Серіалізує PIL-зображення у JPEG.

        Args:
            image: Зображення Pillow.

        Returns:
            bytes: JPEG-байти зображення.
        """
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()

    @classmethod
    async def _call_llm(
        cls,
        *,
        text: str | None = None,
        image_data_url: str | None = None,
    ) -> str:
        """Надсилає запит до Vision-LLM моделі OpenRouter.

        Args:
            text: Попередньо видобутий текст чека (для цифрових PDF).
            image_data_url: Data URL зображення чека (для фото/сканів).

        Returns:
            str: Сирий текстовий вміст відповіді (очікується JSON).
        """
        client = cls._get_client()
        settings = get_settings()

        content: list[dict[str, Any]] = []
        if image_data_url is not None:
            content.append(
                {"type": "image_url", "image_url": {"url": image_data_url}}
            )
        if text:
            content.append(
                {"type": "text", "text": f"Extracted receipt text:\n{text}"}
            )
        if not content:
            content.append(
                {"type": "text", "text": "No receipt content available."}
            )

        response = await client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _parse_response(raw: str) -> ReceiptParseResult:
        """Парсить JSON-відповідь LLM з відновленням через json-repair.

        Args:
            raw: Сира відповідь моделі (може містити пошкоджений JSON).

        Returns:
            ReceiptParseResult: Нормалізований результат розпізнавання.
        """
        try:
            data = json.loads(repair_json(raw))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не вдалося розпарсити відповідь LLM: %s", exc)
            return OcrService._fallback()

        if not isinstance(data, dict):
            logger.warning("Відповідь LLM не є об'єктом JSON: %r", data)
            return OcrService._fallback()

        return {
            "amount": _to_decimal(data.get("amount")),
            "merchant": _clean_str(data.get("merchant")),
            "category": _clean_str(data.get("category")),
        }

    @staticmethod
    def _fallback() -> ReceiptParseResult:
        """Повертає безпечний fallback-результат для ручного введення.

        Returns:
            ReceiptParseResult: Нульова сума та відсутні поля.
        """
        return {"amount": Decimal("0.00"), "merchant": None, "category": None}


def _to_decimal(value: Any) -> Decimal:
    """Безпечно перетворює значення на Decimal з двома десятковими знаками.

    Args:
        value: Число, рядок або ``None``.

    Returns:
        Decimal: Сума з округленням до копійок (``0.00`` у разі помилки).
    """
    if value is None:
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _clean_str(value: Any) -> str | None:
    """Нормалізує рядкове значення з відповіді LLM.

    Args:
        value: Довільне значення.

    Returns:
        str | None: Обрізаний непорожній рядок або ``None``.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None
