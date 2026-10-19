"""Ініціалізація асинхронного рушія та фабрики сесій бази даних."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.db_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    """Надає асинхронну сесію як dependency-генератор.

    Yields:
        AsyncSession: Активна сесія, що закривається після використання.
    """
    async with async_session_maker() as session:
        yield session
