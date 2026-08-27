"""
Thin wrapper around the Anthropic Messages API.

Design goals:
- Never raise out into request handlers; callers get None/False on any
  failure and switch to their deterministic fallback path.
- Centralize model/key configuration so the rest of the app never touches
  environment variables directly.
"""
import json
import logging
from functools import lru_cache
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger("finance_agent.ai")


class AIClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.enabled = bool(api_key.strip())
        self._client = None
        if self.enabled:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=api_key)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to initialize Anthropic client: %s", exc)
                self.enabled = False

    def structured_json(self, system_prompt: str, user_message: str, max_tokens: int = 400) -> Optional[dict]:
        """Ask the model for a single JSON object and parse it. Returns None
        on any failure (network error, malformed JSON, disabled client)."""
        if not self.enabled or self._client is None:
            return None
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                text = text.split("\n", 1)[-1] if "\n" in text else text
                if text.lower().startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as exc:  # pragma: no cover - defensive
            logger.info("AI structured_json call failed, falling back: %s", exc)
            return None

    def converse_with_tools(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 700,
    ) -> Optional[Any]:
        """Single-turn call that allows the model to request tool use.
        Returns the raw Anthropic response object, or None on failure."""
        if not self.enabled or self._client is None:
            return None
        try:
            return self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                tools=tools,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.info("AI converse_with_tools call failed, falling back: %s", exc)
            return None

    def plain_text_reply(self, system_prompt: str, user_message: str, max_tokens: int = 500) -> Optional[str]:
        if not self.enabled or self._client is None:
            return None
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()
        except Exception as exc:  # pragma: no cover - defensive
            logger.info("AI plain_text_reply call failed, falling back: %s", exc)
            return None


@lru_cache
def get_ai_client() -> AIClient:
    settings = get_settings()
    return AIClient(api_key=settings.ai_api_key, model=settings.ai_model)
