"""Date helpers for budget period math (elapsed days, remaining days, etc.)."""
import calendar
from datetime import date, datetime, timedelta


def parse_period(period: str) -> tuple[int, int]:
    """'2026-08' -> (2026, 8)"""
    year_str, month_str = period.split("-")
    return int(year_str), int(month_str)


def period_bounds(period: str) -> tuple[date, date]:
    """Return (first_day, last_day) of the given YYYY-MM period."""
    year, month = parse_period(period)
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


def total_days_in_period(period: str) -> int:
    first, last = period_bounds(period)
    return (last - first).days + 1


def days_elapsed(period: str, as_of: date | None = None) -> int:
    """Number of days elapsed in the period, inclusive of today, clamped to
    the period's bounds. Day 1 of the month returns 1 (not 0), so that
    'average daily spending' is well-defined from the first day."""
    as_of = as_of or date.today()
    first, last = period_bounds(period)
    if as_of < first:
        return 0
    if as_of > last:
        return total_days_in_period(period)
    return (as_of - first).days + 1


def days_remaining(period: str, as_of: date | None = None) -> int:
    """Days left in the period INCLUDING today. Never negative."""
    as_of = as_of or date.today()
    first, last = period_bounds(period)
    if as_of > last:
        return 0
    if as_of < first:
        return total_days_in_period(period)
    return (last - as_of).days + 1


def current_period(as_of: date | None = None) -> str:
    as_of = as_of or date.today()
    return f"{as_of.year:04d}-{as_of.month:02d}"


def resolve_relative_date(term: str, as_of: date | None = None) -> date:
    """Resolve simple relative date terms used in natural-language expense
    entry: 'today', 'yesterday', 'tomorrow'. Falls back to today for
    anything unrecognized (the parser should pass real ISO dates through
    untouched before reaching here)."""
    as_of = as_of or date.today()
    term = term.strip().lower()
    if term in ("today", ""):
        return as_of
    if term == "yesterday":
        return as_of - timedelta(days=1)
    if term == "tomorrow":
        return as_of + timedelta(days=1)
    try:
        return datetime.strptime(term, "%Y-%m-%d").date()
    except ValueError:
        return as_of
