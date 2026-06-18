from __future__ import annotations

import json
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
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["primary_prompt"] == "a green bottle"
    assert payload["target_phrase"] == "green bottle"
