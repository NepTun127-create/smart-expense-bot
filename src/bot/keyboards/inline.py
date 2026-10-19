"""Фабрика inline-клавіатури вибору категорій витрат."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Відображення «ключ категорії» -> «підпис кнопки». У БД зберігається лише
# чистий ключ (без емодзі), а смайли використовуються тільки для відображення.
CATEGORIES: dict[str, str] = {
    "Їжа": "🍔 Їжа",
    "Транспорт": "🚗 Транспорт",
    "Житло": "🏠 Житло",
    "Розваги": "🎮 Розваги",
    "Інше": "🛒 Інше",
}


def category_keyboard() -> InlineKeyboardMarkup:
    """Створює inline-клавіатуру вибору категорії.

    Returns:
        InlineKeyboardMarkup: Клавіатура, де ``callback_data`` містить
            чистий ключ категорії (без емодзі).
    """
    builder = InlineKeyboardBuilder()
    for key, label in CATEGORIES.items():
        builder.button(text=label, callback_data=f"category:{key}")
    builder.adjust(2)
    return builder.as_markup()
