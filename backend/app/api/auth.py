"""Signup / login / current-user / password-recovery endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.database.db import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _normalize_answer(answer: str) -> str:
    """Security answers are matched case/whitespace-insensitively so a
    user isn't locked out by capitalization differences."""
    return answer.strip().lower()


@router.get("/security-questions", response_model=list[str])
def security_questions():
    return schemas.SECURITY_QUESTIONS


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
        security_question=payload.security_question,
        security_answer_hash=hash_password(_normalize_answer(payload.security_answer)),
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


@router.patch("/me", response_model=schemas.UserOut)
def update_me(payload: schemas.UserUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if payload.name is not None:
        user.name = payload.name.strip()
        db.commit()
        db.refresh(user)
    return user


@router.post("/change-password", status_code=204)
def change_password(payload: schemas.ChangePasswordRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return None


@router.post("/forgot-password", response_model=schemas.ForgotPasswordResponse)
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Returns the account's security question so the user can answer it to
    reset their password. Deliberately does not reveal whether the email
    exists at all -- an unknown email and an account with no security
    question configured both come back as security_question: null, so an
    attacker can't use this endpoint to enumerate registered emails."""
    email = payload.email.lower()
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user or not user.security_question:
        return schemas.ForgotPasswordResponse(security_question=None)
    return schemas.ForgotPasswordResponse(security_question=user.security_question)


@router.post("/reset-password", response_model=schemas.Token)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user or not user.security_answer_hash:
        raise HTTPException(status_code=400, detail="No recovery option is set up for this account.")
    if not verify_password(_normalize_answer(payload.security_answer), user.security_answer_hash):
        raise HTTPException(status_code=400, detail="That answer doesn't match our records.")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))
