"""Tests for form question lists + next_step_raw (no duplicate NextStep builders)."""
from __future__ import annotations

import unittest

from engine.helpers.next_step import build_next_step_raw
from engine.static.deterministic_forms import (
    build_consent_questions,
    build_survey_questions,
)


class TestDeterministicForms(unittest.TestCase):
    def test_consent_questions(self) -> None:
        qs = build_consent_questions()
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].id, "consent_privacy")
        self.assertEqual(qs[0].kind, "consent_accept")

    def test_survey_questions(self) -> None:
        qs = build_survey_questions()
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].id, "survey_ease")
        self.assertEqual(qs[0].kind, "single_choice")


class TestBuildNextStepRaw(unittest.TestCase):
    def test_consent_via_raw(self) -> None:
        step = build_next_step_raw(
            0, build_consent_questions(), phase="consent"
        )
        self.assertEqual(step.step_type, "consent")
        self.assertEqual(step.phase, "consent")
        self.assertEqual(step.turn_number, 0)
        self.assertEqual(step.questions[0].id, "consent_privacy")

    def test_survey_via_raw(self) -> None:
        step = build_next_step_raw(
            3, build_survey_questions(), phase="survey"
        )
        self.assertEqual(step.step_type, "survey")
        self.assertEqual(step.phase, "survey")
        self.assertEqual(step.turn_number, 3)
        self.assertEqual(step.questions[0].id, "survey_ease")


if __name__ == "__main__":
    unittest.main()
