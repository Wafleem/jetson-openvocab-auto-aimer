"""NanoOWL open-vocab detector wrapper.

Thin wrapper around NVIDIA-AI-IOT/nanoowl (OWL-ViT on TensorRT). Heavy imports (torch,
nanoowl) are done lazily inside methods so this module imports fine on a dev machine without
the Jetson stack installed.

STUB: the structure is here; fill in the TODOs once NanoOWL is installed and an engine is built
(see scripts/build_engine.py).
"""

from __future__ import annotations

from dataclasses import dataclass


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
        """Instantiate the NanoOWL predictor with the prebuilt image-encoder engine.

        TODO:
            from nanoowl.owl_predictor import OwlPredictor
            self._predictor = OwlPredictor(self.model_name,
                                           image_encoder_engine=self.engine_path)
        """
        raise NotImplementedError

    def detect(
        self,
        image,                       # PIL.Image.Image (RGB)
        prompts: list[str],
        threshold: float = 0.1,
    ) -> list[Detection]:
        """Run open-vocab detection for `prompts` on `image`; return Detections above threshold.

        TODO:
            text_encodings = self._predictor.encode_text(prompts)
            output = self._predictor.predict(image=image, text=prompts,
                                             text_encodings=text_encodings,
                                             threshold=threshold)
            -> map output.boxes / labels / scores into list[Detection]
        """
        raise NotImplementedError
