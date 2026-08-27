"""
Tool functions exposed to the AI assistant via Anthropic tool use / function
calling. Every tool is a thin wrapper around the deterministic calculation
engine (app.services.analytics_service, forecast_service, etc.) -- the AI
NEVER computes a financial number itself, it only calls these tools and
narrates the result. This directly implements the "single source of truth"
requirement.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.services import (
    affordability_service,
    analytics_service,
    expense_service,
    forecast_service,
)


def _find_category(budget: models.Budget, name: str) -> models.Category | None:
    name_lower = name.strip().lower()
    for c in budget.categories:
        if c.name.lower() == name_lower:
            return c
    # fuzzy: partial match
    for c in budget.categories:
        if name_lower in c.name.lower() or c.name.lower() in name_lower:
            return c
    return None


def get_current_budget(db: Session, budget: models.Budget, **_) -> dict:
    summary = analytics_service.compute_budget_summary(db, budget)
    return summary.model_dump(mode="json")


def get_category_budget(db: Session, budget: models.Budget, category: str, **_) -> dict:
    cat = _find_category(budget, category)
    if not cat:
        return {"error": f"No category named '{category}' found. Available: {[c.name for c in budget.categories]}"}
    analytics = analytics_service.compute_category_analytics(db, budget, cat)
    return analytics.model_dump(mode="json")


def get_total_spending(db: Session, budget: models.Budget, **_) -> dict:
    summary = analytics_service.compute_budget_summary(db, budget)
    return {"total_spent": summary.total_spent, "currency_symbol": summary.currency_symbol}


def get_category_spending(db: Session, budget: models.Budget, category: str, **_) -> dict:
    return get_category_budget(db, budget, category)


def get_remaining_budget(db: Session, budget: models.Budget, **_) -> dict:
    summary = analytics_service.compute_budget_summary(db, budget)
    return {"total_remaining": summary.total_remaining, "currency_symbol": summary.currency_symbol}


def get_remaining_days(db: Session, budget: models.Budget, **_) -> dict:
    summary = analytics_service.compute_budget_summary(db, budget)
    return {"days_remaining": summary.days_remaining, "days_elapsed": summary.days_elapsed, "total_days": summary.total_days}


def get_daily_allowance(db: Session, budget: models.Budget, **_) -> dict:
    summary = analytics_service.compute_budget_summary(db, budget)
    return {
        "recommended_safe_daily_spending": summary.recommended_safe_daily_spending,
        "currency_symbol": summary.currency_symbol,
    }


def get_spending_trends(db: Session, budget: models.Budget, **_) -> dict:
    trends = analytics_service.spending_trends(db, budget)
    # Keep payload small for the model: last 14 points
    recent = trends[-14:]
    return {"trend": [t.model_dump(mode="json") for t in recent]}


def get_projected_spending(db: Session, budget: models.Budget, **_) -> dict:
    forecast = forecast_service.generate_forecast(db, budget)
    return forecast.model_dump(mode="json")


def get_recent_expenses(db: Session, budget: models.Budget, limit: int = 5, **_) -> dict:
    expenses = expense_service.get_recent_expenses(db, budget.id, limit=limit)
    return {
        "expenses": [
            {
                "amount": float(e.amount),
                "category": e.category.name if e.category else "",
                "description": e.description,
                "date": e.date.isoformat(),
                "payment_method": e.payment_method.value,
            }
            for e in expenses
        ]
    }


def calculate_affordability(db: Session, budget: models.Budget, amount: float, category: str | None = None, **_) -> dict:
    category_id = None
    if category:
        cat = _find_category(budget, category)
        category_id = cat.id if cat else None
    result = affordability_service.evaluate_affordability(db, budget, amount=amount, category_id=category_id)
    return result.model_dump(mode="json")


def create_expense_tool(db: Session, budget: models.Budget, amount: float, category: str, description: str = "", date_str: str | None = None, **_) -> dict:
    cat = _find_category(budget, category)
    if not cat:
        return {"error": f"No category named '{category}' found."}
    expense_date = date.fromisoformat(date_str) if date_str else date.today()
    expense = expense_service.create_expense(
        db,
        budget,
        schemas.ExpenseCreate(
            amount=amount,
            category_id=cat.id,
            description=description,
            date=expense_date,
            is_ai_entered=True,
        ),
    )
    return {"created": True, "expense_id": expense.id, "amount": float(expense.amount), "category": cat.name}


TOOL_FUNCTIONS = {
    "get_current_budget": get_current_budget,
    "get_category_budget": get_category_budget,
    "get_total_spending": get_total_spending,
    "get_category_spending": get_category_spending,
    "get_remaining_budget": get_remaining_budget,
    "get_remaining_days": get_remaining_days,
    "get_daily_allowance": get_daily_allowance,
    "get_spending_trends": get_spending_trends,
    "get_projected_spending": get_projected_spending,
    "get_recent_expenses": get_recent_expenses,
    "calculate_affordability": calculate_affordability,
    "create_expense": create_expense_tool,
}


ANTHROPIC_TOOL_SCHEMAS = [
    {
        "name": "get_current_budget",
        "description": "Get the full current budget summary: total budget, spent, remaining, percent used, days elapsed/remaining, daily averages, projections, and per-category breakdown.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_category_budget",
        "description": "Get detailed budget analytics for one specific category by name (e.g. 'Food', 'Travel').",
        "input_schema": {
            "type": "object",
            "properties": {"category": {"type": "string", "description": "Category name"}},
            "required": ["category"],
        },
    },
    {
        "name": "get_total_spending",
        "description": "Get the total amount spent so far this period across all categories.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_category_spending",
        "description": "Get how much has been spent in one specific category.",
        "input_schema": {
            "type": "object",
            "properties": {"category": {"type": "string"}},
            "required": ["category"],
        },
    },
    {
        "name": "get_remaining_budget",
        "description": "Get the total remaining budget for the period.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_remaining_days",
        "description": "Get how many days remain, have elapsed, and total days in the current budget period.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_daily_allowance",
        "description": "Get the recommended safe daily spending amount for the rest of the period.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_spending_trends",
        "description": "Get the recent day-by-day spending trend (amount per day and cumulative total).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_projected_spending",
        "description": "Get the forecasted end-of-month spending, projected surplus/deficit, and per-category forecasts, with an explanation of the method used.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_expenses",
        "description": "Get the most recent expenses (default 5).",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Number of expenses to return"}},
        },
    },
    {
        "name": "calculate_affordability",
        "description": "Determine whether the user can afford to spend a given amount, optionally in a specific category. Returns a Yes/No/Caution verdict with explanation. Use this for any 'can I afford / can I spend' question.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "The amount the user wants to spend"},
                "category": {"type": "string", "description": "Optional category name"},
            },
            "required": ["amount"],
        },
    },
    {
        "name": "create_expense",
        "description": "Log a new expense on the user's behalf. Only call this if the user explicitly confirms they want to record/add/log an expense.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "category": {"type": "string"},
                "description": {"type": "string"},
                "date_str": {"type": "string", "description": "ISO date YYYY-MM-DD, defaults to today"},
            },
            "required": ["amount", "category"],
        },
    },
]
