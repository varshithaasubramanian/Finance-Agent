"""Expense CRUD, filtering, search and sorting service."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas


class ExpenseError(Exception):
    pass


def get_expense(db: Session, expense_id: str) -> models.Expense | None:
    return db.get(models.Expense, expense_id)


def get_expense_or_404(db: Session, expense_id: str) -> models.Expense:
    expense = get_expense(db, expense_id)
    if not expense:
        raise ExpenseError(f"Expense {expense_id} not found")
    return expense


def create_expense(db: Session, budget: models.Budget, data: schemas.ExpenseCreate) -> models.Expense:
    category = db.get(models.Category, data.category_id)
    if not category or category.budget_id != budget.id:
        raise ExpenseError("Category does not belong to this budget")

    expense = models.Expense(
        budget_id=budget.id,
        category_id=data.category_id,
        amount=data.amount,
        description=data.description,
        date=data.date,
        payment_method=models.PaymentMethod(data.payment_method.value),
        notes=data.notes,
        is_ai_entered=data.is_ai_entered,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def update_expense(db: Session, expense: models.Expense, data: schemas.ExpenseUpdate) -> models.Expense:
    if data.category_id is not None:
        category = db.get(models.Category, data.category_id)
        if not category or category.budget_id != expense.budget_id:
            raise ExpenseError("Category does not belong to this budget")
        expense.category_id = data.category_id
    if data.amount is not None:
        expense.amount = data.amount
    if data.description is not None:
        expense.description = data.description
    if data.date is not None:
        expense.date = data.date
    if data.payment_method is not None:
        expense.payment_method = models.PaymentMethod(data.payment_method.value)
    if data.notes is not None:
        expense.notes = data.notes

    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, expense: models.Expense) -> None:
    db.delete(expense)
    db.commit()


def list_expenses(db: Session, budget_id: str, filters: schemas.ExpenseFilter) -> list[models.Expense]:
    stmt = select(models.Expense).where(models.Expense.budget_id == budget_id)

    if filters.category_id:
        stmt = stmt.where(models.Expense.category_id == filters.category_id)
    if filters.date_from:
        stmt = stmt.where(models.Expense.date >= filters.date_from)
    if filters.date_to:
        stmt = stmt.where(models.Expense.date <= filters.date_to)
    if filters.payment_method:
        stmt = stmt.where(models.Expense.payment_method == models.PaymentMethod(filters.payment_method.value))
    if filters.search:
        like = f"%{filters.search.lower()}%"
        stmt = stmt.where(models.Expense.description.ilike(like))

    expenses = list(db.scalars(stmt))

    reverse = filters.sort_dir == "desc"
    if filters.sort_by == "date":
        expenses.sort(key=lambda e: (e.date, e.created_at), reverse=reverse)
    elif filters.sort_by == "amount":
        expenses.sort(key=lambda e: float(e.amount), reverse=reverse)
    elif filters.sort_by == "category":
        expenses.sort(key=lambda e: (e.category.name if e.category else ""), reverse=reverse)

    return expenses


def get_recent_expenses(db: Session, budget_id: str, limit: int = 5) -> list[models.Expense]:
    stmt = (
        select(models.Expense)
        .where(models.Expense.budget_id == budget_id)
        .order_by(models.Expense.date.desc(), models.Expense.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
