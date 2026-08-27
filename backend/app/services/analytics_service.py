"""
The deterministic calculation engine.

This module is the SINGLE SOURCE OF TRUTH for every financial number shown
in the UI or spoken by the AI assistant. The AI layer never invents a
number -- it always calls into this module (directly, or via the tool
functions in app.ai.tools) and simply narrates the result.

All arithmetic is performed with Decimal via app.utils.decimal_utils and
only rounded to float at the very end, right before being placed on a
response schema.
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.utils.date_utils import days_elapsed, days_remaining, period_bounds, total_days_in_period
from app.utils.decimal_utils import D, pct, round2, safe_div


# --------------------------------------------------------------------- raw
def category_spent(db: Session, category_id: str) -> Decimal:
    expenses = db.scalars(select(models.Expense).where(models.Expense.category_id == category_id))
    return sum((D(e.amount) for e in expenses), Decimal("0"))


def budget_total_spent(db: Session, budget: models.Budget) -> Decimal:
    expenses = db.scalars(select(models.Expense).where(models.Expense.budget_id == budget.id))
    return sum((D(e.amount) for e in expenses), Decimal("0"))


def category_expenses(db: Session, category_id: str) -> list[models.Expense]:
    return list(db.scalars(select(models.Expense).where(models.Expense.category_id == category_id)))


# ------------------------------------------------------------- per-category
def compute_category_analytics(db: Session, budget: models.Budget, category: models.Category, as_of: date | None = None) -> schemas.CategoryAnalytics:
    as_of = as_of or date.today()
    spent = category_spent(db, category.id)
    allocation = D(category.allocation)
    remaining = allocation - spent
    elapsed = max(days_elapsed(budget.period, as_of), 1)
    total_days = total_days_in_period(budget.period)

    daily_avg = safe_div(spent, elapsed)
    projected = daily_avg * D(total_days)
    surplus_deficit = allocation - projected

    return schemas.CategoryAnalytics(
        category_id=category.id,
        name=category.name,
        allocation=round2(allocation),
        spent=round2(spent),
        remaining=round2(remaining),
        percent_used=pct(spent, allocation),
        daily_average=round2(daily_avg),
        projected_spending=round2(projected),
        projected_surplus_deficit=round2(surplus_deficit),
        color=category.color,
        icon=category.icon,
    )


# ------------------------------------------------------------- budget-wide
def compute_budget_summary(db: Session, budget: models.Budget, as_of: date | None = None) -> schemas.BudgetSummary:
    as_of = as_of or date.today()
    total_spent = budget_total_spent(db, budget)
    total_budget = D(budget.total_amount)
    total_remaining = total_budget - total_spent

    total_days = total_days_in_period(budget.period)
    elapsed = days_elapsed(budget.period, as_of)
    remaining_days = days_remaining(budget.period, as_of)
    elapsed_for_avg = max(elapsed, 1)

    daily_avg = safe_div(total_spent, elapsed_for_avg)
    # Safe daily spending: what's left divided by what's left of the month.
    # If the period has already ended, avoid dividing by zero.
    safe_daily = safe_div(total_remaining, remaining_days) if remaining_days > 0 else Decimal("0")
    projected = daily_avg * D(total_days)
    surplus_deficit = total_budget - projected

    categories = [compute_category_analytics(db, budget, c, as_of) for c in budget.categories]

    return schemas.BudgetSummary(
        period=budget.period,
        total_budget=round2(total_budget),
        total_spent=round2(total_spent),
        total_remaining=round2(total_remaining),
        percent_used=pct(total_spent, total_budget),
        days_elapsed=elapsed,
        days_remaining=remaining_days,
        total_days=total_days,
        daily_average_spending=round2(daily_avg),
        recommended_safe_daily_spending=round2(safe_daily),
        projected_monthly_spending=round2(projected),
        projected_surplus_deficit=round2(surplus_deficit),
        categories=categories,
        currency_symbol=budget.user.currency_symbol if budget.user else "\u20b9",
    )


def category_out_list(db: Session, budget: models.Budget) -> list[schemas.CategoryOut]:
    """CategoryOut list (used by the /categories endpoint) enriched with
    live spend/remaining/percent/daily-allowance figures."""
    out = []
    remaining_days = max(days_remaining(budget.period), 1)
    for c in budget.categories:
        spent = category_spent(db, c.id)
        allocation = D(c.allocation)
        remaining = allocation - spent
        out.append(
            schemas.CategoryOut(
                id=c.id,
                budget_id=c.budget_id,
                name=c.name,
                allocation=round2(allocation),
                spending_limit=round2(c.spending_limit) if c.spending_limit is not None else None,
                color=c.color,
                icon=c.icon,
                is_travel=c.is_travel,
                fixed_amount=round2(c.fixed_amount),
                estimated_daily_amount=round2(c.estimated_daily_amount) if c.estimated_daily_amount is not None else None,
                spent=round2(spent),
                remaining=round2(remaining),
                percent_used=pct(spent, allocation),
                daily_allowance=round2(safe_div(remaining, remaining_days)),
            )
        )
    return out


# ------------------------------------------------------------------ travel
def compute_travel_analytics(db: Session, budget: models.Budget, as_of: date | None = None) -> schemas.TravelAnalytics | None:
    travel_category = next((c for c in budget.categories if c.is_travel), None)
    if not travel_category:
        return None

    as_of = as_of or date.today()
    spent = category_spent(db, travel_category.id)
    travel_budget = D(travel_category.allocation)
    travel_remaining = travel_budget - spent

    fixed = D(travel_category.fixed_amount)
    variable_budget = travel_budget - fixed
    # Variable spend = total spend minus fixed portion already "used up"
    variable_spent = max(spent - fixed, Decimal("0"))
    variable_remaining = variable_budget - variable_spent

    remaining_days = max(days_remaining(budget.period, as_of), 0)
    recommended_daily = safe_div(variable_remaining, remaining_days) if remaining_days > 0 else Decimal("0")

    result = schemas.TravelAnalytics(
        travel_budget=round2(travel_budget),
        travel_spent=round2(spent),
        travel_remaining=round2(travel_remaining),
        fixed_travel_expenses=round2(fixed),
        variable_travel_budget=round2(variable_budget),
        variable_travel_remaining=round2(variable_remaining),
        recommended_daily_spending=round2(recommended_daily),
    )

    if travel_category.estimated_daily_amount is not None and remaining_days > 0:
        est_daily = D(travel_category.estimated_daily_amount)
        expected_cost = est_daily * D(remaining_days)
        sufficient = expected_cost <= variable_remaining
        result.estimated_daily_travel = round2(est_daily)
        result.expected_cost_remaining_days = round2(expected_cost)
        result.budget_sufficient = sufficient

        if est_daily > 0:
            days_until_exhausted = int(safe_div(variable_remaining, est_daily))
            days_until_exhausted = max(days_until_exhausted, 0)
            exhaustion_date = as_of + timedelta(days=days_until_exhausted)
            _, period_end = period_bounds(budget.period)
            result.expected_exhaustion_date = min(exhaustion_date, period_end)

        if not sufficient and remaining_days > 0:
            required_daily = safe_div(variable_remaining, remaining_days)
            reduction = est_daily - required_daily
            result.required_daily_reduction = round2(max(reduction, Decimal("0")))

    return result


# -------------------------------------------------------------------- trend
def spending_trends(db: Session, budget: models.Budget) -> list[schemas.SpendingTrendPoint]:
    first_day, _ = period_bounds(budget.period)
    expenses = db.scalars(select(models.Expense).where(models.Expense.budget_id == budget.id))
    by_day: dict[date, Decimal] = {}
    for e in expenses:
        by_day[e.date] = by_day.get(e.date, Decimal("0")) + D(e.amount)

    today = date.today()
    last_day = today if today >= first_day else first_day
    points: list[schemas.SpendingTrendPoint] = []
    cumulative = Decimal("0")
    d = first_day
    while d <= last_day:
        amount = by_day.get(d, Decimal("0"))
        cumulative += amount
        points.append(schemas.SpendingTrendPoint(date=d, amount=round2(amount), cumulative=round2(cumulative)))
        d += timedelta(days=1)
    return points
