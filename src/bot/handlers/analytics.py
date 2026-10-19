"""Обробники статистики та зведених звітів про витрати."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.analytics_service import AnalyticsService

analytics_router = Router(name="analytics")


async def _send_stats(message: Message, session: AsyncSession) -> None:
    """Надсилає текстовий звіт та (за наявності витрат) діаграму.

    Args:
        message: Вхідне повідомлення.
        session: Асинхронна сесія БД, інжектована middleware.
    """
    if message.from_user is None:
        return

    user_id: int = message.from_user.id
    summary: str = await AnalyticsService.get_summary(user_id, session)
    chart = await AnalyticsService.generate_chart(user_id, session)

    await message.answer(summary)
    if chart is not None:
        await message.answer_photo(chart)


@analytics_router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    """Обробляє команду /stats і показує зведену статистику.

    Args:
        message: Вхідне повідомлення від користувача.
        session: Асинхронна сесія БД, інжектована middleware.
    """
    await _send_stats(message, session)


@analytics_router.message(F.text == "📊 Статистика")
async def handle_stats_button(message: Message, session: AsyncSession) -> None:
    """Обробляє натискання кнопки «Статистика» з reply-клавіатури.

    Args:
        message: Вхідне повідомлення.
        session: Асинхронна сесія БД, інжектована middleware.
    """
    await _send_stats(message, session)
