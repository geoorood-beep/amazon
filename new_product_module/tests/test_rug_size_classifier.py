from __future__ import annotations

import unittest
from pathlib import Path

from src.rug_size_classifier import classify_rug_size
from src.rule_loader import load_rules


class RugSizeClassifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rules = load_rules(Path(__file__).resolve().parents[1] / "config/category_rules.example.yaml")
        cls.mapping = rules.rug_size_type_mapping

    def test_user_confirmed_overlap_sizes_are_runner(self) -> None:
        for size in ["2x4", "3x6", "3x7", "4x10", "4x12"]:
            with self.subTest(size=size):
                result = classify_rug_size(size, mapping=self.mapping)
                self.assertEqual(result.rug_type, "runner")
                self.assertEqual(result.analysis_threshold_profile, "runner")

    def test_every_2_5_short_side_rectangle_is_runner(self) -> None:
        for size in ["2.5x6", "8 x 2.5", "2.5×12"]:
            with self.subTest(size=size):
                result = classify_rug_size(size, mapping=self.mapping)
                self.assertEqual(result.rug_type, "runner")

    def test_round_marker_takes_priority_over_2_5_width(self) -> None:
        result = classify_rug_size("2.5ft round", mapping=self.mapping)
        self.assertEqual(result.rug_type, "round")
        self.assertIsNone(result.analysis_threshold_profile)

        oval = classify_rug_size("6x9", shape="oval", mapping=self.mapping)
        self.assertEqual(oval.rug_type, "round")

    def test_standard_sizes_map_to_expected_types(self) -> None:
        cases = {
            "2x3": ("doormat", "doormat"),
            "5x7": ("area_rug", "area_small"),
            "7x9": ("area_rug", "area_large"),
            "6ft round": ("round", None),
        }
        for size, expected in cases.items():
            with self.subTest(size=size):
                result = classify_rug_size(size, mapping=self.mapping)
                self.assertEqual((result.rug_type, result.analysis_threshold_profile), expected)

    def test_inch_area_is_converted_before_profile_selection(self) -> None:
        result = classify_rug_size('30x48 inches', mapping=self.mapping)
        self.assertEqual(result.rug_type, "area_rug")
        self.assertEqual(result.analysis_threshold_profile, "area_small")

    def test_unknown_size_does_not_borrow_a_threshold(self) -> None:
        result = classify_rug_size("13x17", mapping=self.mapping)
        self.assertIsNone(result.rug_type)
        self.assertIsNone(result.analysis_threshold_profile)

    def test_configuration_can_remove_a_previous_size_mapping(self) -> None:
        result = classify_rug_size(
            "3x8",
            mapping={
                "runner_sizes": [],
                "runner_short_widths": [2.5],
                "doormat_sizes": [],
                "area_sizes": ["3x8"],
                "area_small_max_square_feet": 57.5,
            },
        )
        self.assertEqual(result.rug_type, "area_rug")
        self.assertEqual(result.analysis_threshold_profile, "area_small")


if __name__ == "__main__":
    unittest.main()
