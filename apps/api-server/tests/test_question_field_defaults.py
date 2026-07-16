"""QuestionField default_value / default_values shape."""
from __future__ import annotations

import unittest

from schemas.question_fields import QuestionField, QuestionOption


class TestQuestionFieldDefaults(unittest.TestCase):
    def test_default_value_for_single_choice(self) -> None:
        q = QuestionField(
            id="onset_timing",
            kind="single_choice",
            prompt="When did this start?",
            personalization_note="timing chip",
            default_value="WITHIN_48_HOURS",
            options=[
                QuestionOption(value="LAST_24_HOURS", label="Last 24 hours"),
                QuestionOption(value="WITHIN_48_HOURS", label="Within 48 hours"),
            ],
        )
        self.assertEqual(q.default_value, "WITHIN_48_HOURS")
        self.assertIsNone(q.default_values)

    def test_default_values_for_multi_choice(self) -> None:
        q = QuestionField(
            id="allergy",
            kind="multi_choice",
            prompt="What kinds of allergies?",
            personalization_note="multi prefill",
            default_values=["Medicines", "Food"],
            options=[
                QuestionOption(value="Medicines", label="Medicines"),
                QuestionOption(value="Food", label="Food"),
                QuestionOption(value="Other", label="Other"),
            ],
        )
        self.assertEqual(q.default_values, ["Medicines", "Food"])
        self.assertIsNone(q.default_value)

    def test_both_defaults_optional(self) -> None:
        q = QuestionField(
            id="meds",
            kind="yes_no",
            prompt="Any medicines?",
            personalization_note="no prefill",
        )
        self.assertIsNone(q.default_value)
        self.assertIsNone(q.default_values)


if __name__ == "__main__":
    unittest.main()
