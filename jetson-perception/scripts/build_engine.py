"""Build the NanoOWL image-encoder TensorRT engine.

Run inside the Jetson container. Output goes to models/ (mounted at /models).
STUB: fill in per the upstream NanoOWL build step.

Upstream typically provides a builder, e.g.:
    python -m nanoowl.build_image_encoder_engine /models/owl_image_encoder_patch32.engine
This wrapper just centralizes the path/options for this project.
"""

from __future__ import annotations

import argparse


def build(output_path: str, model_name: str = "google/owlvit-base-patch32") -> None:
    """Build/export the NanoOWL image-encoder engine to `output_path`.

    TODO: call the upstream nanoowl engine builder (see module docstring).
    """
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NanoOWL TensorRT image-encoder engine")
    parser.add_argument("--output", default="/models/owl_image_encoder_patch32.engine")
    parser.add_argument("--model", default="google/owlvit-base-patch32")
    args = parser.parse_args()
    build(args.output, args.model)


if __name__ == "__main__":
    main()
