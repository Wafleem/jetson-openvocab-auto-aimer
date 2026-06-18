"""Data contracts for command-to-prompt parsing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any


@dataclass(frozen=True)
class CommandPrompt:
    """NanoOWL-ready target prompt extracted from a user command."""

    raw_command: str
    target_phrase: str
    nanoowl_prompts: list[str]
    parser: str
    confidence: float
    attributes: list[str] = field(default_factory=list)
    spatial_context: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def primary_prompt(self) -> str:
        """The first prompt to feed NanoOWL."""
        return self.nanoowl_prompts[0] if self.nanoowl_prompts else ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["primary_prompt"] = self.primary_prompt
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)
