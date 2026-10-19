"""Unit-тести сервісу оптичного розпізнавання (OCR).

Архітектурна роль:
    - перевіряє парсинг та нормалізацію результатів ``OcrService``;
    - покриває чисті (pure) функції без мережевих викликів та LLM.

Примітка: тести не вимагають реального підключення до OpenRouter чи Telegram.
"""

import unittest
from decimal import Decimal

from src.services.ocr_service import _clean_str, _to_decimal, OcrService


class TestToDecimal(unittest.TestCase):
    """Тести безпечного перетворення значень на ``Decimal``."""

    def test_none_returns_zero(self) -> None:
        """``None`` повертає нульову суму."""
        self.assertEqual(_to_decimal(None), Decimal("0.00"))

    def test_float(self) -> None:
        """Дробове число округлюється до копійок."""
        self.assertEqual(_to_decimal(123.456), Decimal("123.46"))

    def test_string(self) -> None:
        """Рядкове число коректно конвертується."""
        self.assertEqual(_to_decimal("42.5"), Decimal("42.50"))

    def test_invalid_returns_zero(self) -> None:
        """Некоректне значення повертає нуль без виключення."""
        self.assertEqual(_to_decimal("not-a-number"), Decimal("0.00"))


class TestCleanStr(unittest.TestCase):
    """Тести нормалізації рядкових значень."""

    def test_none(self) -> None:
        """``None`` лишається ``None``."""
        self.assertIsNone(_clean_str(None))

    def test_strip(self) -> None:
        """Рядок обрізається від зайвих пробілів."""
        self.assertEqual(_clean_str("  Магазин  "), "Магазин")

    def test_empty_returns_none(self) -> None:
        """Порожній рядок стає ``None``."""
        self.assertIsNone(_clean_str("   "))


class TestParseResponse(unittest.TestCase):
    """Тести парсингу JSON-відповіді LLM."""

    def test_valid_json(self) -> None:
        """Валідний JSON коректно розбирається."""
        result = OcrService._parse_response(
            '{"amount": 10.5, "merchant": "АТБ", "category": "Продукти"}'
        )
        self.assertEqual(result["amount"], Decimal("10.50"))
        self.assertEqual(result["merchant"], "АТБ")
        self.assertEqual(result["category"], "Продукти")

    def test_broken_json_returns_fallback(self) -> None:
        """Пошкоджений JSON повертає fallback без виключення."""
        result = OcrService._parse_response("not json at all")
        self.assertEqual(result["amount"], Decimal("0.00"))
        self.assertIsNone(result["merchant"])
        self.assertIsNone(result["category"])


class TestFallback(unittest.TestCase):
    """Тести fallback-результату OCR."""

    def test_fallback_fields(self) -> None:
        """Fallback повертає нульову суму та порожні поля."""
        result = OcrService._fallback()
        self.assertEqual(result["amount"], Decimal("0.00"))
        self.assertIsNone(result["merchant"])
        self.assertIsNone(result["category"])


if __name__ == "__main__":
    unittest.main()
