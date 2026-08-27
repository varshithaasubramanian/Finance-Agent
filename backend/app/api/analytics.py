from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.db import get_db
from app.models import models
from app.schemas import schemas
from app.services import affordability_service, alert_service, analytics_service, budget_service, forecast_service
from app.ai import nlp_parser

router = APIRouter(prefix="/api/budgets/{budget_id}", tags=["analytics"])


def _owned_budget(budget_id: str, db: Session, user: models.User) -> models.Budget:
    try:
        return budget_service.get_owned_budget_or_404(db, budget_id, user)
    except budget_service.BudgetError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/summary", response_model=schemas.BudgetSummary)
def get_summary(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    return analytics_service.compute_budget_summary(db, budget)


@router.get("/travel", response_model=schemas.TravelAnalytics | None)
def get_travel(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    return analytics_service.compute_travel_analytics(db, budget)


@router.get("/trends", response_model=list[schemas.SpendingTrendPoint])
def get_trends(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    return analytics_service.spending_trends(db, budget)


@router.get("/forecast", response_model=schemas.ForecastOut)
def get_forecast(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    return forecast_service.generate_forecast(db, budget)


@router.get("/alerts", response_model=list[schemas.AlertOut])
def get_alerts(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    alerts = alert_service.generate_alerts(db, budget)
    alert_service.persist_alerts(db, budget, alerts)
    return alerts


@router.post("/affordability", response_model=schemas.AffordabilityResponse)
def check_affordability(budget_id: str, payload: schemas.AffordabilityRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    return affordability_service.evaluate_affordability(
        db, budget, amount=payload.amount, category_id=payload.category_id
    )


@router.post("/parse-expense", response_model=schemas.ParsedExpense)
def parse_expense(budget_id: str, payload: schemas.NLParseRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_budget(budget_id, db, user)
    try:
        return nlp_parser.parse_expense_text(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
