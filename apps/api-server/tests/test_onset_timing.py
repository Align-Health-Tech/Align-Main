"""Unit tests for onset timing chip helpers."""
from __future__ import annotations

import unittest

from engine.static.onset_timing import (
    ONSET_TIMING_OPTIONS,
    onset_timing_default,
    onset_timing_label,
)


class TestOnsetTiming(unittest.TestCase):
    def test_four_shorecare_chips(self) -> None:
        self.assertEqual(len(ONSET_TIMING_OPTIONS), 4)
        self.assertEqual(
            [o.value for o in ONSET_TIMING_OPTIONS],
            [
                "LAST_24_HOURS",
                "WITHIN_48_HOURS",
                "WITHIN_1_WEEK",
                "MORE_THAN_1_WEEK",
            ],
        )

    def test_label_and_default(self) -> None:
        self.assertEqual(onset_timing_label("WITHIN_48_HOURS"), "Within 48 hours")
        self.assertEqual(onset_timing_default("Within 48 hours"), "WITHIN_48_HOURS")
        self.assertEqual(onset_timing_default("WITHIN_48_HOURS"), "WITHIN_48_HOURS")
        self.assertIsNone(onset_timing_default("twisted it yesterday"))


if __name__ == "__main__":
    unittest.main()
