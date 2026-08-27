from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import assistant
from app.ai.ai_client import get_ai_client
from app.auth.dependencies import get_current_user
from app.database.db import get_db
from app.models import models
from app.schemas import schemas
from app.services import budget_service

router = APIRouter(prefix="/api/budgets/{budget_id}/assistant", tags=["assistant"])


def _owned_budget(budget_id: str, db: Session, user: models.User) -> models.Budget:
    try:
        return budget_service.get_owned_budget_or_404(db, budget_id, user)
    except budget_service.BudgetError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/ask", response_model=schemas.AssistantResponse)
def ask_assistant(budget_id: str, payload: schemas.AssistantRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    budget = _owned_budget(budget_id, db, user)
    return assistant.answer(db, budget, payload.message)


@router.get("/status")
def assistant_status(budget_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_budget(budget_id, db, user)
    client = get_ai_client()
    return {"ai_enabled": client.enabled, "model": client.model if client.enabled else None}
