"""Use PaliGemma localization to choose one NanoOWL detection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import hypot
from typing import Iterable

from targeting import Box, Detection, box_center


DEFAULT_VLM_MODEL = "google/paligemma2-3b-mix-224"
_LOCATION_PATTERN = re.compile(
    r"<loc(\d{4})>\s*<loc(\d{4})>\s*<loc(\d{4})>\s*<loc(\d{4})>"
)


@dataclass(frozen=True)
class VlmLocalization:
    boxes: tuple[Box, ...]
    raw_output: str


def parse_location_tokens(output: str, frame_width: int, frame_height: int) -> tuple[Box, ...]:
    """Convert PaliGemma's normalized y1/x1/y2/x2 tokens to pixel boxes."""
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")

    boxes = []
    for match in _LOCATION_PATTERN.finditer(output):
        y1, x1, y2, x2 = (int(value) for value in match.groups())
        if max(y1, x1, y2, x2) > 1023 or y2 <= y1 or x2 <= x1:
            continue
        boxes.append(
            (
                x1 * frame_width / 1023.0,
                y1 * frame_height / 1023.0,
                x2 * frame_width / 1023.0,
                y2 * frame_height / 1023.0,
            )
        )
    return tuple(boxes)


def _area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _iou(first: Box, second: Box) -> float:
    intersection = (
        max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
        * max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    )
    union = _area(first) + _area(second) - intersection
    return intersection / union if union else 0.0


def select_detection(
    detections: Iterable[Detection],
    vlm_boxes: Iterable[Box],
    frame_size: tuple[int, int],
) -> Detection | None:
    """Associate the best VLM localization with the detector's precise boxes."""
    frame_width, frame_height = frame_size
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")

    candidates = tuple(detections)
    localizations = tuple(vlm_boxes)
    if not candidates or not localizations:
        return None

    frame_diagonal = hypot(frame_width, frame_height)
    best: tuple[float, Detection] | None = None
    for localization in localizations:
        localization_center = box_center(localization)
        for detection in candidates:
            detection_center = box_center(detection.box)
            center_distance = hypot(
                localization_center[0] - detection_center[0],
                localization_center[1] - detection_center[1],
            )
            overlap = _iou(localization, detection.box)
            if overlap < 0.05 and center_distance > frame_diagonal * 0.08:
                continue

            proximity = max(0.0, 1.0 - center_distance / (frame_diagonal * 0.25))
            score = (0.75 * overlap + 0.25 * proximity) * (0.9 + 0.1 * detection.score)
            if best is None or score > best[0]:
                best = (score, detection)

    return best[1] if best else None


class PaliGemmaSelector:
    """Load a 4-bit PaliGemma model and localize a text query in a real frame."""

    def __init__(self, model_name: str = DEFAULT_VLM_MODEL) -> None:
        import torch
        from transformers import AutoProcessor, BitsAndBytesConfig
        from transformers import PaliGemmaForConditionalGeneration

        if not torch.cuda.is_available():
            raise RuntimeError("PaliGemma requires the Jetson CUDA device")

        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = PaliGemmaForConditionalGeneration.from_pretrained(
            model_name,
            device_map="auto",
            quantization_config=quantization,
            attn_implementation="sdpa",
            low_cpu_mem_usage=True,
        ).eval()

    def locate(self, image: object, query: str) -> VlmLocalization:
        import torch

        target = query.strip()
        if not target:
            raise ValueError("VLM target query cannot be empty")
        if not hasattr(image, "size") or len(image.size) != 2:
            raise TypeError("PaliGemma expects a PIL image")

        prompt = f"detect {target}"
        inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(
            self.model.device
        )
        prompt_length = inputs["input_ids"].shape[-1]
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=128,
                cache_implementation="static",
            )
        raw_output = self.processor.decode(
            generated[0, prompt_length:],
            skip_special_tokens=False,
        )
        frame_width, frame_height = image.size
        boxes = parse_location_tokens(raw_output, frame_width, frame_height)
        return VlmLocalization(boxes=boxes, raw_output=raw_output)
