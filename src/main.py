"""Точка входу застосунку: ініціалізація БД, роутерів та polling."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.handlers.analytics import analytics_router
from src.bot.handlers.receipts import receipts_router
from src.bot.handlers.start import start_router
from src.bot.middlewares.db_session import DbSessionMiddleware
from src.config import get_settings
from src.db.base import Base
from src.db.session import async_session_maker, engine


async def main() -> None:
    """Запускає застосунок: налаштовує бота, БД та polling."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Таблиці бази даних синхронізовано")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())

    # Підключення middleware для ін'єкції сесії БД у хендлери.
    dispatcher.update.middleware(DbSessionMiddleware(async_session_maker))

    # Реєстрація роутерів.
    dispatcher.include_router(start_router)
    dispatcher.include_router(receipts_router)
    dispatcher.include_router(analytics_router)

    logger.info("Бот запущено, розпочинаю polling")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Застосунок зупинено користувачем")
