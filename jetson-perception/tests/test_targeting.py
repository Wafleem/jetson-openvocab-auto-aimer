import math
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from targeting import solve_aim


class SolveAimTests(unittest.TestCase):
    def test_centered_target_has_zero_error(self) -> None:
        solution = solve_aim((620, 340, 660, 380), 1280, 720, 62.2, 37.4)

        self.assertTrue(solution.valid)
        self.assertTrue(solution.centered)
        self.assertEqual((solution.dx, solution.dy), (0, 0))
        self.assertEqual((solution.yaw_error, solution.pitch_error), (0.0, 0.0))

    def test_right_edge_is_negative_half_horizontal_fov(self) -> None:
        solution = solve_aim((1270, 350, 1290, 370), 1280, 720, 62.2, 37.4)

        self.assertEqual(solution.dx, 640)
        self.assertAlmostEqual(math.degrees(solution.yaw_error), -31.1, places=6)

    def test_bottom_edge_is_positive_half_vertical_fov(self) -> None:
        solution = solve_aim((630, 710, 650, 730), 1280, 720, 62.2, 37.4)

        self.assertEqual(solution.dy, 360)
        self.assertAlmostEqual(math.degrees(solution.pitch_error), 18.7, places=6)

    def test_missing_target_has_invalid_solution(self) -> None:
        solution = solve_aim(None, 1280, 720, 62.2, 37.4)

        self.assertFalse(solution.valid)
        self.assertEqual((solution.yaw_error, solution.pitch_error), (0.0, 0.0))

    def test_invalid_fov_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            solve_aim((0, 0, 10, 10), 1280, 720, 180.0, 37.4)


if __name__ == "__main__":
    unittest.main()
