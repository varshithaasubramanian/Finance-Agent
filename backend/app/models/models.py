"""
SQLAlchemy ORM models for the AI Personal Finance & Budget Agent.

Core entities: User, Budget, Category, Expense, RecurringExpense,
FinancialGoal, AIInsight.

Monetary columns use Numeric(12, 2) so that values round-trip through the
database without floating point drift. All monetary arithmetic in the
service layer is performed with Python's Decimal type.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class PaymentMethod(str, enum.Enum):
    CASH = "Cash"
    UPI = "UPI"
    DEBIT_CARD = "Debit Card"
    CREDIT_CARD = "Credit Card"
    BANK_TRANSFER = "Bank Transfer"
    OTHER = "Other"


class RecurrenceFrequency(str, enum.Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), default="Demo User")
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    currency_symbol: Mapped[str] = mapped_column(String(4), default="\u20b9")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    budgets: Mapped[list["Budget"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    goals: Mapped[list["FinancialGoal"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Budget(Base):
    """A monthly budget envelope for a given user/period, e.g. 2026-08."""

    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "period", name="uq_budget_user_period"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    period: Mapped[str] = mapped_column(String(7))  # "YYYY-MM"
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    allow_over_allocation: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="budgets")
    categories: Mapped[list["Category"]] = relationship(back_populates="budget", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_category_budget_name"),
        Index("ix_category_budget_id", "budget_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    budget_id: Mapped[str] = mapped_column(String(32), ForeignKey("budgets.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    allocation: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    spending_limit: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    color: Mapped[str] = mapped_column(String(16), default="#0F766E")
    icon: Mapped[str] = mapped_column(String(32), default="wallet")
    is_travel: Mapped[bool] = mapped_column(Boolean, default=False)
    fixed_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # e.g. bus pass
    estimated_daily_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    budget: Mapped["Budget"] = relationship(back_populates="categories")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expense_category_id", "category_id"),
        Index("ix_expense_date", "date"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    budget_id: Mapped[str] = mapped_column(String(32), ForeignKey("budgets.id"), index=True)
    category_id: Mapped[str] = mapped_column(String(32), ForeignKey("categories.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    description: Mapped[str] = mapped_column(String(255), default="")
    date: Mapped[datetime] = mapped_column(Date)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.OTHER)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_ai_entered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped["Category"] = relationship(back_populates="expenses")


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    budget_id: Mapped[str] = mapped_column(String(32), ForeignKey("budgets.id"), index=True)
    category_id: Mapped[str] = mapped_column(String(32), ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    frequency: Mapped[RecurrenceFrequency] = mapped_column(Enum(RecurrenceFrequency))
    next_due_date: Mapped[datetime] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped["Category"] = relationship()


class FinancialGoal(Base):
    __tablename__ = "financial_goals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    current_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    deadline: Mapped[datetime] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="goals")


class AIInsight(Base):
    """Persisted AI/deterministic insights so the dashboard has history."""

    __tablename__ = "ai_insights"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    budget_id: Mapped[str] = mapped_column(String(32), ForeignKey("budgets.id"), index=True)
    category: Mapped[str] = mapped_column(String(80), default="general")
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), default=AlertSeverity.INFO)
    message: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), default="rules")  # "rules" | "ai"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
