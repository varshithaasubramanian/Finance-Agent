"""Category CRUD service, including default category seeding and
over-allocation protection."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.utils.decimal_utils import D

DEFAULT_CATEGORIES = [
    {"name": "Food", "icon": "utensils", "color": "#0F766E"},
    {"name": "Travel", "icon": "bus", "color": "#2563EB", "is_travel": True},
    {"name": "Education", "icon": "book", "color": "#7C3AED"},
    {"name": "Shopping", "icon": "bag", "color": "#DB2777"},
    {"name": "Entertainment", "icon": "film", "color": "#EA580C"},
    {"name": "Bills", "icon": "receipt", "color": "#0891B2"},
    {"name": "Health", "icon": "heart", "color": "#DC2626"},
    {"name": "Others", "icon": "dots", "color": "#64748B"},
]


class CategoryError(Exception):
    pass


def list_categories(db: Session, budget_id: str) -> list[models.Category]:
    return list(db.scalars(select(models.Category).where(models.Category.budget_id == budget_id)))


def get_category(db: Session, category_id: str) -> models.Category | None:
    return db.get(models.Category, category_id)


def get_category_or_404(db: Session, category_id: str) -> models.Category:
    cat = get_category(db, category_id)
    if not cat:
        raise CategoryError(f"Category {category_id} not found")
    return cat


def _current_allocation_total(db: Session, budget: models.Budget, exclude_id: str | None = None) -> Decimal:
    total = Decimal("0")
    for cat in budget.categories:
        if exclude_id and cat.id == exclude_id:
            continue
        total += D(cat.allocation)
    return total


def create_category(db: Session, budget: models.Budget, data: schemas.CategoryCreate) -> models.Category:
    existing_names = {c.name.lower() for c in budget.categories}
    if data.name.lower() in existing_names:
        raise CategoryError(f"Category '{data.name}' already exists in this budget")

    new_total = _current_allocation_total(db, budget) + D(data.allocation)
    if not budget.allow_over_allocation and new_total > D(budget.total_amount):
        raise CategoryError(
            f"Allocating {data.allocation} would bring total category allocation to {new_total}, "
            f"exceeding the budget of {budget.total_amount}. Enable over-allocation to override."
        )

    category = models.Category(
        budget_id=budget.id,
        name=data.name,
        allocation=data.allocation,
        spending_limit=data.spending_limit,
        color=data.color,
        icon=data.icon,
        is_travel=data.is_travel,
        fixed_amount=data.fixed_amount,
        estimated_daily_amount=data.estimated_daily_amount,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, budget: models.Budget, category: models.Category, data: schemas.CategoryUpdate) -> models.Category:
    if data.allocation is not None:
        new_total = _current_allocation_total(db, budget, exclude_id=category.id) + D(data.allocation)
        if not budget.allow_over_allocation and new_total > D(budget.total_amount):
            raise CategoryError(
                f"Allocating {data.allocation} would bring total category allocation to {new_total}, "
                f"exceeding the budget of {budget.total_amount}."
            )
        category.allocation = data.allocation

    for field in ("name", "spending_limit", "color", "icon", "is_travel", "fixed_amount", "estimated_daily_amount"):
        value = getattr(data, field)
        if value is not None:
            setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: models.Category) -> None:
    db.delete(category)
    db.commit()


def seed_default_categories(db: Session, budget: models.Budget, allocations: dict[str, float] | None = None) -> None:
    """Create the default category set. `allocations` maps category name ->
    allocation amount; categories without an explicit allocation default to 0."""
    allocations = allocations or {}
    for spec in DEFAULT_CATEGORIES:
        db.add(
            models.Category(
                budget_id=budget.id,
                name=spec["name"],
                allocation=allocations.get(spec["name"], 0),
                color=spec["color"],
                icon=spec["icon"],
                is_travel=spec.get("is_travel", False),
            )
        )
    db.commit()
