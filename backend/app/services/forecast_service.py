"""
Forecasting service.

Primary method ("linear_average"): projected_monthly_spending =
    (total_spent_so_far / days_elapsed) * total_days_in_period
This is always computed and always explainable in one sentence.

Secondary method ("recency_weighted"): if at least MIN_DATA_POINTS distinct
days of spending exist, a lightweight statistical refinement is layered on
top using pandas/numpy: recent days are weighted more heavily than early
days, which reacts faster to a recent change in spending habits than a flat
average. This is NOT a machine-learning model (no training, no black box) --
it is a transparent weighted average that the app can explain in plain
language, per the project's forecasting requirements.
"""
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.services import analytics_service, recurring_service
from app.utils.date_utils import days_elapsed, days_remaining, period_bounds, total_days_in_period
from app.utils.decimal_utils import D, round2, safe_div

MIN_DATA_POINTS = 5


def _daily_series(db: Session, budget: models.Budget) -> pd.Series:
    trends = analytics_service.spending_trends(db, budget)
    if not trends:
        return pd.Series(dtype=float)
    idx = [t.date for t in trends]
    vals = [t.amount for t in trends]
    return pd.Series(vals, index=pd.to_datetime(idx))


def _recency_weighted_daily_average(series: pd.Series) -> float | None:
    if len(series) < MIN_DATA_POINTS:
        return None
    values = series.to_numpy(dtype=float)
    n = len(values)
    # Linearly increasing weights: most recent day weighted ~2x the oldest.
    weights = np.linspace(1.0, 2.0, n)
    weighted_avg = float(np.average(values, weights=weights))
    return weighted_avg


def generate_forecast(db: Session, budget: models.Budget, as_of: date | None = None) -> schemas.ForecastOut:
    as_of = as_of or date.today()
    summary = analytics_service.compute_budget_summary(db, budget, as_of)
    total_days = total_days_in_period(budget.period)
    elapsed = max(days_elapsed(budget.period, as_of), 1)
    remaining_days = days_remaining(budget.period, as_of)

    linear_daily_avg = D(summary.daily_average_spending)
    linear_projection = linear_daily_avg * D(total_days)

    method = "linear_average"
    explanation = (
        f"Based on an average of {summary.currency_symbol}{summary.daily_average_spending}/day "
        f"spent over {elapsed} day(s) so far, projected spending for all {total_days} days "
        f"of the period is {summary.currency_symbol}{round2(linear_projection)}."
    )
    projected = linear_projection

    series = _daily_series(db, budget)
    weighted_avg = _recency_weighted_daily_average(series)
    if weighted_avg is not None:
        weighted_projection = D(weighted_avg) * D(total_days)
        method = "recency_weighted_average"
        explanation = (
            f"Using a recency-weighted average of your last {len(series)} days of spending "
            f"(recent days count more than earlier ones), your daily spending rate is about "
            f"{summary.currency_symbol}{round2(weighted_avg)}/day, projecting to "
            f"{summary.currency_symbol}{round2(weighted_projection)} across all {total_days} days."
        )
        projected = weighted_projection

    # Add known committed recurring expenses still due this period.
    committed = recurring_service.project_committed_amount(db, budget, as_of)
    if committed > 0:
        projected += committed
        explanation += (
            f" This includes {summary.currency_symbol}{round2(committed)} in known upcoming "
            f"recurring expenses."
        )

    surplus_deficit = D(budget.total_amount) - projected

    category_forecasts = []
    exhaustion_date = None
    for cat in budget.categories:
        cat_analytics = analytics_service.compute_category_analytics(db, budget, cat, as_of)
        cat_committed = recurring_service.project_committed_amount(db, budget, as_of, category_id=cat.id)
        cat_projected = D(cat_analytics.projected_spending) + cat_committed
        cat_allocation = D(cat.allocation)

        cat_exhaustion = None
        remaining_amt = cat_allocation - D(cat_analytics.spent)
        daily_rate = D(cat_analytics.daily_average)
        if daily_rate > 0 and remaining_amt > 0:
            days_to_exhaust = int(safe_div(remaining_amt, daily_rate))
            candidate = as_of + timedelta(days=days_to_exhaust)
            _, period_end = period_bounds(budget.period)
            if candidate <= period_end:
                cat_exhaustion = candidate.isoformat()
        elif daily_rate > 0 and remaining_amt <= 0:
            cat_exhaustion = as_of.isoformat()

        category_forecasts.append(
            {
                "category_id": cat.id,
                "name": cat.name,
                "allocation": round2(cat_allocation),
                "projected_spending": round2(cat_projected),
                "projected_surplus_deficit": round2(cat_allocation - cat_projected),
                "expected_exhaustion_date": cat_exhaustion,
            }
        )

    # Overall budget exhaustion date (based on linear/weighted daily rate)
    daily_rate_overall = D(weighted_avg) if weighted_avg is not None else linear_daily_avg
    if daily_rate_overall > 0 and summary.total_remaining > 0:
        days_to_exhaust = int(safe_div(D(summary.total_remaining), daily_rate_overall))
        candidate = as_of + timedelta(days=days_to_exhaust)
        _, period_end = period_bounds(budget.period)
        if candidate <= period_end:
            exhaustion_date = candidate
    elif daily_rate_overall > 0 and summary.total_remaining <= 0:
        exhaustion_date = as_of

    return schemas.ForecastOut(
        method=method,
        explanation=explanation,
        projected_monthly_spending=round2(projected),
        projected_surplus_deficit=round2(surplus_deficit),
        category_forecasts=category_forecasts,
        expected_exhaustion_date=exhaustion_date,
    )
