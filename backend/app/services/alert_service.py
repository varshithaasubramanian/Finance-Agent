"""
Spending alert engine.

Generates INFO/WARNING/CRITICAL alerts from the deterministic analytics
engine's output. Alerts are computed on demand (not polled) and are also
persisted as AIInsight rows with source="rules" so the dashboard has a
history to show.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.services import analytics_service
from app.utils.date_utils import days_elapsed, total_days_in_period
from app.utils.decimal_utils import D, pct


def generate_alerts(db: Session, budget: models.Budget, as_of: date | None = None) -> list[schemas.AlertOut]:
    as_of = as_of or date.today()
    alerts: list[schemas.AlertOut] = []
    summary = analytics_service.compute_budget_summary(db, budget, as_of)

    total_days = total_days_in_period(budget.period)
    elapsed = days_elapsed(budget.period, as_of)
    time_elapsed_pct = pct(elapsed, total_days)

    # ---- Category-level thresholds -------------------------------------
    for cat in summary.categories:
        if cat.allocation <= 0:
            continue
        used = cat.percent_used

        if used > 100:
            alerts.append(
                schemas.AlertOut(
                    severity=schemas.SeverityEnum.CRITICAL,
                    category=cat.name,
                    message=(
                        f"You have exceeded your {cat.name} budget by "
                        f"{summary.currency_symbol}{round(cat.spent - cat.allocation, 2)}."
                    ),
                    metric={"percent_used": used, "spent": cat.spent, "allocation": cat.allocation},
                )
            )
        elif used >= 90:
            alerts.append(
                schemas.AlertOut(
                    severity=schemas.SeverityEnum.CRITICAL,
                    category=cat.name,
                    message=f"You have used {used}% of your {cat.name} budget.",
                    metric={"percent_used": used},
                )
            )
        elif used >= 75:
            severity = schemas.SeverityEnum.WARNING
            if used >= 75 and time_elapsed_pct < used:
                alerts.append(
                    schemas.AlertOut(
                        severity=severity,
                        category=cat.name,
                        message=(
                            f"You have used {used}% of your {cat.name} budget but only "
                            f"{time_elapsed_pct}% of the period has elapsed."
                        ),
                        metric={"percent_used": used, "time_elapsed_percent": time_elapsed_pct},
                    )
                )
            else:
                alerts.append(
                    schemas.AlertOut(
                        severity=severity,
                        category=cat.name,
                        message=f"You have used {used}% of your {cat.name} budget.",
                        metric={"percent_used": used},
                    )
                )
        elif used >= 50:
            alerts.append(
                schemas.AlertOut(
                    severity=schemas.SeverityEnum.INFO,
                    category=cat.name,
                    message=f"You have used {used}% of your {cat.name} budget.",
                    metric={"percent_used": used},
                )
            )

        # Spending rate significantly ahead of the elapsed-time pace
        if used - time_elapsed_pct >= 20 and used < 90:
            alerts.append(
                schemas.AlertOut(
                    severity=schemas.SeverityEnum.WARNING,
                    category=cat.name,
                    message=(
                        f"Your {cat.name} spending is pacing well ahead of the month: "
                        f"{used}% spent vs {time_elapsed_pct}% of days elapsed."
                    ),
                    metric={"percent_used": used, "time_elapsed_percent": time_elapsed_pct},
                )
            )

        # Category-level projection exceeding allocation
        if cat.projected_surplus_deficit < 0:
            alerts.append(
                schemas.AlertOut(
                    severity=schemas.SeverityEnum.WARNING,
                    category=cat.name,
                    message=(
                        f"At your current pace, {cat.name} spending may exceed its budget by "
                        f"{summary.currency_symbol}{abs(cat.projected_surplus_deficit)} by month end."
                    ),
                    metric={"projected_surplus_deficit": cat.projected_surplus_deficit},
                )
            )

        # Category daily spending vs recommended allowance (using spending_limit if set)
        cat_model = next((c for c in budget.categories if c.id == cat.category_id), None)
        if cat_model and cat_model.spending_limit and cat.daily_average > float(D(cat_model.spending_limit)):
            alerts.append(
                schemas.AlertOut(
                    severity=schemas.SeverityEnum.WARNING,
                    category=cat.name,
                    message=(
                        f"Your average daily {cat.name} spending "
                        f"({summary.currency_symbol}{cat.daily_average}) exceeds your set limit of "
                        f"{summary.currency_symbol}{cat_model.spending_limit}/day."
                    ),
                    metric={"daily_average": cat.daily_average, "limit": float(D(cat_model.spending_limit))},
                )
            )

    # ---- Budget-wide thresholds -----------------------------------------
    if summary.percent_used > 100:
        alerts.append(
            schemas.AlertOut(
                severity=schemas.SeverityEnum.CRITICAL,
                category="overall",
                message=(
                    f"You have exceeded your total monthly budget by "
                    f"{summary.currency_symbol}{round(summary.total_spent - summary.total_budget, 2)}."
                ),
                metric={"percent_used": summary.percent_used},
            )
        )
    elif summary.projected_surplus_deficit < 0:
        alerts.append(
            schemas.AlertOut(
                severity=schemas.SeverityEnum.WARNING,
                category="overall",
                message=(
                    f"Projected monthly spending exceeds your total budget by "
                    f"{summary.currency_symbol}{abs(summary.projected_surplus_deficit)}."
                ),
                metric={"projected_surplus_deficit": summary.projected_surplus_deficit},
            )
        )

    if summary.daily_average_spending > summary.recommended_safe_daily_spending and summary.recommended_safe_daily_spending > 0:
        alerts.append(
            schemas.AlertOut(
                severity=schemas.SeverityEnum.INFO,
                category="overall",
                message=(
                    f"Your average daily spending ({summary.currency_symbol}{summary.daily_average_spending}) "
                    f"is above today's recommended safe daily spending "
                    f"({summary.currency_symbol}{summary.recommended_safe_daily_spending})."
                ),
                metric={
                    "daily_average": summary.daily_average_spending,
                    "safe_daily": summary.recommended_safe_daily_spending,
                },
            )
        )

    return alerts


def persist_alerts(db: Session, budget: models.Budget, alerts: list[schemas.AlertOut]) -> None:
    for alert in alerts:
        db.add(
            models.AIInsight(
                budget_id=budget.id,
                category=alert.category,
                severity=models.AlertSeverity(alert.severity.value),
                message=alert.message,
                source="rules",
            )
        )
    db.commit()
