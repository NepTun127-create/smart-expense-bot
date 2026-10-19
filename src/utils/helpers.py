"""Допоміжні функції парсингу даних."""

import re
from decimal import Decimal, InvalidOperation


def parse_amount(raw: str) -> Decimal | None:
    """Парсить грошову суму з довільного рядка.

    Args:
        raw: Вхідний текст, що може містити суму (наприклад, ``12 345,67``).

    Returns:
        Decimal | None: Числове значення суми або ``None``, якщо не вдалося розпізнати.
    """
    normalized = raw.replace(" ", "").replace(",", ".").replace("\xa0", "")
    match = re.search(r"\d+(?:\.\d{1,2})?", normalized)
    if not match:
        return None
    try:
        return Decimal(match.group())
    except InvalidOperation:
        return None
