from datetime import date, timedelta

from app.models import models
from app.services import analytics_service


def _add_expense(db, budget, category, amount, days_ago=0, description="test"):
    e = models.Expense(
        budget_id=budget.id,
        category_id=category.id,
        amount=amount,
        description=description,
        date=date.today() - timedelta(days=days_ago),
        payment_method=models.PaymentMethod.CASH,
    )
    db.add(e)
    db.commit()
    return e


def test_budget_totals_with_no_expenses(db, demo_budget):
    summary = analytics_service.compute_budget_summary(db, demo_budget)
    assert summary.total_budget == 2000.0
    assert summary.total_spent == 0.0
    assert summary.total_remaining == 2000.0
    assert summary.percent_used == 0.0


def test_total_spent_sums_all_categories(db, demo_budget):
    food = demo_budget.categories[0]
    travel = demo_budget.categories[1]
    _add_expense(db, demo_budget, food, 120)
    _add_expense(db, demo_budget, travel, 60)
    db.refresh(demo_budget)

    summary = analytics_service.compute_budget_summary(db, demo_budget)
    assert summary.total_spent == 180.0
    assert summary.total_remaining == 1820.0


def test_category_remaining_amount(db, demo_budget):
    food = demo_budget.categories[0]
    _add_expense(db, demo_budget, food, 650)
    db.refresh(demo_budget)

    analytics = analytics_service.compute_category_analytics(db, demo_budget, food)
    assert analytics.spent == 650.0
    assert analytics.remaining == 350.0
    assert analytics.percent_used == 65.0


def test_budget_utilization_percentage(db, demo_budget):
    food = demo_budget.categories[0]
    _add_expense(db, demo_budget, food, 250)
    db.refresh(demo_budget)

    analytics = analytics_service.compute_category_analytics(db, demo_budget, food)
    # 250 / 1000 * 100 = 25%
    assert analytics.percent_used == 25.0


def test_overspending_produces_negative_remaining(db, demo_budget):
    others = demo_budget.categories[2]
    _add_expense(db, demo_budget, others, 250)  # allocation is 200
    db.refresh(demo_budget)

    analytics = analytics_service.compute_category_analytics(db, demo_budget, others)
    assert analytics.remaining == -50.0
    assert analytics.percent_used == 125.0


def test_zero_spending_edge_case(db, demo_budget):
    summary = analytics_service.compute_budget_summary(db, demo_budget)
    for cat in summary.categories:
        assert cat.spent == 0.0
        assert cat.percent_used == 0.0


def test_category_with_no_expenses_has_full_remaining(db, demo_budget):
    education = models.Category(budget_id=demo_budget.id, name="Education", allocation=500)
    db.add(education)
    db.commit()
    db.refresh(demo_budget)

    analytics = analytics_service.compute_category_analytics(db, demo_budget, education)
    assert analytics.spent == 0.0
    assert analytics.remaining == 500.0
