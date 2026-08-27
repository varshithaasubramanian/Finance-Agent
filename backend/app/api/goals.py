from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.db import get_db
from app.models import models
from app.schemas import schemas
from app.services import goal_service

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("", response_model=list[schemas.FinancialGoalOut])
def list_goals(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    goals = goal_service.list_goals(db, user.id)
    return [goal_service.compute_goal_out(g) for g in goals]


@router.post("", response_model=schemas.FinancialGoalOut, status_code=201)
def create_goal(payload: schemas.FinancialGoalCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    goal = goal_service.create_goal(db, user, payload)
    return goal_service.compute_goal_out(goal)


@router.patch("/{goal_id}", response_model=schemas.FinancialGoalOut)
def update_goal(goal_id: str, payload: schemas.FinancialGoalUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    try:
        goal = goal_service.get_goal_or_404(db, goal_id)
    except goal_service.GoalError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal = goal_service.update_goal(db, goal, payload)
    return goal_service.compute_goal_out(goal)


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    try:
        goal = goal_service.get_goal_or_404(db, goal_id)
    except goal_service.GoalError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal_service.delete_goal(db, goal)
    return None
