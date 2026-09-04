from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    async def extract(self, *, text: str, expected_field: str, context: dict[str, Any]) -> dict[str, Any]:
        """Return provider-neutral structured extraction data."""
        ...
