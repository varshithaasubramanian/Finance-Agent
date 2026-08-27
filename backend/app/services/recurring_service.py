"""Recurring expense CRUD and committed-amount projection.

Recurring expenses (bus pass, subscriptions, hostel fee, ...) are included
in affordability and forecasting calculations via `project_committed_amount`,
which sums the expected occurrences of each active recurring expense between
`as_of` and `period_end`.
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.utils.date_utils import period_bounds
from app.utils.decimal_utils import D


class RecurringError(Exception):
    pass


def list_recurring(db: Session, budget_id: str) -> list[models.RecurringExpense]:
    return list(
        db.scalars(select(models.RecurringExpense).where(models.RecurringExpense.budget_id == budget_id))
    )


def get_recurring_or_404(db: Session, recurring_id: str) -> models.RecurringExpense:
    r = db.get(models.RecurringExpense, recurring_id)
    if not r:
        raise RecurringError(f"Recurring expense {recurring_id} not found")
    return r


def create_recurring(db: Session, budget: models.Budget, data: schemas.RecurringExpenseCreate) -> models.RecurringExpense:
    category = db.get(models.Category, data.category_id)
    if not category or category.budget_id != budget.id:
        raise RecurringError("Category does not belong to this budget")

    r = models.RecurringExpense(
        budget_id=budget.id,
        category_id=data.category_id,
        name=data.name,
        amount=data.amount,
        frequency=models.RecurrenceFrequency(data.frequency.value),
        next_due_date=data.next_due_date,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def deactivate_recurring(db: Session, r: models.RecurringExpense) -> models.RecurringExpense:
    r.active = False
    db.commit()
    db.refresh(r)
    return r


def delete_recurring(db: Session, r: models.RecurringExpense) -> None:
    db.delete(r)
    db.commit()


def upcoming_occurrences(recurring: models.RecurringExpense, start: date, end: date) -> list[date]:
    """List the dates on which this recurring expense is expected to occur
    between start and end (inclusive)."""
    occurrences: list[date] = []
    current = recurring.next_due_date
    step = {
        models.RecurrenceFrequency.DAILY: timedelta(days=1),
        models.RecurrenceFrequency.WEEKLY: timedelta(days=7),
        models.RecurrenceFrequency.MONTHLY: timedelta(days=30),
    }[recurring.frequency]

    # Fast-forward to the first occurrence >= start
    guard = 0
    while current < start and guard < 400:
        current = current + step
        guard += 1

    guard = 0
    while current <= end and guard < 400:
        occurrences.append(current)
        current = current + step
        guard += 1

    return occurrences


def project_committed_amount(db: Session, budget: models.Budget, as_of: date | None = None, category_id: str | None = None) -> Decimal:
    """Sum of expected recurring-expense occurrences between `as_of` and the
    end of the budget period. Used by forecasting and affordability checks
    so that known upcoming bills are accounted for."""
    as_of = as_of or date.today()
    _, period_end = period_bounds(budget.period)
    if as_of > period_end:
        return Decimal("0")

    total = Decimal("0")
    for r in list_recurring(db, budget.id):
        if not r.active:
            continue
        if category_id and r.category_id != category_id:
            continue
        occurrences = upcoming_occurrences(r, as_of, period_end)
        total += D(r.amount) * len(occurrences)
    return total
