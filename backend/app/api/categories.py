from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.db import get_db
from app.models import models
from app.services import budget_service, category_service
from app.services.analytics_service import category_out_list
from app.schemas import schemas

router = APIRouter(prefix="/api/budgets/{budget_id}/categories", tags=["categories"])


def _owned_budget(budget_id: str, db: Session, user: models.User) -> models.Budget:
    try:
        return budget_service.get_owned_budget_or_404(db, budget_id, user)
    except budget_service.BudgetError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("", response_model=list[schemas.CategoryOut])
def list_categories(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    return category_out_list(db, budget)


@router.post("", response_model=schemas.CategoryOut, status_code=201)
def create_category(budget_id: str, payload: schemas.CategoryCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    try:
        category_service.create_category(db, budget, payload)
        db.refresh(budget)
        return next(c for c in category_out_list(db, budget) if c.name == payload.name)
    except category_service.CategoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{category_id}", response_model=schemas.CategoryOut)
def update_category(budget_id: str, category_id: str, payload: schemas.CategoryUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    category = category_service.get_category(db, category_id)
    if not category or category.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Category not found")
    try:
        category_service.update_category(db, budget, category, payload)
        db.refresh(budget)
        return next(c for c in category_out_list(db, budget) if c.id == category_id)
    except category_service.CategoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{category_id}", status_code=204)
def delete_category(budget_id: str, category_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_budget(budget_id, db, user)
    category = category_service.get_category(db, category_id)
    if not category or category.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="Category not found")
    category_service.delete_category(db, category)
    return None
