"""Build NanoOWL's engine or run detection on a photo or live CSI feed."""

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


def live(prompt_text: str, threshold: float, port: int) -> None:
    import io
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    import cv2
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
    camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not camera.isOpened():
        raise RuntimeError("Could not open the IMX219 through NVIDIA Argus")

    for _ in range(45):
        ok, _ = camera.read()
        if not ok:
            camera.release()
            raise RuntimeError("The IMX219 stopped during camera warm-up")

    print("Loading NanoOWL...", flush=True)
    predictor = OwlPredictor(model_name=MODEL, image_encoder_engine=ENGINE)
    text_encodings = predictor.encode_text(prompts)

    condition = threading.Condition()
    latest_jpeg = None
    frame_number = 0

    class StreamHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            nonlocal latest_jpeg, frame_number
            if self.path == "/":
                page = b"""<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NanoOWL Live</title><style>
html,body{margin:0;width:100%;height:100%;background:#000;overflow:hidden}
img{width:100%;height:100%;object-fit:contain;display:block}
</style></head><body><img src="/stream.mjpg"></body></html>"""
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(page)))
                self.end_headers()
                self.wfile.write(page)
                return
            if self.path == "/snapshot.jpg":
                with condition:
                    condition.wait_for(lambda: latest_jpeg is not None)
                    jpeg = latest_jpeg
                self.send_response(200)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(jpeg)))
                self.end_headers()
                self.wfile.write(jpeg)
                return
            if self.path != "/stream.mjpg":
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            seen_frame = -1
            try:
                while True:
                    with condition:
                        condition.wait_for(lambda: frame_number != seen_frame)
                        jpeg = latest_jpeg
                        seen_frame = frame_number
                    if jpeg is None:
                        continue
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("0.0.0.0", port), StreamHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Live view: http://localhost:{port}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    last_output = None
    last_seen = 0.0
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("The IMX219 stopped producing frames")

            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            with torch.no_grad():
                output = predictor.predict(
                    image=image,
                    text=prompts,
                    text_encodings=text_encodings,
                    threshold=threshold,
                )

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
            buffer = io.BytesIO()
            annotated.save(buffer, format="JPEG", quality=80)
            with condition:
                latest_jpeg = buffer.getvalue()
                frame_number += 1
                condition.notify_all()
    except KeyboardInterrupt:
        pass
    finally:
        camera.release()
        server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("engine", help="build the TensorRT engine")

    detect_parser = commands.add_parser("detect", help="detect objects in one photo")
    detect_parser.add_argument("image")
    detect_parser.add_argument("prompts", help="comma-separated object descriptions")
    detect_parser.add_argument("--threshold", type=float, default=0.1)

    live_parser = commands.add_parser("live", help="show live CSI camera detections")
    live_parser.add_argument("prompts", help="comma-separated object descriptions")
    live_parser.add_argument("--threshold", type=float, default=0.1)
    live_parser.add_argument("--port", type=int, default=7860)

    args = parser.parse_args()
    if args.command == "engine":
        build_engine()
    elif args.command == "detect":
        detect(args.image, args.prompts, args.threshold)
    else:
        live(args.prompts, args.threshold, args.port)


if __name__ == "__main__":
    main()
