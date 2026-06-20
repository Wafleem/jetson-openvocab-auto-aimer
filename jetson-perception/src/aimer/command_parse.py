"""CLI for turning text commands into NanoOWL prompts."""

from __future__ import annotations

import argparse

from .commands import CommandPromptParser, ParserBackend


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse a command into NanoOWL-ready prompts")
    parser.add_argument("command", help="natural-language text command")
    parser.add_argument(
        "--backend",
        choices=[backend.value for backend in ParserBackend],
        default=ParserBackend.AUTO.value,
        help="parser backend to use",
    )
    parser.add_argument(
        "--model-id",
        default="google/paligemma2-3b-mix-224",
        help="local/Hugging Face PaliGemma model id or path",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="optional image path for PaliGemma image-aware parsing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    parser = CommandPromptParser(backend=args.backend, model_id=args.model_id)
    print(parser.parse(args.command, image_path=args.image).to_json())


if __name__ == "__main__":
    main()
