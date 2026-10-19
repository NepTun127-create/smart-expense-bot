"""ORM-моделі чека (``Receipt``) та витрати (``Expense``)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Receipt(Base):
    """Метадані завантаженого чека.

    Attributes:
        id: Первинний ключ чека.
        user_id: Зовнішній ключ на ``users.telegram_id`` користувача-власника.
        file_id: Ідентифікатор файлу в Telegram.
        file_name: Оригінальна назва файлу (для PDF).
        created_at: Часова мітка завантаження.
        expenses: Зв'язок з витратами, отриманими з цього чека.
    """

    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_id: Mapped[str] = mapped_column(String(256), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="receipts")  # noqa: F821
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class Expense(Base):
    """Нормалізована витрата, отримана з чека.

    Attributes:
        id: Первинний ключ витрати.
        receipt_id: Зовнішній ключ пов'язаного чека.
        amount: Сума витрати (з двома знаками після коми).
        category: Категорія витрати.
        expense_date: Дата здійснення витрати.
        description: Необов'язковий опис.
        created_at: Часова мітка створення запису.
    """

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("receipts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expense_date: Mapped[date] = mapped_column(
        Date,
        default=lambda: datetime.now(timezone.utc).date(),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    receipt: Mapped["Receipt"] = relationship(back_populates="expenses")  # noqa: F821
