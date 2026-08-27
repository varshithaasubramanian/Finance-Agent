"""
Decimal-safe monetary helpers.

All financial arithmetic in the services layer routes through these
helpers to avoid floating point rounding artefacts (e.g. 0.1 + 0.2).
API boundaries convert Decimal -> float only at the very end, rounded to
2 decimal places.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import Union

Number = Union[int, float, str, Decimal, None]

TWO_PLACES = Decimal("0.01")


def D(value: Number) -> Decimal:
    """Safely coerce any numeric-ish input into a Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    # Route through str() to avoid binary float artefacts (e.g. Decimal(0.1))
    return Decimal(str(value))


def round2(value: Number) -> float:
    """Round a Decimal-ish value to 2 decimal places and return a float
    suitable for JSON serialization."""
    d = D(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return float(d)


def safe_div(numerator: Number, denominator: Number, default: Number = 0) -> Decimal:
    """Division that never raises ZeroDivisionError."""
    n, d = D(numerator), D(denominator)
    if d == 0:
        return D(default)
    return n / d


def pct(numerator: Number, denominator: Number) -> float:
    """Percentage (0-100+) as a float rounded to 2 decimals."""
    if D(denominator) == 0:
        return 0.0
    return round2(safe_div(numerator, denominator) * D(100))
