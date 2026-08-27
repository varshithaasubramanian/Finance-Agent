from datetime import date

from app.models import models
from app.services import analytics_service, forecast_service
from app.utils.date_utils import days_elapsed, days_remaining, total_days_in_period


def _add_expense(db, budget, category, amount, on_date, description="test"):
    e = models.Expense(
        budget_id=budget.id,
        category_id=category.id,
        amount=amount,
        description=description,
        date=on_date,
        payment_method=models.PaymentMethod.CASH,
    )
    db.add(e)
    db.commit()
    return e


def test_daily_average_and_remaining_allowance(db, demo_budget):
    as_of = date(2026, 8, 10)  # day 10 of a 31-day period -> 21 days remaining (incl. today)
    food = demo_budget.categories[0]
    _add_expense(db, demo_budget, food, 100, date(2026, 8, 5))
    _add_expense(db, demo_budget, food, 100, date(2026, 8, 8))
    db.refresh(demo_budget)

    summary = analytics_service.compute_budget_summary(db, demo_budget, as_of=as_of)
    assert summary.days_elapsed == 10
    assert summary.days_remaining == 22
    assert summary.total_spent == 200.0
    # daily average = 200 / 10 = 20
    assert summary.daily_average_spending == 20.0
    # safe daily = remaining (1800) / 22 days
    assert round(summary.recommended_safe_daily_spending, 2) == round(1800 / 22, 2)


def test_travel_fixed_and_variable_split(db, demo_budget):
    as_of = date(2026, 8, 11)  # 20 days remaining
    travel = demo_budget.categories[1]
    _add_expense(db, demo_budget, travel, 300, date(2026, 8, 1), "Monthly bus pass")  # the fixed cost
    _add_expense(db, demo_budget, travel, 100, date(2026, 8, 5), "Cab")
    db.refresh(demo_budget)

    travel_analytics = analytics_service.compute_travel_analytics(db, demo_budget, as_of=as_of)
    assert travel_analytics.travel_budget == 800.0
    assert travel_analytics.fixed_travel_expenses == 300.0
    assert travel_analytics.variable_travel_budget == 500.0
    # spent 400 total, fixed portion 300 -> variable spent = 100
    assert travel_analytics.variable_travel_remaining == 400.0


def test_travel_recommended_daily_matches_brief_example(db, demo_budget):
    """From the brief: variable budget 500, 20 days remaining -> ₹25/day."""
    as_of = date(2026, 8, 12)  # 31 - 12 + 1 = 20 days remaining
    assert days_remaining("2026-08", as_of) == 20

    travel_analytics = analytics_service.compute_travel_analytics(db, demo_budget, as_of=as_of)
    assert travel_analytics.variable_travel_remaining == 500.0
    assert travel_analytics.recommended_daily_spending == 25.0


def test_travel_exhaustion_projection_when_overspending(db, demo_budget):
    # 20 days remaining (inclusive) x ₹25/day estimate == ₹500 variable budget exactly
    as_of = date(2026, 8, 12)
    travel_analytics = analytics_service.compute_travel_analytics(db, demo_budget, as_of=as_of)
    assert travel_analytics.estimated_daily_travel == 25.0
    assert travel_analytics.budget_sufficient is True

    # Now push estimate higher than what the remaining budget can sustain.
    demo_budget.categories[1].estimated_daily_amount = 40
    db.commit()
    travel_analytics_over = analytics_service.compute_travel_analytics(db, demo_budget, as_of=as_of)
    assert travel_analytics_over.budget_sufficient is False
    assert travel_analytics_over.required_daily_reduction is not None
    assert travel_analytics_over.required_daily_reduction > 0


def test_first_day_of_month_edge_case(db, demo_budget):
    as_of = date(2026, 8, 1)
    assert days_elapsed("2026-08", as_of) == 1
    summary = analytics_service.compute_budget_summary(db, demo_budget, as_of=as_of)
    assert summary.days_elapsed == 1
    assert summary.days_remaining == 31


def test_last_day_of_month_edge_case(db, demo_budget):
    as_of = date(2026, 8, 31)
    assert days_remaining("2026-08", as_of) == 1
    summary = analytics_service.compute_budget_summary(db, demo_budget, as_of=as_of)
    assert summary.days_remaining == 1


def test_total_days_in_period():
    assert total_days_in_period("2026-08") == 31
    assert total_days_in_period("2026-02") == 28  # 2026 is not a leap year


def test_forecast_transparent_linear_method(db, demo_budget):
    as_of = date(2026, 8, 10)
    food = demo_budget.categories[0]
    for d in range(1, 6):
        _add_expense(db, demo_budget, food, 50, date(2026, 8, d))
    db.refresh(demo_budget)

    forecast = forecast_service.generate_forecast(db, demo_budget, as_of=as_of)
    assert forecast.method in ("linear_average", "recency_weighted_average")
    assert forecast.projected_monthly_spending > 0
    assert "explanation" not in forecast.model_fields or forecast.explanation  # explanation present
    assert isinstance(forecast.explanation, str) and len(forecast.explanation) > 0
