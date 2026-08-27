"""
Natural language expense entry parsing.

Tries the AI client first (structured JSON output matching ParsedExpense).
If AI is disabled or the call fails for any reason, falls back to a
deterministic regex/keyword parser so expense entry never breaks.
"""
import re
from datetime import date

from app.ai.ai_client import get_ai_client
from app.schemas.schemas import ParsedExpense, PaymentMethodEnum
from app.utils.date_utils import resolve_relative_date

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Food": ["lunch", "dinner", "breakfast", "food", "snack", "restaurant", "coffee", "tea", "meal", "canteen", "pizza", "burger", "grocery", "groceries"],
    "Travel": ["auto", "bus", "cab", "taxi", "uber", "ola", "train", "metro", "fuel", "petrol", "diesel", "travel", "ride", "flight", "parking"],
    "Education": ["book", "books", "course", "tuition", "fees", "fee", "stationery", "exam", "class"],
    "Shopping": ["shirt", "shoes", "clothes", "shopping", "amazon", "flipkart", "mall", "bag", "gadget"],
    "Entertainment": ["movie", "netflix", "spotify", "game", "concert", "party", "outing"],
    "Bills": ["bill", "electricity", "rent", "recharge", "wifi", "internet", "water bill", "subscription"],
    "Health": ["medicine", "doctor", "hospital", "pharmacy", "health", "gym"],
}

PAYMENT_KEYWORDS: dict[PaymentMethodEnum, list[str]] = {
    PaymentMethodEnum.UPI: ["upi", "gpay", "google pay", "phonepe", "paytm"],
    PaymentMethodEnum.CASH: ["cash"],
    PaymentMethodEnum.DEBIT_CARD: ["debit card", "debit"],
    PaymentMethodEnum.CREDIT_CARD: ["credit card", "credit"],
    PaymentMethodEnum.BANK_TRANSFER: ["bank transfer", "neft", "imps", "rtgs"],
}

AMOUNT_PATTERN = re.compile(r"(?:₹|rs\.?|inr)?\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:₹|rs\.?|inr)?", re.IGNORECASE)


def _extract_amount(text: str) -> float | None:
    for match in AMOUNT_PATTERN.finditer(text):
        raw = match.group(1).replace(",", "")
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            continue
    return None


def _extract_category(text: str) -> str:
    lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return category
    return "Others"


def _extract_payment_method(text: str) -> PaymentMethodEnum | None:
    lower = text.lower()
    for method, keywords in PAYMENT_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return method
    return None


def _extract_date(text: str) -> str:
    lower = text.lower()
    if "yesterday" in lower:
        return resolve_relative_date("yesterday").isoformat()
    if "tomorrow" in lower:
        return resolve_relative_date("tomorrow").isoformat()
    return resolve_relative_date("today").isoformat()


def _extract_description(text: str, amount: float | None) -> str:
    cleaned = text
    cleaned = re.sub(r"^(i\s+)?(spent|paid|bought|got)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(₹|rs\.?|inr)?\s*[0-9]+(?:[.,][0-9]{1,2})?\s*(₹|rs\.?|inr)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(yesterday|today|tomorrow)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(on|for|via|using|by)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    return cleaned.capitalize() if cleaned else "Expense"


def fallback_parse(text: str) -> ParsedExpense:
    """Deterministic keyword/regex parser used whenever AI is unavailable."""
    amount = _extract_amount(text)
    if amount is None:
        raise ValueError("Could not find an amount in the text. Try including a number, e.g. 'spent 120 on lunch'.")

    category = _extract_category(text)
    payment_method = _extract_payment_method(text)
    date_str = _extract_date(text)
    description = _extract_description(text, amount)

    return ParsedExpense(
        amount=amount,
        category=category,
        description=description,
        date=date_str,
        payment_method=payment_method,
        confidence=0.6,
        source="fallback",
    )


PARSE_SYSTEM_PROMPT = """You extract structured expense data from short, casual natural-language messages about personal spending (often Indian English/Hinglish, amounts in INR).

Respond ONLY with a single JSON object with EXACTLY these keys, no prose, no markdown fences:
{
  "amount": <number>,
  "category": <one of: Food, Travel, Education, Shopping, Entertainment, Bills, Health, Others>,
  "description": <short human-readable description, capitalized>,
  "date": <"today", "yesterday", "tomorrow", or an ISO date YYYY-MM-DD>,
  "payment_method": <one of: Cash, UPI, Debit Card, Credit Card, Bank Transfer, Other, or null if not mentioned>,
  "confidence": <number between 0 and 1 reflecting how sure you are>
}"""


def ai_parse(text: str) -> ParsedExpense | None:
    client = get_ai_client()
    if not client.enabled:
        return None

    result = client.structured_json(system_prompt=PARSE_SYSTEM_PROMPT, user_message=text, max_tokens=300)
    if not result:
        return None

    try:
        date_value = result.get("date") or "today"
        if date_value not in ("today", "yesterday", "tomorrow"):
            # assume ISO date already; resolve_relative_date passes it through
            date_value = resolve_relative_date(date_value).isoformat()
        else:
            date_value = resolve_relative_date(date_value).isoformat()

        payment_method = result.get("payment_method")
        pm_enum = None
        if payment_method:
            try:
                pm_enum = PaymentMethodEnum(payment_method)
            except ValueError:
                pm_enum = None

        return ParsedExpense(
            amount=float(result["amount"]),
            category=str(result.get("category") or "Others"),
            description=str(result.get("description") or "Expense"),
            date=date_value,
            payment_method=pm_enum,
            confidence=float(result.get("confidence", 0.8)),
            source="ai",
        )
    except (KeyError, ValueError, TypeError):
        return None


def parse_expense_text(text: str) -> ParsedExpense:
    """Public entry point: try AI, gracefully fall back to the deterministic
    parser on any failure so expense entry always works."""
    try:
        parsed = ai_parse(text)
        if parsed:
            return parsed
    except Exception:
        pass
    return fallback_parse(text)
