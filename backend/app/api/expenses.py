from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.db import get_db
from app.models import models
from app.schemas import schemas
from app.services import budget_service, expense_service

router = APIRouter(prefix="/api/budgets/{budget_id}/expenses", tags=["expenses"])


def _owned_budget(budget_id: str, db: Session, user: models.User) -> models.Budget:
    try:
        return budget_service.get_owned_budget_or_404(db, budget_id, user)
    except budget_service.BudgetError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _to_out(e) -> schemas.ExpenseOut:
    return schemas.ExpenseOut(
        id=e.id,
        budget_id=e.budget_id,
        category_id=e.category_id,
        category_name=e.category.name if e.category else "",
        amount=float(e.amount),
        description=e.description,
        date=e.date,
        payment_method=e.payment_method.value,
        notes=e.notes,
        is_ai_entered=e.is_ai_entered,
        created_at=e.created_at,
    )


@router.get("", response_model=list[schemas.ExpenseOut])
def list_expenses(
    budget_id: str,
    category_id: str | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    payment_method: schemas.PaymentMethodEnum | None = None,
    sort_by: str = Query("date", pattern="^(date|amount|category)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _owned_budget(budget_id, db, user)
    filters = schemas.ExpenseFilter(
        category_id=category_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        payment_method=payment_method,
        sort_by=sort_by,  # type: ignore[arg-type]
        sort_dir=sort_dir,  # type: ignore[arg-type]
    )
    expenses = expense_service.list_expenses(db, budget_id, filters)
    return [_to_out(e) for e in expenses]


@router.post("", response_model=schemas.ExpenseOut, status_code=201)
def create_expense(budget_id: str, payload: schemas.ExpenseCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    try:
        expense = expense_service.create_expense(db, budget, payload)
        return _to_out(expense)
    except expense_service.ExpenseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(budget_id: str, expense_id: str, payload: schemas.ExpenseUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_budget(budget_id, db, user)
    expense = expense_service.get_expense(db, expense_id)
    if not expense or expense.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    try:
        expense = expense_service.update_expense(db, expense, payload)
        return _to_out(expense)
    except expense_service.ExpenseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{expense_id}", status_code=204)
def delete_expense(budget_id: str, expense_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_budget(budget_id, db, user)
    expense = expense_service.get_expense(db, expense_id)
    if not expense or expense.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    expense_service.delete_expense(db, expense)
    return None
