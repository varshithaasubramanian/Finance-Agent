"""Budget creation/retrieval service."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.utils.date_utils import current_period


class BudgetError(Exception):
    pass


def get_or_create_demo_user(db: Session) -> models.User:
    user = db.scalar(select(models.User).where(models.User.email == "demo@financeagent.local"))
    if user:
        return user
    user = models.User(
        name="Demo User",
        email="demo@financeagent.local",
        hashed_password="not-used-in-demo-mode",
        currency="INR",
        currency_symbol="\u20b9",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_budget(db: Session, budget_id: str) -> models.Budget | None:
    return db.get(models.Budget, budget_id)


def get_budget_or_404(db: Session, budget_id: str) -> models.Budget:
    budget = get_budget(db, budget_id)
    if not budget:
        raise BudgetError(f"Budget {budget_id} not found")
    return budget


def get_owned_budget_or_404(db: Session, budget_id: str, user: models.User) -> models.Budget:
    """Like get_budget_or_404, but also enforces that the budget belongs to
    the given user. Returns a generic 'not found' (rather than 'forbidden')
    for budgets owned by someone else, so we don't leak which budget IDs
    exist to unauthorized callers."""
    budget = get_budget(db, budget_id)
    if not budget or budget.user_id != user.id:
        raise BudgetError(f"Budget {budget_id} not found")
    return budget


def get_current_budget(db: Session, user: models.User) -> models.Budget | None:
    period = current_period()
    return db.scalar(
        select(models.Budget).where(models.Budget.user_id == user.id, models.Budget.period == period)
    )

def list_budgets(db: Session, user: models.User) -> list[models.Budget]:
    return list(
        db.scalars(select(models.Budget).where(models.Budget.user_id == user.id).order_by(models.Budget.period.desc()))
    )


def create_budget(db: Session, user: models.User, data: schemas.BudgetCreate) -> models.Budget:
    existing = db.scalar(
        select(models.Budget).where(models.Budget.user_id == user.id, models.Budget.period == data.period)
    )
    if existing:
        raise BudgetError(f"A budget for period {data.period} already exists")

    total = sum((c.allocation for c in data.categories), 0.0)
    if not data.allow_over_allocation and data.categories and total > data.total_amount:
        raise BudgetError(
            f"Category allocations ({total}) exceed the total budget ({data.total_amount}). "
            "Enable allow_over_allocation to override."
        )

    budget = models.Budget(
        user_id=user.id,
        period=data.period,
        total_amount=data.total_amount,
        allow_over_allocation=data.allow_over_allocation,
    )
    db.add(budget)
    db.flush()

    for cat in data.categories:
        db.add(
            models.Category(
                budget_id=budget.id,
                name=cat.name,
                allocation=cat.allocation,
                spending_limit=cat.spending_limit,
                color=cat.color,
                icon=cat.icon,
                is_travel=cat.is_travel,
                fixed_amount=cat.fixed_amount,
                estimated_daily_amount=cat.estimated_daily_amount,
            )
        )

    db.commit()
    db.refresh(budget)
    return budget


def update_budget(db: Session, budget: models.Budget, data: schemas.BudgetUpdate) -> models.Budget:
    if data.total_amount is not None:
        budget.total_amount = data.total_amount
    if data.allow_over_allocation is not None:
        budget.allow_over_allocation = data.allow_over_allocation
    db.commit()
    db.refresh(budget)
    return budget
