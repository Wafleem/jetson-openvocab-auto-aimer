"""Smoke-test entrypoint for NanoOWL: detect open-vocab prompts in one image.

Run inside the Jetson container once an engine is built:
    python -m aimer.run_detect --engine /models/owl_image_encoder_patch32.engine \
        --image test.jpg --prompts "a person, a red mug" --threshold 0.1

This is the first thing to get working. Camera/VLM/control come later.
STUB: wiring is here; detector internals are TODO (see detector.py).
"""

from __future__ import annotations

import argparse

from .detector import NanoOwlDetector


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NanoOWL open-vocab detection smoke test")
    p.add_argument("--engine", required=True, help="path to the NanoOWL image-encoder TRT engine")
    p.add_argument("--image", required=True, help="path to an input image")
    p.add_argument("--prompts", required=True, help="comma-separated text prompts")
    p.add_argument("--threshold", type=float, default=0.1)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    prompts = [s.strip() for s in args.prompts.split(",") if s.strip()]

    from PIL import Image  # lazy: only needed at runtime on the Jetson

    image = Image.open(args.image).convert("RGB")

    detector = NanoOwlDetector(engine_path=args.engine)
    detector.load()
    detections = detector.detect(image, prompts, threshold=args.threshold)

    for d in detections:
        print(f"{d.label:>20s}  score={d.score:.3f}  box={d.box}")
    print(f"({len(detections)} detection(s))")


if __name__ == "__main__":
    main()
