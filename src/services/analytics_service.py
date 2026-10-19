"""Сервіс агрегації даних та генерації діаграм для аналітики."""

import io
from decimal import Decimal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from aiogram.types import BufferedInputFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.receipt import Expense, Receipt

# Сучасна м'яка палітра для кругової діаграми.
_PALETTE = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#76B7B2", "#EDC948"]


class AnalyticsService:
    """Обчислює та форматує аналітичні показники витрат."""

    @staticmethod
    async def _category_totals(
        user_id: int, session: AsyncSession
    ) -> list[tuple[str, Decimal]]:
        """Повертає суми витрат, згруповані за категоріями (за спаданням).

        Args:
            user_id: Ідентифікатор користувача (telegram_id).
            session: Активна асинхронна сесія БД.

        Returns:
            list[tuple[str, Decimal]]: Пари «категорія, сума».
        """
        stmt = (
            select(Expense.category, func.sum(Expense.amount).label("total"))
            .join(Receipt, Receipt.id == Expense.receipt_id)
            .where(Receipt.user_id == user_id)
            .group_by(Expense.category)
            .order_by(func.sum(Expense.amount).desc())
        )
        result = await session.execute(stmt)
        return [(category, total) for category, total in result.all()]

    @staticmethod
    async def get_summary(user_id: int, session: AsyncSession) -> str:
        """Повертає текстову зведену статистику витрат користувача.

        Args:
            user_id: Ідентифікатор користувача (telegram_id).
            session: Активна асинхронна сесія БД.

        Returns:
            str: Відформатований текстовий звіт.
        """
        totals = await AnalyticsService._category_totals(user_id, session)
        if not totals:
            return "📊 Поки що немає витрат. Надішліть чек!"

        lines = [f"{category}: {total:.2f} грн" for category, total in totals]
        return "📊 Статистика витрат:\n" + "\n".join(lines)

    @staticmethod
    async def generate_chart(
        user_id: int, session: AsyncSession
    ) -> BufferedInputFile | None:
        """Формує PNG-діаграму витрат за категоріями.

        Args:
            user_id: Ідентифікатор користувача (telegram_id).
            session: Активна асинхронна сесія БД.

        Returns:
            BufferedInputFile | None: Готова до надсилання PNG-діаграма або
            ``None``, якщо витрат ще немає.
        """
        totals = await AnalyticsService._category_totals(user_id, session)
        if not totals:
            return None

        labels = [category for category, _ in totals]
        values = [float(total) for _, total in totals]

        figure, ax = plt.subplots(figsize=(6, 6), dpi=120)
        _, _, autotexts = ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=_PALETTE[: len(labels)],
            pctdistance=0.75,
            textprops={"fontsize": 10},
        )
        for text in autotexts:
            text.set_color("white")
            text.set_fontsize(9)
        ax.axis("equal")

        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", bbox_inches="tight", transparent=True)
        plt.close(figure)
        buffer.seek(0)
        return BufferedInputFile(buffer.read(), filename="expenses_chart.png")
