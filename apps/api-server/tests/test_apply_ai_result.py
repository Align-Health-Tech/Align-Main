"""AI-input apply dispatcher + nurse review mapper."""
from __future__ import annotations

import unittest

from engine.session_state_mappers import map_ai_result
from engine.session_state_mappers.ai import map_nurse_review
from schemas.clinical_ai_io import ClassifierResult, ReviewSummaryResult
from schemas.session_states import SessionState


def _state(**kwargs) -> SessionState:
    base = dict(session_id="s1", patient_id="p1", organization_id="o1")
    base.update(kwargs)
    return SessionState(**base)


class TestApplyNurseReview(unittest.TestCase):
    def test_writes_encounter_summary(self) -> None:
        updates = map_nurse_review(
            _state(),
            ReviewSummaryResult(summary="Wrist pain, no red flags."),
        )
        self.assertEqual(
            updates, {"encounter_summary": "Wrist pain, no red flags."}
        )


class TestApplyAiResult(unittest.TestCase):
    def test_routes_classifier(self) -> None:
        updates = map_ai_result(
            _state(),
            ClassifierResult(ready=True, category="LOCALISED"),
        )
        self.assertEqual(updates["presentation_category"], "LOCALISED")

    def test_routes_nurse_review(self) -> None:
        updates = map_ai_result(
            _state(),
            ReviewSummaryResult(summary="One-line nurse note."),
        )
        self.assertEqual(updates["encounter_summary"], "One-line nurse note.")

    def test_rejects_unknown_type(self) -> None:
        with self.assertRaises(TypeError):
            map_ai_result(_state(), object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
