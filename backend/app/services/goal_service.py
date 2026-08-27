"""Financial goals CRUD and saving-plan calculations."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.utils.decimal_utils import D, round2, safe_div


class GoalError(Exception):
    pass


def list_goals(db: Session, user_id: str) -> list[models.FinancialGoal]:
    return list(db.scalars(select(models.FinancialGoal).where(models.FinancialGoal.user_id == user_id)))


def get_goal_or_404(db: Session, goal_id: str) -> models.FinancialGoal:
    g = db.get(models.FinancialGoal, goal_id)
    if not g:
        raise GoalError(f"Goal {goal_id} not found")
    return g


def create_goal(db: Session, user: models.User, data: schemas.FinancialGoalCreate) -> models.FinancialGoal:
    goal = models.FinancialGoal(
        user_id=user.id,
        name=data.name,
        target_amount=data.target_amount,
        current_amount=data.current_amount,
        deadline=data.deadline,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(db: Session, goal: models.FinancialGoal, data: schemas.FinancialGoalUpdate) -> models.FinancialGoal:
    for field in ("name", "target_amount", "current_amount", "deadline"):
        value = getattr(data, field)
        if value is not None:
            setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal: models.FinancialGoal) -> None:
    db.delete(goal)
    db.commit()


def compute_goal_out(goal: models.FinancialGoal, as_of: date | None = None) -> schemas.FinancialGoalOut:
    as_of = as_of or date.today()
    remaining = D(goal.target_amount) - D(goal.current_amount)
    days_left = max((goal.deadline - as_of).days, 0)
    weeks_left = max(safe_div(days_left, 7), 1) if days_left > 0 else 1

    daily = safe_div(remaining, days_left) if days_left > 0 else remaining
    weekly = safe_div(remaining, weeks_left) if days_left > 0 else remaining

    return schemas.FinancialGoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=round2(goal.target_amount),
        current_amount=round2(goal.current_amount),
        deadline=goal.deadline,
        remaining_amount=round2(max(remaining, 0)),
        days_left=days_left,
        required_daily_saving=round2(max(daily, 0)),
        required_weekly_saving=round2(max(weekly, 0)),
    )
