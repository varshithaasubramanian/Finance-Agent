"""
Pydantic schemas: request/response contracts for the API and structured
output contracts for the AI layer (NL expense parsing, assistant tool
calls).
"""
import datetime as dt
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class PaymentMethodEnum(str, Enum):
    CASH = "Cash"
    UPI = "UPI"
    DEBIT_CARD = "Debit Card"
    CREDIT_CARD = "Credit Card"
    BANK_TRANSFER = "Bank Transfer"
    OTHER = "Other"


class RecurrenceFrequencyEnum(str, Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


class SeverityEnum(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------- Category
class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    allocation: float = Field(ge=0)
    spending_limit: Optional[float] = Field(default=None, ge=0)
    color: str = "#0F766E"
    icon: str = "wallet"
    is_travel: bool = False
    fixed_amount: float = 0
    estimated_daily_amount: Optional[float] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    allocation: Optional[float] = Field(default=None, ge=0)
    spending_limit: Optional[float] = Field(default=None, ge=0)
    color: Optional[str] = None
    icon: Optional[str] = None
    is_travel: Optional[bool] = None
    fixed_amount: Optional[float] = None
    estimated_daily_amount: Optional[float] = None


class CategoryOut(CategoryBase):
    id: str
    budget_id: str
    spent: float = 0
    remaining: float = 0
    percent_used: float = 0
    daily_allowance: float = 0

    class Config:
        from_attributes = True


# ------------------------------------------------------------------ Budget
class BudgetCreate(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")
    total_amount: float = Field(ge=0)
    allow_over_allocation: bool = False
    categories: list[CategoryCreate] = Field(default_factory=list)


class BudgetUpdate(BaseModel):
    total_amount: Optional[float] = Field(default=None, ge=0)
    allow_over_allocation: Optional[bool] = None


class BudgetOut(BaseModel):
    id: str
    period: str
    total_amount: float
    allow_over_allocation: bool
    currency_symbol: str = "\u20b9"
    categories: list[CategoryOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ----------------------------------------------------------------- Expense
class ExpenseCreate(BaseModel):
    amount: float = Field(gt=0)
    category_id: str
    description: str = ""
    date: dt.date
    payment_method: PaymentMethodEnum = PaymentMethodEnum.OTHER
    notes: str = ""
    is_ai_entered: bool = False


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    category_id: Optional[str] = None
    description: Optional[str] = None
    date: Optional[dt.date] = None
    payment_method: Optional[PaymentMethodEnum] = None
    notes: Optional[str] = None


class ExpenseOut(BaseModel):
    id: str
    budget_id: str
    category_id: str
    category_name: str = ""
    amount: float
    description: str
    date: dt.date
    payment_method: PaymentMethodEnum
    notes: str
    is_ai_entered: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ExpenseFilter(BaseModel):
    category_id: Optional[str] = None
    search: Optional[str] = None
    date_from: Optional[dt.date] = None
    date_to: Optional[dt.date] = None
    payment_method: Optional[PaymentMethodEnum] = None
    sort_by: Literal["date", "amount", "category"] = "date"
    sort_dir: Literal["asc", "desc"] = "desc"


# -------------------------------------------------------- Recurring Expense
class RecurringExpenseCreate(BaseModel):
    category_id: str
    name: str
    amount: float = Field(gt=0)
    frequency: RecurrenceFrequencyEnum
    next_due_date: dt.date


class RecurringExpenseOut(BaseModel):
    id: str
    budget_id: str
    category_id: str
    category_name: str = ""
    name: str
    amount: float
    frequency: RecurrenceFrequencyEnum
    next_due_date: dt.date
    active: bool

    class Config:
        from_attributes = True


# ------------------------------------------------------------------- Goals
class FinancialGoalCreate(BaseModel):
    name: str
    target_amount: float = Field(gt=0)
    current_amount: float = Field(default=0, ge=0)
    deadline: dt.date


class FinancialGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    deadline: Optional[dt.date] = None


class FinancialGoalOut(BaseModel):
    id: str
    name: str
    target_amount: float
    current_amount: float
    deadline: dt.date
    remaining_amount: float = 0
    days_left: int = 0
    required_daily_saving: float = 0
    required_weekly_saving: float = 0

    class Config:
        from_attributes = True


# --------------------------------------------------------------- Analytics
class CategoryAnalytics(BaseModel):
    category_id: str
    name: str
    allocation: float
    spent: float
    remaining: float
    percent_used: float
    daily_average: float
    projected_spending: float
    projected_surplus_deficit: float
    color: str
    icon: str


class TravelAnalytics(BaseModel):
    travel_budget: float
    travel_spent: float
    travel_remaining: float
    fixed_travel_expenses: float
    variable_travel_budget: float
    variable_travel_remaining: float
    recommended_daily_spending: float
    estimated_daily_travel: Optional[float] = None
    expected_cost_remaining_days: Optional[float] = None
    budget_sufficient: Optional[bool] = None
    expected_exhaustion_date: Optional[dt.date] = None
    required_daily_reduction: Optional[float] = None


class BudgetSummary(BaseModel):
    period: str
    total_budget: float
    total_spent: float
    total_remaining: float
    percent_used: float
    days_elapsed: int
    days_remaining: int
    total_days: int
    daily_average_spending: float
    recommended_safe_daily_spending: float
    projected_monthly_spending: float
    projected_surplus_deficit: float
    categories: list[CategoryAnalytics]
    currency_symbol: str = "\u20b9"


class SpendingTrendPoint(BaseModel):
    date: dt.date
    amount: float
    cumulative: float


class ForecastOut(BaseModel):
    method: str
    explanation: str
    projected_monthly_spending: float
    projected_surplus_deficit: float
    category_forecasts: list[dict]
    expected_exhaustion_date: Optional[dt.date] = None


class AlertOut(BaseModel):
    severity: SeverityEnum
    category: str
    message: str
    metric: Optional[dict] = None


# ------------------------------------------------------------- Affordability
class AffordabilityRequest(BaseModel):
    amount: float = Field(gt=0)
    category_id: Optional[str] = None
    description: str = ""


class AffordabilityResponse(BaseModel):
    verdict: Literal["Yes", "No", "Caution"]
    amount: float
    remaining_total_after: float
    category_name: Optional[str] = None
    category_remaining_before: Optional[float] = None
    category_remaining_after: Optional[float] = None
    recommended_spending_limit: float
    explanation: str


# --------------------------------------------------------------- NL Parsing
class ParsedExpense(BaseModel):
    amount: float = Field(gt=0)
    category: str
    description: str
    date: str  # ISO date string, resolved from relative terms like "today"/"yesterday"
    payment_method: Optional[PaymentMethodEnum] = None
    confidence: float = Field(ge=0, le=1, default=0.6)
    source: Literal["ai", "fallback"] = "fallback"


class NLParseRequest(BaseModel):
    text: str = Field(min_length=1)


# ----------------------------------------------------------------- Assistant
class AssistantRequest(BaseModel):
    message: str = Field(min_length=1)


class AssistantResponse(BaseModel):
    reply: str
    source: Literal["ai", "fallback"]
    tool_calls: list[dict] = Field(default_factory=list)


class InsightOut(BaseModel):
    id: str
    category: str
    severity: SeverityEnum
    message: str
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# -------------------------------------------------------------------- Auth
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    currency: str
    currency_symbol: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut