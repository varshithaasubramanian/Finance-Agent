from datetime import date

from app.models import models
from app.services import affordability_service


def _add_expense(db, budget, category, amount, on_date):
    e = models.Expense(
        budget_id=budget.id,
        category_id=category.id,
        amount=amount,
        description="test",
        date=on_date,
        payment_method=models.PaymentMethod.CASH,
    )
    db.add(e)
    db.commit()


def test_affordability_yes_when_plenty_remaining(db, demo_budget):
    result = affordability_service.evaluate_affordability(
        db, demo_budget, amount=100, as_of=date(2026, 8, 5)
    )
    assert result.verdict == "Yes"
    assert result.remaining_total_after == 1900.0


def test_affordability_no_when_would_go_negative(db, demo_budget):
    food = demo_budget.categories[0]
    _add_expense(db, demo_budget, food, 1900, date(2026, 8, 1))
    result = affordability_service.evaluate_affordability(
        db, demo_budget, amount=200, as_of=date(2026, 8, 5)
    )
    assert result.verdict == "No"
    assert result.remaining_total_after < 0


def test_affordability_with_category_context(db, demo_budget):
    food = demo_budget.categories[0]
    _add_expense(db, demo_budget, food, 900, date(2026, 8, 1))
    result = affordability_service.evaluate_affordability(
        db, demo_budget, amount=150, category_id=food.id, as_of=date(2026, 8, 5)
    )
    assert result.category_name == "Food"
    assert result.category_remaining_before == 100.0
    assert result.category_remaining_after == -50.0
    assert result.verdict in ("Caution", "No")


def test_affordability_caution_when_tight(db, demo_budget):
    food = demo_budget.categories[0]
    _add_expense(db, demo_budget, food, 1850, date(2026, 8, 1))
    result = affordability_service.evaluate_affordability(
        db, demo_budget, amount=100, as_of=date(2026, 8, 28)
    )
    assert result.verdict in ("Caution", "No")


def test_affordability_never_mentions_investing(db, demo_budget):
    result = affordability_service.evaluate_affordability(db, demo_budget, amount=50, as_of=date(2026, 8, 5))
    assert "invest" not in result.explanation.lower()
