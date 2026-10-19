"""Middleware ін'єкції асинхронної сесії БД у хендлери."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    """Інжектує асинхронну сесію БД у контекст обробки оновлення.

    Args:
        session_factory: Фабрика асинхронних сесій SQLAlchemy.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Обгортає виклик хендлера, керуючи життєвим циклом сесії.

        Args:
            handler: Наступний обробник у ланцюжку middleware.
            event: Вхідне оновлення Telegram.
            data: Словник контексту, що передається хендлеру.

        Returns:
            Any: Результат виконання хендлера.
        """
        async with self._session_factory() as session:
            data["session"] = session
            return await handler(event, data)
