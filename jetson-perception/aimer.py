"""Build NanoOWL's engine or run detection on a photo or local CSI feed."""

from __future__ import annotations

import argparse
from pathlib import Path


ENGINE = "/models/owl_image_encoder_patch32.engine"
MODEL = "google/owlvit-base-patch32"
DEFAULT_VLM_MODEL = "google/paligemma2-3b-mix-224"
DEFAULT_HORIZONTAL_FOV = 62.2
DEFAULT_VERTICAL_FOV = 37.4


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


def vlm_detect(image_path: str, query: str, model_name: str) -> None:
    from PIL import Image
    from vlm_selector import PaliGemmaSelector

    image = Image.open(image_path).convert("RGB")
    print(f"Loading PaliGemma: {model_name}", flush=True)
    localization = PaliGemmaSelector(model_name).locate(image, query)
    print(f"Model output: {localization.raw_output}")
    for box in localization.boxes:
        coordinates = [round(value, 3) for value in box]
        print(f"{query}: box={coordinates}")
    print(f"Found {len(localization.boxes)} VLM location(s).")


def live(
    prompt_text: str,
    threshold: float,
    lock_threshold: float,
    horizontal_fov: float,
    vertical_fov: float,
    serial_device: str | None,
    vlm_query: str | None,
    vlm_model: str,
    vlm_interval: float,
) -> None:
    import os
    from math import degrees
    from time import monotonic

    import cv2
    import torch
    from nanoowl.owl_predictor import OwlPredictor
    from PIL import Image
    from gimbal_link import GimbalLink
    from targeting import Detection, TargetTracker, box_center, solve_aim
    from vlm_selector import PaliGemmaSelector, select_detection

    prompts = [prompt.strip() for prompt in prompt_text.split(",") if prompt.strip()]
    if not prompts:
        raise ValueError("Give at least one prompt, such as 'a computer mouse'")
    if vlm_query is not None and not vlm_query.strip():
        raise ValueError("VLM target query cannot be empty")
    if vlm_interval <= 0.0:
        raise ValueError("VLM interval must be positive")

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
    vlm_selector = None
    if vlm_query is not None:
        print(f"Loading PaliGemma: {vlm_model}", flush=True)
        vlm_selector = PaliGemmaSelector(vlm_model)
    tracker = TargetTracker(
        min_lock_score=lock_threshold,
        automatic_lock=vlm_selector is None,
    )
    gimbal = GimbalLink(serial_device) if serial_device else None
    next_vlm_time = 0.0

    window = "NanoOWL Live"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, 1280, 720)
    selection: dict[str, tuple[int, int] | None] = {"point": None}

    def select_target(event: int, x: int, y: int, _flags: int, _data: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            selection["point"] = (x, y)

    cv2.setMouseCallback(window, select_target)
    print("Local live window ready.", flush=True)
    print(
        f"Detection threshold: {threshold:.2f}; lock threshold: {lock_threshold:.2f}",
        flush=True,
    )
    if vlm_query is not None:
        print(f'PaliGemma target: "{vlm_query}"', flush=True)
    print(f"2D solver FOV: {horizontal_fov:.1f} x {vertical_fov:.1f} degrees", flush=True)
    if gimbal is not None:
        print(f"Gimbal link: {serial_device}", flush=True)
    print("Click a detection to lock it. Press R to reset, Q or Esc to stop.", flush=True)

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

            detections = [
                Detection(
                    int(label),
                    float(score),
                    tuple(float(coordinate) for coordinate in box),
                )
                for label, score, box in zip(output.labels, output.scores, output.boxes)
            ]
            frame_height, frame_width = frame.shape[:2]
            vlm_boxes = ()
            point = selection["point"]
            if point is not None:
                under_pointer = [
                    detection
                    for detection in detections
                    if detection.box[0] <= point[0] <= detection.box[2]
                    and detection.box[1] <= point[1] <= detection.box[3]
                ]
                if under_pointer:
                    tracker.lock(max(under_pointer, key=lambda detection: detection.score))
                selection["point"] = None

            now = monotonic()
            if (
                vlm_selector is not None
                and tracker.state in ("SEARCHING", "LOST")
                and now >= next_vlm_time
            ):
                assert vlm_query is not None
                localization = vlm_selector.locate(image, vlm_query)
                vlm_boxes = localization.boxes
                eligible = [
                    detection
                    for detection in detections
                    if detection.score >= lock_threshold
                ]
                selected = select_detection(
                    eligible,
                    vlm_boxes,
                    (frame_width, frame_height),
                )
                if selected is not None:
                    tracker.lock(selected)
                    print(
                        f"PaliGemma locked {prompts[selected.label]} "
                        f"at detector score {selected.score:.3f}",
                        flush=True,
                    )
                next_vlm_time = monotonic() + vlm_interval

            tracker.update(detections, (frame_width, frame_height))
            solution = solve_aim(
                tracker.box if tracker.aim_valid else None,
                frame_width,
                frame_height,
                horizontal_fov,
                vertical_fov,
            )
            if gimbal is not None:
                gimbal.send(
                    1 if solution.valid else 0,
                    solution.yaw_error,
                    solution.pitch_error,
                )

            display_frame = frame.copy()
            for vlm_box in vlm_boxes:
                x1, y1, x2, y2 = (round(value) for value in vlm_box)
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 180, 0), 2)
                cv2.putText(
                    display_frame,
                    "PaliGemma",
                    (max(4, x1), max(18, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 180, 0),
                    1,
                    cv2.LINE_AA,
                )
            for detection in detections:
                x1, y1, x2, y2 = (round(value) for value in detection.box)
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (150, 150, 150), 1)
                label = f"{prompts[detection.label]} {detection.score:.2f}"
                cv2.putText(
                    display_frame,
                    label,
                    (max(4, x1), max(18, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (230, 230, 230),
                    1,
                    cv2.LINE_AA,
                )

            camera_center = (frame_width // 2, frame_height // 2)
            cv2.drawMarker(display_frame, camera_center, (0, 255, 0), cv2.MARKER_CROSS, 28, 2)
            cv2.rectangle(
                display_frame,
                (camera_center[0] - 20, camera_center[1] - 20),
                (camera_center[0] + 20, camera_center[1] + 20),
                (0, 180, 0),
                1,
            )

            if tracker.box is not None:
                colors = {
                    "TENTATIVE": (0, 215, 255),
                    "TRACKING": (255, 0, 180),
                    "COASTING": (0, 140, 255),
                    "LOST": (0, 0, 255),
                }
                color = colors.get(tracker.state, (180, 180, 180))
                x1, y1, x2, y2 = (round(value) for value in tracker.box)
                target_center = tuple(round(value) for value in box_center(tracker.box))
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 3)
                cv2.circle(display_frame, target_center, 6, color, -1)
                cv2.line(display_frame, camera_center, target_center, color, 2)

            track_name = (
                f"TARGET {tracker.track_id}" if tracker.track_id is not None else "NO TARGET"
            )
            aim_text = (
                f"yaw={degrees(solution.yaw_error):+.1f}  "
                f"pitch={degrees(solution.pitch_error):+.1f} deg"
                f"  (dx={solution.dx:+d}, dy={solution.dy:+d})"
                if solution.valid
                else "aim paused"
            )
            if tracker.state == "COASTING":
                aim_text += f"  prediction {tracker.misses}/{tracker.max_misses}"
            cv2.putText(
                display_frame,
                f"{track_name}  {tracker.state}",
                (18, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                display_frame,
                aim_text,
                (18, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(window, display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("r"):
                tracker.reset()
                next_vlm_time = 0.0
            if key in (ord("q"), 27) or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if gimbal is not None:
            gimbal.close()
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

    vlm_parser = commands.add_parser("vlm", help="localize a target with PaliGemma")
    vlm_parser.add_argument("image")
    vlm_parser.add_argument("query", help="target description")
    vlm_parser.add_argument("--model", default=DEFAULT_VLM_MODEL)

    live_parser = commands.add_parser("live", help="show local CSI camera detections")
    live_parser.add_argument("prompts", help="comma-separated object descriptions")
    live_parser.add_argument("--threshold", type=float, default=0.1)
    live_parser.add_argument("--lock-threshold", type=float, default=0.5)
    live_parser.add_argument("--hfov", type=float, default=DEFAULT_HORIZONTAL_FOV)
    live_parser.add_argument("--vfov", type=float, default=DEFAULT_VERTICAL_FOV)
    live_parser.add_argument("--serial", help="USB CDC device, usually /dev/ttyACM0")
    live_parser.add_argument("--vlm-query", help="let PaliGemma choose the target detection")
    live_parser.add_argument("--vlm-model", default=DEFAULT_VLM_MODEL)
    live_parser.add_argument("--vlm-interval", type=float, default=1.0)

    args = parser.parse_args()
    if args.command == "engine":
        build_engine()
    elif args.command == "detect":
        detect(args.image, args.prompts, args.threshold)
    elif args.command == "vlm":
        vlm_detect(args.image, args.query, args.model)
    else:
        live(
            args.prompts,
            args.threshold,
            args.lock_threshold,
            args.hfov,
            args.vfov,
            args.serial,
            args.vlm_query,
            args.vlm_model,
            args.vlm_interval,
        )


if __name__ == "__main__":
    main()
