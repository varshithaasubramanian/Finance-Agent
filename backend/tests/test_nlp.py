from datetime import date, timedelta

import pytest

from app.ai.nlp_parser import fallback_parse


def test_parses_amount_category_description():
    result = fallback_parse("Spent 60 on auto to college")
    assert result.amount == 60.0
    assert result.category == "Travel"
    assert result.source == "fallback"


def test_parses_rupee_symbol_and_lunch():
    result = fallback_parse("I spent \u20b9120 on lunch")
    assert result.amount == 120.0
    assert result.category == "Food"
    assert "lunch" in result.description.lower()


def test_parses_yesterday_relative_date():
    result = fallback_parse("Yesterday I paid 250 for dinner")
    assert result.amount == 250.0
    expected = (date.today() - timedelta(days=1)).isoformat()
    assert result.date == expected
    assert result.category == "Food"


def test_defaults_to_today_when_no_date_mentioned():
    result = fallback_parse("Paid 40 for coffee")
    assert result.date == date.today().isoformat()


def test_unknown_category_falls_back_to_others():
    result = fallback_parse("Spent 500 on random stuff")
    assert result.category == "Others"


def test_detects_payment_method_when_present():
    result = fallback_parse("Paid 90 via UPI for snacks")
    assert result.payment_method is not None
    assert result.payment_method.value == "UPI"


def test_raises_when_no_amount_found():
    with pytest.raises(ValueError):
        fallback_parse("Bought some snacks")
