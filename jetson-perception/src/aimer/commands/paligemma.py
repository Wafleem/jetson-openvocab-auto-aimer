"""PaliGemma-backed command parser.

The project uses PaliGemma as the image+text model in the full pipeline. This backend keeps
the same output contract as the deterministic parser while allowing a local PaliGemma checkpoint
to refine the NanoOWL prompt when model dependencies and weights are available.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .heuristic import HeuristicCommandParser
from .models import CommandPrompt


_INSTRUCTION = """Extract the visual target from the user's camera command.
Return compact JSON with exactly these keys:
target_phrase: object phrase for an open-vocabulary object detector, no action words.
attributes: visual descriptive words preserved from the command.
spatial_context: location or relation words that should help later target selection, or null.
notes: short list of caveats.

Rules:
- Output only JSON.
- Do not include words like aim, track, find, look, point, follow, camera, please.
- Keep useful visual descriptions such as color, size, material, and clothing.
- Keep spatial relations out of target_phrase unless they describe a person or animal.
- The target_phrase should be suitable for NanoOWL.
"""


class PaliGemmaCommandParser:
    """Use a local PaliGemma checkpoint to parse commands."""

    name = "paligemma"

    def __init__(
        self,
        model_id: str = "google/paligemma2-3b-mix-224",
        max_new_tokens: int = 128,
    ) -> None:
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self._heuristic = HeuristicCommandParser()
        self._processor = None
        self._model = None

    def parse(self, command: str, image_path: str | None = None) -> CommandPrompt:
        self._load()
        prompt = f"{_INSTRUCTION}\nUser command: {command}\nJSON:"
        inputs = self._build_inputs(prompt, image_path=image_path)

        output = self._model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
        )
        decoded = self._processor.decode(output[0], skip_special_tokens=True)
        payload = _extract_json(decoded)
        return _payload_to_prompt(
            raw_command=command,
            payload=payload,
            fallback=self._heuristic.parse(command),
        )

    def _load(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        try:
            import torch
            from transformers import AutoProcessor, PaliGemmaForConditionalGeneration
        except ImportError as exc:
            raise RuntimeError(
                "PaliGemma backend requires torch and transformers installed in the Jetson env"
            ) from exc

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        device_map: str | None = "auto" if torch.cuda.is_available() else None

        self._processor = AutoProcessor.from_pretrained(self.model_id)
        self._model = PaliGemmaForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            device_map=device_map,
        )

        if device_map is None:
            self._model.to("cpu")

    def _build_inputs(self, prompt: str, image_path: str | None):
        image = None
        if image_path:
            from PIL import Image

            image = Image.open(Path(image_path)).convert("RGB")

        inputs = self._processor(images=image, text=prompt, return_tensors="pt")
        return inputs.to(self._model.device)


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"PaliGemma response did not contain JSON: {text!r}")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"PaliGemma response JSON could not be parsed: {text!r}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"PaliGemma response JSON was not an object: {text!r}")
    return payload


def _payload_to_prompt(
    raw_command: str,
    payload: dict[str, Any],
    fallback: CommandPrompt,
) -> CommandPrompt:
    target_phrase = str(payload.get("target_phrase") or fallback.target_phrase).strip().lower()
    target_phrase = re.sub(r"\s+", " ", target_phrase)

    if not target_phrase:
        target_phrase = fallback.target_phrase

    attributes = payload.get("attributes", fallback.attributes)
    if not isinstance(attributes, list):
        attributes = fallback.attributes
    attributes = [str(item).strip().lower() for item in attributes if str(item).strip()]

    spatial_context = payload.get("spatial_context", fallback.spatial_context)
    if spatial_context is not None:
        spatial_context = str(spatial_context).strip().lower() or None

    notes = payload.get("notes", [])
    if not isinstance(notes, list):
        notes = []
    notes = [str(note).strip() for note in notes if str(note).strip()]

    return CommandPrompt(
        raw_command=raw_command,
        target_phrase=target_phrase,
        nanoowl_prompts=_nanoowl_prompts(target_phrase),
        parser="paligemma",
        confidence=0.8,
        attributes=attributes,
        spatial_context=spatial_context,
        notes=notes,
    )


def _nanoowl_prompts(target: str) -> list[str]:
    if not target:
        return []
    article = "an" if target[0] in "aeiou" else "a"
    return [f"{article} {target}", target]
