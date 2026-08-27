from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.db import get_db
from app.models import models
from app.schemas import schemas
from app.services import budget_service, recurring_service

router = APIRouter(prefix="/api/budgets/{budget_id}/recurring", tags=["recurring"])


def _owned_budget(budget_id: str, db: Session, user: models.User) -> models.Budget:
    try:
        return budget_service.get_owned_budget_or_404(db, budget_id, user)
    except budget_service.BudgetError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _to_out(r) -> schemas.RecurringExpenseOut:
    return schemas.RecurringExpenseOut(
        id=r.id,
        budget_id=r.budget_id,
        category_id=r.category_id,
        category_name=r.category.name if r.category else "",
        name=r.name,
        amount=float(r.amount),
        frequency=r.frequency.value,
        next_due_date=r.next_due_date,
        active=r.active,
    )


@router.get("", response_model=list[schemas.RecurringExpenseOut])
def list_recurring(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_budget(budget_id, db, user)
    return [_to_out(r) for r in recurring_service.list_recurring(db, budget_id)]


@router.post("", response_model=schemas.RecurringExpenseOut, status_code=201)
def create_recurring(budget_id: str, payload: schemas.RecurringExpenseCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    try:
        r = recurring_service.create_recurring(db, budget, payload)
        return _to_out(r)
    except recurring_service.RecurringError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{recurring_id}", status_code=204)
def delete_recurring(budget_id: str, recurring_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_budget(budget_id, db, user)
    try:
        r = recurring_service.get_recurring_or_404(db, recurring_id)
    except recurring_service.RecurringError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if r.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    recurring_service.delete_recurring(db, r)
    return None


@router.post("/{recurring_id}/deactivate", response_model=schemas.RecurringExpenseOut)
def deactivate_recurring(budget_id: str, recurring_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_budget(budget_id, db, user)
    try:
        r = recurring_service.get_recurring_or_404(db, recurring_id)
    except recurring_service.RecurringError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if r.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    r = recurring_service.deactivate_recurring(db, r)
    return _to_out(r)
