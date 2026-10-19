"""Сервіс обробки витрат та транзакцій з базою даних."""

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.receipt import Expense, Receipt
from src.db.models.user import ensure_user_exists


class ExpenseService:
    """Інкапсулює операції створення витрат у межах транзакцій."""

    @staticmethod
    async def create_expense(
        session: AsyncSession,
        *,
        user_id: int,
        file_id: str,
        amount: Decimal,
        category: str,
        description: str | None = None,
        file_name: str | None = None,
        expense_date: date | None = None,
    ) -> Expense:
        """Створює чек та пов'язану витрату в єдиній транзакції.

        Args:
            session: Активна асинхронна сесія БД.
            user_id: Ідентифікатор користувача-власника.
            file_id: Ідентифікатор файлу чека в Telegram.
            amount: Сума витрати.
            category: Категорія витрати.
            description: Необов'язковий опис витрати.
            file_name: Необов'язкова назва файлу.
            expense_date: Дата здійснення витрати (``None`` — поточна дата).

        Returns:
            Expense: Збережена сутність витрати.

        Raises:
            ValueError: Якщо сума менша або дорівнює нулю.
        """
        if amount <= 0:
            raise ValueError("Сума витрати має бути додатною")

        # Гарантуємо наявність користувача, аби уникнути ForeignKeyViolation
        # при створенні чеку (наприклад, якщо користувач не запускав /start).
        await ensure_user_exists(session, user_id)

        receipt = Receipt(user_id=user_id, file_id=file_id, file_name=file_name)
        session.add(receipt)
        await session.flush()  # Отримуємо receipt.id до створення витрати.

        expense = Expense(
            receipt_id=receipt.id,
            amount=amount,
            category=category,
            description=description,
        )
        if expense_date is not None:
            expense.expense_date = expense_date
        session.add(expense)
        await session.commit()
        return expense
