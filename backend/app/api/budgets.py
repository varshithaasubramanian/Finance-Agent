from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.db import get_db
from app.models import models
from app.schemas import schemas
from app.services import budget_service, category_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _to_budget_out(budget: models.Budget, db: Session) -> schemas.BudgetOut:
    from app.services.analytics_service import category_out_list

    return schemas.BudgetOut(
        id=budget.id,
        period=budget.period,
        total_amount=float(budget.total_amount),
        allow_over_allocation=budget.allow_over_allocation,
        currency_symbol=budget.user.currency_symbol if budget.user else "\u20b9",
        categories=category_out_list(db, budget),
    )


@router.get("", response_model=list[schemas.BudgetOut])
def list_budgets(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budgets = budget_service.list_budgets(db, user)
    return [_to_budget_out(b, db) for b in budgets]


@router.get("/current", response_model=schemas.BudgetOut)
def get_current(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = budget_service.get_current_budget(db, user)
    if not budget:
        raise HTTPException(status_code=404, detail="No budget exists for the current month yet. Create one first.")
    return _to_budget_out(budget, db)


@router.get("/{budget_id}", response_model=schemas.BudgetOut)
def get_budget(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    try:
        budget = budget_service.get_owned_budget_or_404(db, budget_id, user)
    except budget_service.BudgetError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_budget_out(budget, db)


@router.post("", response_model=schemas.BudgetOut, status_code=201)
def create_budget(payload: schemas.BudgetCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    try:
        budget = budget_service.create_budget(db, user, payload)
        if not payload.categories:
            category_service.seed_default_categories(db, budget)
            db.refresh(budget)
        return _to_budget_out(budget, db)
    except budget_service.BudgetError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{budget_id}", response_model=schemas.BudgetOut)
def update_budget(budget_id: str, payload: schemas.BudgetUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    try:
        budget = budget_service.get_owned_budget_or_404(db, budget_id, user)
    except budget_service.BudgetError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    budget = budget_service.update_budget(db, budget, payload)
    return _to_budget_out(budget, db)
