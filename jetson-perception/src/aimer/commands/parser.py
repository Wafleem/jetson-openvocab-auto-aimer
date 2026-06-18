"""High-level command parser facade."""

from __future__ import annotations

from enum import Enum

from .heuristic import HeuristicCommandParser
from .models import CommandPrompt


class ParserBackend(str, Enum):
    """Available command parsing backends."""

    HEURISTIC = "heuristic"
    PALIGEMMA = "paligemma"
    AUTO = "auto"


class CommandPromptParser:
    """Parse text commands into NanoOWL prompt payloads."""

    def __init__(
        self,
        backend: ParserBackend | str = ParserBackend.AUTO,
        model_id: str = "google/paligemma2-3b-mix-224",
    ) -> None:
        self.backend = ParserBackend(backend)
        self.model_id = model_id
        self._heuristic = HeuristicCommandParser()
        self._model_parser = None

    def parse(self, command: str, image_path: str | None = None) -> CommandPrompt:
        """Parse a command, optionally using an image-aware local model backend."""
        if self.backend is ParserBackend.HEURISTIC:
            return self._heuristic.parse(command)

        if self.backend in {ParserBackend.PALIGEMMA, ParserBackend.AUTO}:
            try:
                return self._parse_with_paligemma(command, image_path=image_path)
            except Exception as exc:
                if self.backend is ParserBackend.PALIGEMMA:
                    raise

                result = self._heuristic.parse(command)
                notes = [
                    *result.notes,
                    f"PaliGemma unavailable; used heuristic parser instead: {exc}",
                ]
                return CommandPrompt(
                    raw_command=result.raw_command,
                    target_phrase=result.target_phrase,
                    nanoowl_prompts=result.nanoowl_prompts,
                    parser=result.parser,
                    confidence=result.confidence,
                    attributes=result.attributes,
                    spatial_context=result.spatial_context,
                    notes=notes,
                )

        raise ValueError(f"unsupported parser backend: {self.backend}")

    def _parse_with_paligemma(self, command: str, image_path: str | None) -> CommandPrompt:
        if self._model_parser is None:
            from .paligemma import PaliGemmaCommandParser

            self._model_parser = PaliGemmaCommandParser(model_id=self.model_id)

        return self._model_parser.parse(command, image_path=image_path)
