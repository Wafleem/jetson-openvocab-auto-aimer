import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from targeting import Detection
from vlm_selector import parse_location_tokens, select_detection


class PaliGemmaLocationParserTests(unittest.TestCase):
    def test_parses_normalized_yx_location_tokens(self) -> None:
        boxes = parse_location_tokens(
            "<loc0256><loc0128><loc0767><loc0895> red mug",
            1023,
            1023,
        )

        self.assertEqual(boxes, ((128.0, 256.0, 895.0, 767.0),))

    def test_skips_malformed_and_out_of_range_boxes(self) -> None:
        boxes = parse_location_tokens(
            "<loc0900><loc0100><loc0200><loc0300> bad "
            "<loc0000><loc0000><loc1024><loc1024> out",
            1280,
            720,
        )

        self.assertEqual(boxes, ())

    def test_rejects_invalid_frame_size(self) -> None:
        with self.assertRaises(ValueError):
            parse_location_tokens("", 0, 720)


class VlmDetectorAssociationTests(unittest.TestCase):
    def test_selects_detector_box_overlapping_vlm_location(self) -> None:
        left = Detection(0, 0.92, (80.0, 100.0, 260.0, 400.0))
        right = Detection(0, 0.60, (700.0, 110.0, 900.0, 410.0))

        selected = select_detection(
            [left, right],
            [(680.0, 90.0, 930.0, 430.0)],
            (1280, 720),
        )

        self.assertEqual(selected, right)

    def test_rejects_unassociated_localization(self) -> None:
        detection = Detection(0, 0.9, (0.0, 0.0, 100.0, 100.0))

        selected = select_detection(
            [detection],
            [(1000.0, 600.0, 1200.0, 700.0)],
            (1280, 720),
        )

        self.assertIsNone(selected)

    def test_empty_inputs_have_no_selection(self) -> None:
        self.assertIsNone(select_detection([], [], (1280, 720)))


if __name__ == "__main__":
    unittest.main()
