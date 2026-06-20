"""Deterministic command parser used as the always-available baseline."""

from __future__ import annotations

import re

from .models import CommandPrompt


_FILLER_RE = re.compile(
    r"\b(?:uh+|um+|erm+|please|could you|can you|would you|i want you to|"
    r"sort of|kind of|like|maybe|just)\b",
    re.IGNORECASE,
)

_ACTION_PATTERNS = [
    r"\b(?:aim|point|look|center|centre|focus|lock)\s+(?:the\s+camera\s+)?(?:at|on|to)\s+",
    r"\b(?:track|follow|find|detect|watch|target|select)\s+",
    r"\b(?:go|move)\s+(?:to|towards|toward)\s+",
]

_LEADING_NOISE_RE = re.compile(
    r"^(?:the\s+)?(?:camera|gimbal|jetson|system)\s+",
    re.IGNORECASE,
)

_TRAILING_NOISE_RE = re.compile(
    r"\b(?:for me|right now|now|please|thanks|thank you)\b.*$",
    re.IGNORECASE,
)

_SPATIAL_RE = re.compile(
    r"\b("
    r"(?:on|to)\s+the\s+(?:left|right)"
    r"|(?:left|right)\s+side"
    r"|near\s+.+"
    r"|next\s+to\s+.+"
    r"|beside\s+.+"
    r"|by\s+.+"
    r"|behind\s+.+"
    r"|in\s+front\s+of\s+.+"
    r"|under\s+.+"
    r"|over\s+.+"
    r"|above\s+.+"
    r"|below\s+.+"
    r"|on\s+(?:top\s+of\s+)?(?:the\s+)?.+"
    r")$",
    re.IGNORECASE,
)

_KEEP_IN_PHRASE_NOUNS = {
    "person",
    "man",
    "woman",
    "boy",
    "girl",
    "child",
    "kid",
    "dog",
    "cat",
}

_ATTRIBUTE_WORDS = {
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "black",
    "white",
    "gray",
    "grey",
    "brown",
    "silver",
    "gold",
    "small",
    "large",
    "big",
    "tiny",
    "tall",
    "short",
    "bright",
    "dark",
    "wooden",
    "metal",
    "plastic",
    "glass",
}

_DETERMINERS_RE = re.compile(r"^(?:a|an|the|that|this|those|these)\s+", re.IGNORECASE)


class HeuristicCommandParser:
    """Extract a visual target without model dependencies."""

    name = "heuristic"

    def parse(self, command: str) -> CommandPrompt:
        normalized = _normalize(command)
        target = _extract_target(normalized)
        target, spatial_context = _split_spatial_context(target)
        target = _clean_target(target)

        if not target:
            target = _clean_target(normalized)

        attributes = [word for word in target.split() if word in _ATTRIBUTE_WORDS]
        prompts = _nanoowl_prompts(target)
        confidence = 0.55 if target else 0.0
        notes: list[str] = []

        if spatial_context:
            notes.append("Spatial context kept out of NanoOWL prompt for later target selection.")

        return CommandPrompt(
            raw_command=command,
            target_phrase=target,
            nanoowl_prompts=prompts,
            parser=self.name,
            confidence=confidence,
            attributes=attributes,
            spatial_context=spatial_context,
            notes=notes,
        )


def _normalize(command: str) -> str:
    text = command.strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\"'`]", "", text)
    text = re.sub(r"[?!.,;:]+", " ", text)
    text = _FILLER_RE.sub(" ", text)
    text = _LEADING_NOISE_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_target(text: str) -> str:
    for pattern in _ACTION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return text[match.end() :].strip()
    return text


def _split_spatial_context(target: str) -> tuple[str, str | None]:
    if _should_keep_relation(target):
        return target, None

    match = _SPATIAL_RE.search(target)
    if not match:
        return target, None

    object_phrase = target[: match.start()].strip()
    spatial = match.group(1).strip()
    return object_phrase, spatial


def _should_keep_relation(target: str) -> bool:
    words = target.split()
    if not words:
        return False
    return words[0] in _KEEP_IN_PHRASE_NOUNS and " in " in f" {target} "


def _clean_target(target: str) -> str:
    previous = None
    while previous != target:
        previous = target
        target = _TRAILING_NOISE_RE.sub("", target)
        target = re.sub(r"\b(?:thing|object|one)\b$", "", target).strip()
        target = re.sub(r"\s+", " ", target).strip()
        target = _DETERMINERS_RE.sub("", target).strip()

    return target


def _nanoowl_prompts(target: str) -> list[str]:
    if not target:
        return []

    article = "an" if target[0] in "aeiou" else "a"
    article_prompt = f"{article} {target}"
    prompts = [article_prompt]

    if target != article_prompt:
        prompts.append(target)

    return prompts
