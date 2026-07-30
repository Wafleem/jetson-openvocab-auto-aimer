"""Build NanoOWL's engine or run detection on a photo or local CSI feed."""

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


def live(prompt_text: str, threshold: float) -> None:
    import os
    import time

    import cv2
    import numpy as np
    import torch
    from nanoowl.owl_drawing import draw_owl_output
    from nanoowl.owl_predictor import OwlPredictor
    from PIL import Image

    prompts = [prompt.strip() for prompt in prompt_text.split(",") if prompt.strip()]
    if not prompts:
        raise ValueError("Give at least one prompt, such as 'a computer mouse'")

    pipeline = (
        "nvarguscamerasrc sensor-id=0 wbmode=3 ! "
        "video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1 ! "
        "nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
        "video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false"
    )
    cv2.setLogLevel(2)
    display = os.environ.pop("DISPLAY", None)
    try:
        camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not camera.isOpened():
            raise RuntimeError("Could not open the IMX219 through NVIDIA Argus")

        for _ in range(45):
            ok, _ = camera.read()
            if not ok:
                camera.release()
                raise RuntimeError("The IMX219 stopped during camera warm-up")
    finally:
        if display is not None:
            os.environ["DISPLAY"] = display

    print("Loading NanoOWL...", flush=True)
    predictor = OwlPredictor(model_name=MODEL, image_encoder_engine=ENGINE)
    text_encodings = predictor.encode_text(prompts)
    inference_stream = torch.cuda.Stream()

    window = "NanoOWL Live"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, 1280, 720)
    print("Local live window ready. Press Q or Esc to stop.", flush=True)

    last_output = None
    last_seen = 0.0
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("The IMX219 stopped producing frames")

            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            with torch.cuda.stream(inference_stream):
                with torch.no_grad():
                    output = predictor.predict(
                        image=image,
                        text=prompts,
                        text_encodings=text_encodings,
                        threshold=threshold,
                    )
            inference_stream.synchronize()

            now = time.monotonic()
            if len(output.labels):
                last_output = output
                last_seen = now
            output_to_draw = output
            if not len(output.labels) and last_output is not None and now - last_seen < 0.25:
                output_to_draw = last_output

            annotated = draw_owl_output(
                image,
                output_to_draw,
                text=prompts,
                draw_text=True,
            )
            display_frame = cv2.cvtColor(np.asarray(annotated), cv2.COLOR_RGB2BGR)
            cv2.imshow(window, display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27) or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
    except KeyboardInterrupt:
        pass
    finally:
        camera.release()
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("engine", help="build the TensorRT engine")

    detect_parser = commands.add_parser("detect", help="detect objects in one photo")
    detect_parser.add_argument("image")
    detect_parser.add_argument("prompts", help="comma-separated object descriptions")
    detect_parser.add_argument("--threshold", type=float, default=0.1)

    live_parser = commands.add_parser("live", help="show local CSI camera detections")
    live_parser.add_argument("prompts", help="comma-separated object descriptions")
    live_parser.add_argument("--threshold", type=float, default=0.1)

    args = parser.parse_args()
    if args.command == "engine":
        build_engine()
    elif args.command == "detect":
        detect(args.image, args.prompts, args.threshold)
    else:
        live(args.prompts, args.threshold)


if __name__ == "__main__":
    main()
