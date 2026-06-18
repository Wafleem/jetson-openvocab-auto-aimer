from __future__ import annotations

import json
import os
import subprocess
import sys

from aimer.commands import CommandPromptParser, ParserBackend


def test_simple_command_outputs_nanoowl_prompt() -> None:
    result = CommandPromptParser(ParserBackend.HEURISTIC).parse("track the red mug")

    assert result.target_phrase == "red mug"
    assert result.primary_prompt == "a red mug"
    assert result.nanoowl_prompts == ["a red mug", "red mug"]
    assert result.attributes == ["red"]


def test_natural_command_keeps_object_attributes_and_splits_spatial_context() -> None:
    result = CommandPromptParser(ParserBackend.HEURISTIC).parse(
        "Can you aim at the small red mug near the laptop?"
    )

    assert result.target_phrase == "small red mug"
    assert result.primary_prompt == "a small red mug"
    assert result.attributes == ["small", "red"]
    assert result.spatial_context == "near the laptop"


def test_messy_command_strips_filler() -> None:
    result = CommandPromptParser(ParserBackend.HEURISTIC).parse(
        "uh could you like point at the blue cup thing for me"
    )

    assert result.target_phrase == "blue cup"
    assert result.primary_prompt == "a blue cup"


def test_keeps_person_visual_description() -> None:
    result = CommandPromptParser(ParserBackend.HEURISTIC).parse(
        "follow the person in blue shirt"
    )

    assert result.target_phrase == "person in blue shirt"
    assert result.primary_prompt == "a person in blue shirt"
    assert result.spatial_context is None


def test_cli_outputs_json() -> None:
    env = {**os.environ, "PYTHONPATH": "src"}
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "aimer.command_parse",
            "--backend",
            "heuristic",
            "center on the green bottle",
        ],
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["primary_prompt"] == "a green bottle"
    assert payload["target_phrase"] == "green bottle"


def test_auto_backend_falls_back_with_concise_note(monkeypatch) -> None:
    parser = CommandPromptParser(ParserBackend.AUTO)

    def fail_paligemma(command: str, image_path: str | None):
        raise RuntimeError("You are trying to access a gated repo.\nLong traceback-ish message")

    monkeypatch.setattr(parser, "_parse_with_paligemma", fail_paligemma)
    result = parser.parse("track the red mug")

    assert result.parser == "heuristic"
    assert result.primary_prompt == "a red mug"
    assert result.notes == [
        "PaliGemma unavailable; used heuristic parser instead: RuntimeError: "
        "model access is gated; authenticate with a Hugging Face token that has accepted the model terms"
    ]
