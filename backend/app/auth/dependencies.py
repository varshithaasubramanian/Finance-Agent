"""
`get_current_user` — the FastAPI dependency every protected route uses to
resolve "who is making this request" from an `Authorization: Bearer <token>`
header. Every budget/expense/category/etc. endpoint depends on this (directly
or via `get_owned_budget_or_404`) so that one user's data is never visible or
editable by another.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database.db import get_db
from app.models import models

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session. Please log in again.")

    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session. Please log in again.")

    return user
