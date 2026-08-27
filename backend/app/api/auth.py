"""Signup / login / current-user endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.database.db import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.Token, status_code=201)
def signup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()
    existing = db.scalar(select(models.User).where(models.User.email == email))
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = models.User(
        name=payload.name.strip(),
        email=email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    email = payload.email.lower()
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(user.id)
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
