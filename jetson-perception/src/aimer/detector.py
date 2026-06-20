"""NanoOWL open-vocabulary detector wrapper."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Detection:
    """A single detected object."""

    label: str
    score: float
    box: tuple[int, int, int, int]   # (x1, y1, x2, y2) in pixels


class NanoOwlDetector:
    """Open-vocab detection with NanoOWL.

    Typical usage:
        det = NanoOwlDetector(engine_path="/models/owl_image_encoder_patch32.engine")
        det.load()
        results = det.detect(image, ["a person", "a red mug"], threshold=0.1)
    """

    def __init__(
        self,
        engine_path: str,
        model_name: str = "google/owlvit-base-patch32",
    ) -> None:
        self.engine_path = engine_path
        self.model_name = model_name
        self._predictor = None  # nanoowl OwlPredictor, set in load()

    def load(self) -> None:
        """Instantiate NanoOWL with the prebuilt TensorRT image encoder."""
        engine = Path(self.engine_path).expanduser()
        if not engine.is_file():
            raise FileNotFoundError(f"NanoOWL engine not found: {engine}")

        from nanoowl.owl_predictor import OwlPredictor

        self._predictor = OwlPredictor(
            model_name=self.model_name,
            image_encoder_engine=str(engine),
        )

    def detect(
        self,
        image,                       # PIL.Image.Image (RGB)
        prompts: list[str],
        threshold: float = 0.1,
    ) -> list[Detection]:
        """Run open-vocabulary detection and return pixel-space boxes."""
        if self._predictor is None:
            raise RuntimeError("NanoOwlDetector.load() must be called before detect()")
        if not prompts:
            raise ValueError("at least one NanoOWL prompt is required")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")

        import torch

        with torch.no_grad():
            text_encodings = self._predictor.encode_text(prompts)
            output = self._predictor.predict(
                image=image,
                text=prompts,
                text_encodings=text_encodings,
                threshold=threshold,
            )

        labels = output.labels.detach().cpu().tolist()
        scores = output.scores.detach().cpu().tolist()
        boxes = output.boxes.detach().cpu().tolist()
        width, height = image.size

        detections = []
        for label_index, score, box in zip(labels, scores, boxes):
            if not 0 <= label_index < len(prompts):
                raise RuntimeError(f"NanoOWL returned invalid label index {label_index}")
            detections.append(
                Detection(
                    label=prompts[label_index],
                    score=float(score),
                    box=_normalized_box_to_pixels(box, width, height),
                )
            )
        return detections


def _normalized_box_to_pixels(
    box: list[float],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    if len(box) != 4:
        raise RuntimeError(f"NanoOWL returned malformed box: {box!r}")

    x1 = max(0, min(width, math.floor(float(box[0]) * width)))
    y1 = max(0, min(height, math.floor(float(box[1]) * height)))
    x2 = max(0, min(width, math.ceil(float(box[2]) * width)))
    y2 = max(0, min(height, math.ceil(float(box[3]) * height)))
    return x1, y1, x2, y2
