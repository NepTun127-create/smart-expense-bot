"""Фабрика постійної (reply) клавіатури головного меню."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Створює головне reply-меню з основними діями.

    Returns:
        ReplyKeyboardMarkup: Клавіатура з кнопками «Додати чек» та «Статистика».
    """
    buttons: list[list[KeyboardButton]] = [
        [KeyboardButton(text="🧾 Додати чек")],
        [KeyboardButton(text="📊 Статистика")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію",
    )
