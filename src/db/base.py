"""Базовий клас декларативних моделей SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовий клас для всіх ORM-моделей застосунку.

    Наслідувачі автоматично реєструються у спільному ``metadata``,
    що використовується під час створення таблиць (див. ``src.main``).
    """
