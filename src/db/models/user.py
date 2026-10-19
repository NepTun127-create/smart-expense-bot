"""ORM-модель користувача Telegram з ідемпотентним upsert."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class User(Base):
    """Сутність користувача Telegram.

    Attributes:
        telegram_id: Первинний ключ — ідентифікатор користувача в Telegram.
        username: Ім'я користувача (юзернейм) у Telegram.
        full_name: Повне ім'я користувача.
        created_at: Часова мітка створення запису (UTC).
        receipts: Зв'язок з чеками користувача.
    """

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    receipts: Mapped[list["Receipt"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


async def ensure_user_exists(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> None:
    """Гарантує існування користувача у БД (ідемпотентний upsert).

    Якщо передано ``username`` або ``full_name`` — оновлює відповідні поля
    при конфлікті (``ON CONFLICT DO UPDATE``). Якщо профільні дані не
    передано — лише гарантує наявність рядка через ``ON CONFLICT DO NOTHING``,
    не перезаписуючи вже збережені дані.

    Args:
        session: Активна асинхронна сесія БД.
        telegram_id: Ідентифікатор користувача в Telegram (primary key).
        username: Юзернейм користувача (необов'язково).
        full_name: Повне ім'я користувача (необов'язково).
    """
    insert_values: dict[str, Any] = {"telegram_id": telegram_id}
    update_set: dict[str, Any] = {}

    if username is not None:
        insert_values["username"] = username
        update_set["username"] = username

    name: str | None = full_name.strip() if full_name else None
    if name is not None:
        insert_values["full_name"] = name
        update_set["full_name"] = name
    else:
        insert_values["full_name"] = "User"

    stmt = pg_insert(User).values(**insert_values)
    if update_set:
        stmt = stmt.on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_=update_set,
        )
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=[User.telegram_id])

    await session.execute(stmt)
    await session.commit()
