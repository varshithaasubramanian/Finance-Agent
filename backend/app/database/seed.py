"""
Demo/sample data seeding.

Creates the demo user, a budget for the current month (Total = 2000,
Food = 1000, Travel = 800, Others = 200 -- matching the project brief's
example) with a realistic spread of sample expenses, one recurring
expense, and one financial goal, so the dashboard is immediately
demonstrative on first run.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import models
from app.services import budget_service, category_service
from app.utils.date_utils import current_period, days_elapsed


def seed_demo_data(db: Session) -> None:
    user = budget_service.get_or_create_demo_user(db)

    period = current_period()
    existing = budget_service.get_current_budget(db, user)
    if existing:
        return  # already seeded

    budget = models.Budget(user_id=user.id, period=period, total_amount=2000, allow_over_allocation=True)
    db.add(budget)
    db.flush()

    food = models.Category(budget_id=budget.id, name="Food", allocation=1000, color="#0F766E", icon="utensils")
    travel = models.Category(
        budget_id=budget.id,
        name="Travel",
        allocation=800,
        color="#2563EB",
        icon="bus",
        is_travel=True,
        fixed_amount=300,
        estimated_daily_amount=40,
    )
    others = models.Category(budget_id=budget.id, name="Others", allocation=200, color="#64748B", icon="dots")
    education = models.Category(budget_id=budget.id, name="Education", allocation=0, color="#7C3AED", icon="book")
    entertainment = models.Category(budget_id=budget.id, name="Entertainment", allocation=0, color="#EA580C", icon="film")

    db.add_all([food, travel, others, education, entertainment])
    db.flush()

    today = date.today()
    elapsed = max(days_elapsed(period, today), 1)
    span = min(elapsed, 14)  # up to the last 14 elapsed days
    start = today - timedelta(days=span - 1)

    sample_expenses = []
    food_items = [
        (120, "Lunch at canteen"),
        (60, "Chai and snacks"),
        (250, "Dinner with friends"),
        (80, "Breakfast"),
        (150, "Groceries"),
    ]
    travel_items = [
        (25, "Auto to college"),
        (40, "Cab ride"),
        (20, "Bus fare"),
        (300, "Monthly bus pass", 0),  # fixed, added on day 0 below explicitly
    ]
    other_items = [
        (50, "Stationery"),
        (100, "Gift"),
    ]

    day_cursor = start
    fi, ti, oi = 0, 0, 0
    for i in range(span):
        d = day_cursor + timedelta(days=i)
        if i % 2 == 0 and fi < len(food_items):
            amt, desc = food_items[fi]
            sample_expenses.append(models.Expense(budget_id=budget.id, category_id=food.id, amount=amt, description=desc, date=d, payment_method=models.PaymentMethod.UPI))
            fi += 1
        if i % 3 == 0 and ti < 3:
            amt, desc = travel_items[ti]
            sample_expenses.append(models.Expense(budget_id=budget.id, category_id=travel.id, amount=amt, description=desc, date=d, payment_method=models.PaymentMethod.CASH))
            ti += 1
        if i % 5 == 0 and oi < len(other_items):
            amt, desc = other_items[oi]
            sample_expenses.append(models.Expense(budget_id=budget.id, category_id=others.id, amount=amt, description=desc, date=d, payment_method=models.PaymentMethod.OTHER))
            oi += 1

    # The fixed monthly bus pass, dated the 1st of the period
    from app.utils.date_utils import period_bounds

    first_day, _ = period_bounds(period)
    sample_expenses.append(
        models.Expense(
            budget_id=budget.id,
            category_id=travel.id,
            amount=300,
            description="Monthly bus pass",
            date=first_day,
            payment_method=models.PaymentMethod.UPI,
            notes="Fixed recurring travel cost",
        )
    )

    db.add_all(sample_expenses)

    # One recurring expense and one financial goal for demonstration
    db.add(
        models.RecurringExpense(
            budget_id=budget.id,
            category_id=others.id,
            name="Phone recharge",
            amount=199,
            frequency=models.RecurrenceFrequency.MONTHLY,
            next_due_date=first_day + timedelta(days=20),
        )
    )
    db.add(
        models.FinancialGoal(
            user_id=user.id,
            name="Buy headphones",
            target_amount=3000,
            current_amount=1200,
            deadline=today + timedelta(days=30),
        )
    )

    db.commit()
