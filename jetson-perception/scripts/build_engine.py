"""Build the NanoOWL image-encoder TensorRT engine."""

from __future__ import annotations

import argparse
from pathlib import Path


def build(
    output_path: str,
    model_name: str = "google/owlvit-base-patch32",
    *,
    fp16: bool = True,
    onnx_opset: int = 17,
) -> Path:
    """Build the NanoOWL image-encoder engine and return its path."""
    from nanoowl.owl_predictor import OwlPredictor

    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    predictor = OwlPredictor(model_name=model_name)
    predictor.build_image_encoder_engine(
        str(destination),
        fp16_mode=fp16,
        onnx_opset=onnx_opset,
    )

    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError(f"NanoOWL did not create a TensorRT engine at {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NanoOWL TensorRT image-encoder engine")
    parser.add_argument("--output", default="/models/owl_image_encoder_patch32.engine")
    parser.add_argument("--model", default="google/owlvit-base-patch32")
    parser.add_argument("--fp16", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--onnx-opset", type=int, default=17)
    args = parser.parse_args()
    output = build(
        args.output,
        args.model,
        fp16=args.fp16,
        onnx_opset=args.onnx_opset,
    )
    print(output)


if __name__ == "__main__":
    main()
