"""Обробники завантаження фото та PDF чеків і вибору категорії."""

from decimal import Decimal
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.inline import category_keyboard
from src.db.models.user import ensure_user_exists
from src.services.expense_service import ExpenseService
from src.services.ocr_service import OcrService
from src.utils.helpers import parse_amount

receipts_router = Router(name="receipts")

# Допустимі MIME-типи PDF-документів.
_PDF_TYPES = {"application/pdf"}


class ReceiptFSM(StatesGroup):
    """Стани обробки чека.

    - ``waiting_for_manual_amount``: очікування ручного введення суми
      (коли OCR не зміг визначити суму).
    - ``waiting_for_category``: очікування вибору категорії витрати.
    """

    waiting_for_category = State()
    waiting_for_manual_amount = State()


@receipts_router.message(F.text == "🧾 Додати чек")
async def handle_add_receipt_prompt(message: Message) -> None:
    """Підказує користувачу надіслати чек у відповідь на кнопку меню.

    Args:
        message: Вхідне повідомлення з текстом кнопки.
    """
    await message.answer(
        "Будь ласка, надішліть фотографію чека або PDF-квитанцію у цей чат."
    )


@receipts_router.message(F.photo)
async def handle_photo_receipt(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """Обробляє надіслану фотографію чека.

    Args:
        message: Вхідне повідомлення з фотографією.
        state: Контекст FSM для збереження проміжних даних.
        bot: Екземпляр бота для завантаження файлу.
        session: Асинхронна сесія БД, інжектована middleware.
    """
    if message.from_user is not None:
        await ensure_user_exists(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

    file_id: str = message.photo[-1].file_id
    await message.answer("🔍 Розпізнаю чек, зачекайте...")

    parsed = await OcrService.process_receipt(
        bot=bot, file_id=file_id, is_photo=True
    )
    await _store_parsed_receipt(
        state,
        message,
        amount=parsed["amount"],
        merchant=parsed["merchant"],
        category=parsed["category"],
        file_id=file_id,
        file_name=None,
    )


@receipts_router.message(F.document)
async def handle_document_receipt(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """Обробляє надісланий PDF-документ чека.

    Args:
        message: Вхідне повідомлення з PDF-документом.
        state: Контекст FSM для збереження проміжних даних.
        bot: Екземпляр бота для завантаження файлу.
        session: Асинхронна сесія БД, інжектована middleware.
    """
    if message.from_user is not None:
        await ensure_user_exists(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

    mime_type: str = message.document.mime_type or ""
    if mime_type not in _PDF_TYPES:
        await message.answer("⚠️ Будь ласка, надішліть PDF-файл.")
        return

    file_id: str = message.document.file_id
    await message.answer("🔍 Розпізнаю PDF, зачекайте...")

    parsed = await OcrService.process_receipt(
        bot=bot, file_id=file_id, is_photo=False
    )
    await _store_parsed_receipt(
        state,
        message,
        amount=parsed["amount"],
        merchant=parsed["merchant"],
        category=parsed["category"],
        file_id=file_id,
        file_name=message.document.file_name,
    )


async def _store_parsed_receipt(
    state: FSMContext,
    message: Message,
    *,
    amount: Decimal,
    merchant: str | None,
    category: str | None,
    file_id: str,
    file_name: str | None,
) -> None:
    """Зберігає розпізнані дані чека та визначає наступний FSM-стан.

    Якщо суму не вдалося визначити (``amount <= 0``), переводить користувача
    у стан ручного введення суми; інакше показує розпізнані деталі та
    запитує вибір категорії.

    Args:
        state: Контекст FSM.
        message: Повідомлення, на яке відповідаємо.
        amount: Розпізнана сума.
        merchant: Назва магазину.
        category: Запропонована категорія.
        file_id: Ідентифікатор файлу в Telegram.
        file_name: Ім'я файлу (для PDF) або ``None``.
    """
    await state.update_data(
        amount=amount,
        merchant=merchant,
        category=category,
        file_id=file_id,
        file_name=file_name,
    )

    if amount <= Decimal("0.00"):
        await state.set_state(ReceiptFSM.waiting_for_manual_amount)
        await message.answer(
            "⚠️ Не вдалося автоматично визначити суму. Будь ласка, "
            "введіть суму покупки вручну (наприклад: 250.50):"
        )
        return

    await state.set_state(ReceiptFSM.waiting_for_category)
    await message.answer(
        f"🔍 Розпізнано чек:\n"
        f"• 💰 Сума: {amount:.2f} грн\n"
        f"• 🏪 Магазин: {merchant or 'Не вказано'}\n\n"
        "Оберіть підтвердження або змініть категорію:",
        reply_markup=category_keyboard(),
    )


@receipts_router.message(ReceiptFSM.waiting_for_manual_amount)
async def handle_manual_amount(message: Message, state: FSMContext) -> None:
    """Обробляє ручне введення суми після невдалого OCR.

    Args:
        message: Повідомлення з введеною користувачем сумою.
        state: Контекст FSM з проміжними даними чека.
    """
    amount: Decimal | None = parse_amount(message.text or "")

    if amount is None or amount <= Decimal("0.00"):
        await message.answer(
            "⚠️ Некоректна сума. Введіть число (наприклад, 150 або 150.50):"
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(ReceiptFSM.waiting_for_category)

    await message.answer(
        f"Сума: {amount:.2f} грн. Тепер оберіть категорію витрати:",
        reply_markup=category_keyboard(),
    )


@receipts_router.callback_query(
    F.data.startswith("category:"),
    ReceiptFSM.waiting_for_category,
)
async def handle_category_selection(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обробляє вибір категорії та зберігає витрату до БД.

    Args:
        callback: Вхідний callback-запит із обраною категорією.
        state: Контекст FSM з проміжними даними чека.
        session: Асинхронна сесія БД, інжектована middleware.
    """
    category: str = callback.data.split(":", maxsplit=1)[1]

    data: dict[str, Any] = await state.get_data()
    amount: Decimal = data["amount"]
    merchant: str | None = data.get("merchant")
    file_id: str = data["file_id"]
    file_name: str | None = data.get("file_name")

    await ExpenseService.create_expense(
        session,
        user_id=callback.from_user.id,
        file_id=file_id,
        amount=amount,
        category=category,
        description=merchant,
        file_name=file_name,
    )

    await state.clear()

    if callback.message is not None:
        await callback.message.edit_text(
            f"✅ Збережено: {amount:.2f} грн (Категорія: {category})"
        )
    await callback.answer()
