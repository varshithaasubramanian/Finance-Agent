"""
'Can I afford this?' feature.

Purely deterministic: analyses remaining total budget, the relevant
category budget, days remaining, current spending rate, projected
spending and known recurring/committed expenses, then returns a
Yes/No/Caution verdict with a plain-language explanation.

No investment advice is given -- this module only ever reasons about
budgeting/expense tracking.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.services import analytics_service, recurring_service
from app.utils.date_utils import days_remaining
from app.utils.decimal_utils import D, round2, safe_div


def evaluate_affordability(
    db: Session,
    budget: models.Budget,
    amount: float,
    category_id: str | None = None,
    as_of: date | None = None,
) -> schemas.AffordabilityResponse:
    as_of = as_of or date.today()
    amount_d = D(amount)

    summary = analytics_service.compute_budget_summary(db, budget, as_of)
    committed = recurring_service.project_committed_amount(db, budget, as_of)

    remaining_total = D(summary.total_remaining) - committed
    remaining_after = remaining_total - amount_d

    remaining_days = max(days_remaining(budget.period, as_of), 1)
    safe_daily = safe_div(remaining_total, remaining_days)

    category = None
    cat_remaining_before = None
    cat_remaining_after = None
    if category_id:
        category = db.get(models.Category, category_id)

    verdict = "Yes"
    reasons: list[str] = []

    if remaining_after < 0:
        verdict = "No"
        reasons.append(
            f"Spending {summary.currency_symbol}{round2(amount_d)} would take your overall remaining "
            f"budget negative (to {summary.currency_symbol}{round2(remaining_after)})."
        )
    elif remaining_after < safe_daily * 3:
        verdict = "Caution"
        reasons.append(
            f"After this purchase you would have {summary.currency_symbol}{round2(remaining_after)} left "
            f"for the remaining {remaining_days} day(s), which is tight relative to your recommended "
            f"safe daily spending of {summary.currency_symbol}{round2(safe_daily)}/day."
        )
    else:
        reasons.append(
            f"You would still have {summary.currency_symbol}{round2(remaining_after)} of your overall "
            f"budget remaining after this purchase."
        )

    if category is not None:
        cat_spent = analytics_service.category_spent(db, category.id)
        cat_allocation = D(category.allocation)
        cat_remaining_before = cat_allocation - cat_spent
        cat_remaining_after = cat_remaining_before - amount_d

        if cat_remaining_after < 0:
            if verdict == "Yes":
                verdict = "Caution"
            reasons.append(
                f"This would put your {category.name} category "
                f"{summary.currency_symbol}{round2(abs(cat_remaining_after))} over its allocated budget "
                f"of {summary.currency_symbol}{round2(cat_allocation)}."
            )
        elif cat_allocation > 0 and safe_div(cat_remaining_after, cat_allocation) < Decimal("0.1"):
            if verdict == "Yes":
                verdict = "Caution"
            reasons.append(
                f"It would leave only {summary.currency_symbol}{round2(cat_remaining_after)} in your "
                f"{category.name} category for the rest of the period."
            )
        else:
            reasons.append(
                f"Your {category.name} category would have "
                f"{summary.currency_symbol}{round2(cat_remaining_after)} remaining."
            )

    recommended_limit = max(safe_daily * remaining_days * Decimal("0.9"), Decimal("0"))

    explanation = " ".join(reasons)

    return schemas.AffordabilityResponse(
        verdict=verdict,  # type: ignore[arg-type]
        amount=round2(amount_d),
        remaining_total_after=round2(remaining_after),
        category_name=category.name if category else None,
        category_remaining_before=round2(cat_remaining_before) if cat_remaining_before is not None else None,
        category_remaining_after=round2(cat_remaining_after) if cat_remaining_after is not None else None,
        recommended_spending_limit=round2(recommended_limit),
        explanation=explanation,
    )
