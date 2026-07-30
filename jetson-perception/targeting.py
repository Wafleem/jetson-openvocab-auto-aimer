"""Small, detector-driven target lock and camera-centering math."""

from dataclasses import dataclass
from math import hypot
from typing import Iterable


Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class Detection:
    label: int
    score: float
    box: Box


@dataclass(frozen=True)
class AimSolution:
    valid: bool
    dx: int
    dy: int
    normalized_x: float
    normalized_y: float
    centered: bool


def box_center(box: Box) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def solve_aim(box: Box | None, frame_width: int, frame_height: int, deadband: int = 20) -> AimSolution:
    if box is None:
        return AimSolution(False, 0, 0, 0.0, 0.0, False)

    target_x, target_y = box_center(box)
    dx = round(target_x - frame_width / 2.0)
    dy = round(target_y - frame_height / 2.0)
    centered = abs(dx) <= deadband and abs(dy) <= deadband
    if abs(dx) <= deadband:
        dx = 0
    if abs(dy) <= deadband:
        dy = 0
    return AimSolution(
        True,
        dx,
        dy,
        dx / (frame_width / 2.0),
        dy / (frame_height / 2.0),
        centered,
    )


def _area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _iou(first: Box, second: Box) -> float:
    intersection = (
        max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
        * max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    )
    union = _area(first) + _area(second) - intersection
    return intersection / union if union else 0.0


def _size_similarity(first: Box, second: Box) -> float:
    first_area, second_area = _area(first), _area(second)
    larger = max(first_area, second_area)
    return min(first_area, second_area) / larger if larger else 0.0


class BoxFilter:
    """Smooth box measurements and predict through short detection gaps."""

    def __init__(self, box: Box, position_gain: float = 0.7, velocity_gain: float = 0.3) -> None:
        self.position_gain = position_gain
        self.velocity_gain = velocity_gain
        self.center_x, self.center_y = box_center(box)
        self.width = box[2] - box[0]
        self.height = box[3] - box[1]
        self.velocity_x = 0.0
        self.velocity_y = 0.0

    def predicted_box(self) -> Box:
        return self._box(self.center_x + self.velocity_x, self.center_y + self.velocity_y)

    def correct(self, measurement: Box) -> Box:
        predicted_x = self.center_x + self.velocity_x
        predicted_y = self.center_y + self.velocity_y
        measured_x, measured_y = box_center(measurement)
        residual_x = measured_x - predicted_x
        residual_y = measured_y - predicted_y

        self.center_x = predicted_x + self.position_gain * residual_x
        self.center_y = predicted_y + self.position_gain * residual_y
        self.velocity_x += self.velocity_gain * residual_x
        self.velocity_y += self.velocity_gain * residual_y

        measured_width = measurement[2] - measurement[0]
        measured_height = measurement[3] - measurement[1]
        self.width += self.position_gain * (measured_width - self.width)
        self.height += self.position_gain * (measured_height - self.height)
        return self._box(self.center_x, self.center_y)

    def coast(self) -> Box:
        self.center_x += self.velocity_x
        self.center_y += self.velocity_y
        self.velocity_x *= 0.8
        self.velocity_y *= 0.8
        return self._box(self.center_x, self.center_y)

    def _box(self, center_x: float, center_y: float) -> Box:
        half_width = self.width / 2.0
        half_height = self.height / 2.0
        return (
            center_x - half_width,
            center_y - half_height,
            center_x + half_width,
            center_y + half_height,
        )


class TargetTracker:
    """Maintain one target using motion, overlap, size, and conservative loss handling."""

    def __init__(self, confirmation_hits: int = 2, max_misses: int = 8) -> None:
        self.confirmation_hits = confirmation_hits
        self.max_misses = max_misses
        self._next_id = 1
        self.reset()

    def reset(self) -> None:
        self.box: Box | None = None
        self.track_id: int | None = None
        self.label: int | None = None
        self.score = 0.0
        self.state = "SEARCHING"
        self.hits = 0
        self.misses = 0
        self.filter: BoxFilter | None = None

    @property
    def aim_valid(self) -> bool:
        return self.state == "TRACKING"

    def lock(self, detection: Detection) -> None:
        self.track_id = self._next_id
        self._next_id += 1
        self.box = detection.box
        self.label = detection.label
        self.score = detection.score
        self.state = "TRACKING"
        self.hits = self.confirmation_hits
        self.misses = 0
        self.filter = BoxFilter(detection.box)

    def _predicted_box(self) -> Box:
        assert self.filter is not None
        return self.filter.predicted_box()

    def _best_match(self, detections: Iterable[Detection], frame_size: tuple[int, int]) -> Detection | None:
        assert self.box is not None and self.label is not None
        predicted = self._predicted_box()
        predicted_center = box_center(predicted)
        frame_diagonal = hypot(*frame_size)
        box_diagonal = hypot(predicted[2] - predicted[0], predicted[3] - predicted[1])
        distance_limit = max(80.0, box_diagonal * 1.5)
        best: tuple[float, Detection] | None = None

        for detection in detections:
            if detection.label != self.label:
                continue
            center = box_center(detection.box)
            distance = hypot(center[0] - predicted_center[0], center[1] - predicted_center[1])
            overlap = _iou(predicted, detection.box)
            if overlap < 0.05 and distance > distance_limit:
                continue
            proximity = max(0.0, 1.0 - distance / (frame_diagonal * 0.35))
            association = 0.45 * overlap + 0.35 * proximity + 0.20 * _size_similarity(predicted, detection.box)
            association *= 0.75 + 0.25 * detection.score
            if best is None or association > best[0]:
                best = (association, detection)
        return best[1] if best else None

    def update(self, detections: list[Detection], frame_size: tuple[int, int]) -> None:
        if self.state == "LOST":
            return

        if self.box is None:
            if not detections:
                return
            candidate = max(detections, key=lambda detection: detection.score)
            self.track_id = self._next_id
            self._next_id += 1
            self.box = candidate.box
            self.label = candidate.label
            self.score = candidate.score
            self.hits = 1
            self.state = "TENTATIVE" if self.confirmation_hits > 1 else "TRACKING"
            self.filter = BoxFilter(candidate.box)
            return

        match = self._best_match(detections, frame_size)
        if match is None:
            self.misses += 1
            assert self.filter is not None
            self.box = self.filter.coast()
            self.state = "COASTING" if self.misses <= self.max_misses else "LOST"
            return

        assert self.filter is not None
        self.box = self.filter.correct(match.box)
        self.score = match.score
        self.misses = 0
        self.hits += 1
        self.state = "TRACKING" if self.hits >= self.confirmation_hits else "TENTATIVE"
