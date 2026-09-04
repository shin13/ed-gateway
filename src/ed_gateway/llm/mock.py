from typing import Any


class MockLLMClient:
    """Deterministic test double; local extraction remains authoritative in mock mode."""

    async def extract(self, *, text: str, expected_field: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"text": text, "expected_field": expected_field, "context": context}
