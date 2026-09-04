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

    async def extract(self, *, text: str, expected_field: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Classify the supplied Traditional Chinese emergency-intake answer into JSON only. "
            "Do not diagnose, triage, recommend treatment, or infer missing measurements. "
            "Distinguish current symptom, denial, past history, family history, hypothetical "
            "question, caregiver statement, measurement, and ambiguity. Return keys "
            "classification, normalized_value, status, requires_human_confirmation.\n"
            f"Expected field: {expected_field}\nContext: {json.dumps(context, ensure_ascii=False)}\n"
            f"Answer: {text}"
        )
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
