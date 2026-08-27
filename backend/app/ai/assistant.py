"""
The AI Financial Assistant.

When AI is enabled, this runs a standard Anthropic tool-use loop: the model
is given the tool schemas from app.ai.tools, may request one or more tool
calls, we execute them against the deterministic engine, feed the results
back, and let the model produce a final natural-language answer. The model
is instructed never to invent numbers.

When AI is disabled (no API key configured), a deterministic fallback
answers the most common question patterns ("how much can I spend today",
"am I overspending on X", "can I afford X", etc.) directly from the
calculation engine using keyword/regex matching, so the assistant page is
always useful.
"""
import re
from typing import Any

from sqlalchemy.orm import Session

from app.ai.ai_client import get_ai_client
from app.ai.tools import ANTHROPIC_TOOL_SCHEMAS, TOOL_FUNCTIONS, _find_category
from app.models import models
from app.schemas import schemas
from app.services import affordability_service, alert_service, analytics_service, forecast_service

SYSTEM_PROMPT = """You are a careful personal-finance assistant embedded in a budgeting app.

Rules you MUST follow:
1. You NEVER calculate or state a financial number (amounts, percentages, dates, counts) from your own reasoning. ALWAYS call the appropriate tool to retrieve real data first, then explain it in plain language.
2. Keep answers concise (2-5 sentences) and use the currency symbol from the tool results.
3. You do not give investment, stock, or trading advice. This app is for budgeting and expense tracking only -- if asked about investing, politely redirect to budgeting topics.
4. If asked to log/add/record an expense, confirm the key details you are about to log, then call create_expense.
5. Be encouraging but honest about overspending; do not sugar-coat critical situations.
"""

MAX_TOOL_ITERATIONS = 4


def _run_tool(db: Session, budget: models.Budget, name: str, tool_input: dict) -> dict:
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return {"error": f"Unknown tool {name}"}
    try:
        return fn(db, budget, **tool_input)
    except Exception as exc:  # pragma: no cover - defensive
        return {"error": str(exc)}


def _ai_assistant_reply(db: Session, budget: models.Budget, message: str) -> schemas.AssistantResponse | None:
    client = get_ai_client()
    if not client.enabled:
        return None

    messages: list[dict] = [{"role": "user", "content": message}]
    tool_calls_log: list[dict] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.converse_with_tools(SYSTEM_PROMPT, messages, ANTHROPIC_TOOL_SCHEMAS)
        if response is None:
            return None

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text").strip()
            if not text:
                return None
            return schemas.AssistantResponse(reply=text, source="ai", tool_calls=tool_calls_log)

        # Model wants to use one or more tools.
        assistant_content = [b.model_dump() for b in response.content]
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                result = _run_tool(db, budget, block.name, block.input or {})
                tool_calls_log.append({"tool": block.name, "input": block.input, "result": result})
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return schemas.AssistantResponse(
        reply="I gathered the numbers but ran out of turns to summarize them. Please try rephrasing your question.",
        source="ai",
        tool_calls=tool_calls_log,
    )


# --------------------------------------------------------- fallback rules
AFFORD_PATTERN = re.compile(r"(?:afford|spend)\D{0,15}?(\d+(?:\.\d{1,2})?)", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"(\d+(?:\.\d{1,2})?)")


def _fallback_reply(db: Session, budget: models.Budget, message: str) -> schemas.AssistantResponse:
    lower = message.lower()
    currency = budget.user.currency_symbol if budget.user else "\u20b9"

    # "can I spend/afford X [on category]?"
    afford_match = AFFORD_PATTERN.search(lower)
    if afford_match and ("afford" in lower or "can i spend" in lower or "can i buy" in lower):
        amount = float(afford_match.group(1))
        category = None
        for cat in budget.categories:
            if cat.name.lower() in lower:
                category = cat
                break
        result = affordability_service.evaluate_affordability(
            db, budget, amount=amount, category_id=category.id if category else None
        )
        reply = f"{result.verdict}. {result.explanation}"
        return schemas.AssistantResponse(reply=reply, source="fallback")

    if "how much" in lower and ("left" in lower or "remaining" in lower):
        summary = analytics_service.compute_budget_summary(db, budget)
        reply = (
            f"You have {currency}{summary.total_remaining} remaining out of your {currency}{summary.total_budget} "
            f"budget ({summary.percent_used}% used, {summary.days_remaining} day(s) left)."
        )
        return schemas.AssistantResponse(reply=reply, source="fallback")

    if "today" in lower and ("spend" in lower or "budget" in lower):
        summary = analytics_service.compute_budget_summary(db, budget)
        reply = (
            f"Your recommended safe spending for today is about {currency}{summary.recommended_safe_daily_spending}, "
            f"based on {currency}{summary.total_remaining} remaining across {summary.days_remaining} day(s)."
        )
        return schemas.AssistantResponse(reply=reply, source="fallback")

    if "overspend" in lower or "over budget" in lower or "over-spending" in lower:
        category = None
        for cat in budget.categories:
            if cat.name.lower() in lower:
                category = cat
                break
        if category:
            analytics = analytics_service.compute_category_analytics(db, budget, category)
            if analytics.percent_used > 100:
                reply = f"Yes, you've exceeded your {category.name} budget by {currency}{round(analytics.spent - analytics.allocation, 2)}."
            elif analytics.projected_surplus_deficit < 0:
                reply = (
                    f"Not yet, but at your current pace you're projected to overspend {category.name} by "
                    f"{currency}{abs(analytics.projected_surplus_deficit)} by month end."
                )
            else:
                reply = f"No, {category.name} is on track: {analytics.percent_used}% of its budget used so far."
            return schemas.AssistantResponse(reply=reply, source="fallback")
        else:
            alerts = alert_service.generate_alerts(db, budget)
            problem_alerts = [a for a in alerts if a.severity in (schemas.SeverityEnum.WARNING, schemas.SeverityEnum.CRITICAL)]
            if problem_alerts:
                reply = " ".join(a.message for a in problem_alerts[:3])
            else:
                reply = "You're not overspending in any category right now -- everything is tracking within budget."
            return schemas.AssistantResponse(reply=reply, source="fallback")

    if "most" in lower and ("spend" in lower or "category" in lower):
        summary = analytics_service.compute_budget_summary(db, budget)
        if summary.categories:
            top = max(summary.categories, key=lambda c: c.spent)
            reply = f"You're spending the most on {top.name}: {currency}{top.spent} so far ({top.percent_used}% of its budget)."
        else:
            reply = "You don't have any categories set up yet."
        return schemas.AssistantResponse(reply=reply, source="fallback")

    if "exceed" in lower and "budget" in lower:
        forecast = forecast_service.generate_forecast(db, budget)
        if forecast.projected_surplus_deficit < 0:
            reply = (
                f"Yes, at your current pace you're projected to exceed your budget by "
                f"{currency}{abs(forecast.projected_surplus_deficit)}. {forecast.explanation}"
            )
        else:
            reply = f"No, you're projected to stay within budget with a surplus of {currency}{forecast.projected_surplus_deficit}. {forecast.explanation}"
        return schemas.AssistantResponse(reply=reply, source="fallback")

    if "travel" in lower and ("limit" in lower or "how much" in lower):
        travel = analytics_service.compute_travel_analytics(db, budget)
        if travel:
            reply = (
                f"Your recommended travel spending is {currency}{travel.recommended_daily_spending}/day, "
                f"based on {currency}{travel.variable_travel_remaining} of variable travel budget remaining."
            )
        else:
            reply = "You don't have a travel category set up yet."
        return schemas.AssistantResponse(reply=reply, source="fallback")

    if "summary" in lower:
        summary = analytics_service.compute_budget_summary(db, budget)
        cat_lines = ", ".join(f"{c.name} {c.percent_used}%" for c in summary.categories)
        reply = (
            f"This month: {currency}{summary.total_spent} spent of {currency}{summary.total_budget} "
            f"({summary.percent_used}% used), {currency}{summary.total_remaining} remaining with "
            f"{summary.days_remaining} day(s) left. By category: {cat_lines}."
        )
        return schemas.AssistantResponse(reply=reply, source="fallback")

    # Generic fallback
    summary = analytics_service.compute_budget_summary(db, budget)
    reply = (
        "I can answer questions about your budget directly (AI narration is currently disabled -- add an "
        "AI_API_KEY to enable free-form chat). Quick summary: "
        f"{currency}{summary.total_remaining} remaining of {currency}{summary.total_budget} "
        f"({summary.percent_used}% used), {summary.days_remaining} day(s) left. Try asking things like "
        "'how much can I spend today', 'am I overspending on food', or 'can I afford 300 on shopping'."
    )
    return schemas.AssistantResponse(reply=reply, source="fallback")


def answer(db: Session, budget: models.Budget, message: str) -> schemas.AssistantResponse:
    try:
        ai_response = _ai_assistant_reply(db, budget, message)
        if ai_response:
            return ai_response
    except Exception:
        pass
    return _fallback_reply(db, budget, message)
