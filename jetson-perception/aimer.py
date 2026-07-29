"""Build NanoOWL's TensorRT engine or run detection on one photo."""

import argparse
from pathlib import Path


ENGINE = "/models/owl_image_encoder_patch32.engine"
MODEL = "google/owlvit-base-patch32"


def build_engine() -> None:
    from nanoowl.owl_predictor import OwlPredictor

    print("Building the TensorRT engine. This can take several minutes...")
    predictor = OwlPredictor(model_name=MODEL)
    predictor.build_image_encoder_engine(
        ENGINE,
        fp16_mode=True,
        onnx_opset=17,
    )

    if not Path(ENGINE).is_file() or Path(ENGINE).stat().st_size == 0:
        raise RuntimeError(f"NanoOWL did not create {ENGINE}")
    print(f"Engine ready: {ENGINE}")


def detect(image_path: str, prompt_text: str, threshold: float) -> None:
    import torch
    from nanoowl.owl_predictor import OwlPredictor
    from PIL import Image

    prompts = [prompt.strip() for prompt in prompt_text.split(",") if prompt.strip()]
    if not prompts:
        raise ValueError("Give at least one prompt, such as 'a red mug'")

    image = Image.open(image_path).convert("RGB")
    predictor = OwlPredictor(model_name=MODEL, image_encoder_engine=ENGINE)

    with torch.no_grad():
        text_encodings = predictor.encode_text(prompts)
        output = predictor.predict(
            image=image,
            text=prompts,
            text_encodings=text_encodings,
            threshold=threshold,
        )

    for label, score, box in zip(output.labels, output.scores, output.boxes):
        name = prompts[int(label)]
        coordinates = [round(float(value), 3) for value in box]
        print(f"{name}: score={float(score):.3f}, box={coordinates}")

    print(f"Found {len(output.labels)} object(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("engine", help="build the TensorRT engine")

    detect_parser = commands.add_parser("detect", help="detect objects in one photo")
    detect_parser.add_argument("image")
    detect_parser.add_argument("prompts", help="comma-separated object descriptions")
    detect_parser.add_argument("--threshold", type=float, default=0.1)

    args = parser.parse_args()
    if args.command == "engine":
        build_engine()
    else:
        detect(args.image, args.prompts, args.threshold)


if __name__ == "__main__":
    main()
