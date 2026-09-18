from __future__ import annotations

import json
from typing import Any

import httpx


class OpenAICompatibleClient:
    """Small chat-completions adapter used only to propose structured observations."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        max_retries: int,
        temperature: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._temperature = temperature

    def _build_prompt(self, *, text: str, expected_field: str, context: dict[str, Any]) -> str:
        other_context = {key: value for key, value in context.items() if key != "safety_categories"}
        return (
            "Classify the supplied emergency-intake answer into JSON only. The answer may be in "
            "any language; interpret it by meaning rather than by matching words. "
            "Do not diagnose, triage, recommend treatment, or infer missing measurements. "
            "Distinguish current symptom, denial, past history, family history, hypothetical "
            "question, caregiver statement, measurement, and ambiguity. Return keys "
            "classification, normalized_value, status, requires_human_confirmation, "
            "other_safety_categories.\n"
            f"{self._safety_category_section(context)}"
            f"Expected field: {expected_field}\n"
            f"Context: {json.dumps(other_context, ensure_ascii=False)}\n"
            f"Answer: {text}"
        )

    @staticmethod
    def _safety_category_section(context: dict[str, Any]) -> str:
        categories = context.get("safety_categories")
        if not isinstance(categories, dict) or not categories:
            return ""
        listed = "\n".join(
            f"- {field}: {'; '.join(concepts)}" for field, concepts in sorted(categories.items())
        )
        return (
            "In other_safety_categories, list the field keys below whose condition this answer "
            "reports as present for this patient right now, and use [] when none apply. Never "
            "list one for a denial, a past episode, a family member's history, or a hypothetical "
            "question.\n"
            f"{listed}\n"
        )

    async def extract(self, *, text: str, expected_field: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(text=text, expected_field=expected_field, context=context)
        payload = {
            "model": self._model,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are a constrained information extraction component.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    response = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    value = json.loads(content)
                    if not isinstance(value, dict):
                        raise ValueError("LLM response must be a JSON object")
                    return value
                except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError):
                    if attempt == self._max_retries:
                        raise
        raise RuntimeError("unreachable")
