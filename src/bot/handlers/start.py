"""Обробники команд /start та /help."""

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.reply import main_menu_keyboard
from src.db.models.user import ensure_user_exists

start_router = Router(name="start")


@start_router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """Обробляє команду /start: реєструє користувача та показує меню.

    Args:
        message: Вхідне повідомлення від користувача.
        session: Асинхронна сесія БД, інжектована middleware.
    """
    user = message.from_user
    name = user.first_name if user else "користувачу"

    if user is not None:
        await ensure_user_exists(
            session,
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
        )

    await message.answer(
        f"Вітаю, {name}! 👋\n"
        "Я допоможу відстежувати витрати.\n"
        "Надішліть фото або PDF чека, і я розпізнаю суми автоматично.",
        reply_markup=main_menu_keyboard(),
    )


@start_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обробляє команду /help: надає коротку довідку.

    Args:
        message: Вхідне повідомлення від користувача.
    """
    await message.answer(
        "📖 Довідка:\n"
        "• Надішліть фото або PDF чека — я розпізнаю суму та категорію.\n"
        "• Скористайтеся кнопками меню для статистики витрат.",
        reply_markup=main_menu_keyboard(),
    )
