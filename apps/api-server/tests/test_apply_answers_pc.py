"""Unit tests for apply_answers presenting_complaint mapping."""
from __future__ import annotations

import unittest

from engine.helpers.apply import apply_answers
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState


class TestApplyAnswersPresentingComplaint(unittest.TestCase):
    def _state(self, **kwargs) -> SessionState:
        base = dict(
            session_id="s1",
            patient_id="p1",
            organization_id="o1",
            awaiting_phase="presenting_complaint",
        )
        base.update(kwargs)
        return SessionState(**base)

    def test_sets_chief_complaint_from_free_text(self) -> None:
        q = QuestionField(
            id="pc_chief_complaint",
            kind="free_text",
            prompt="What brings you in today?",
            personalization_note="deterministic",
            collect_target_id="chief_complaint",
        )
        updates = apply_answers(
            self._state(),
            {"answers": [{"question_id": "pc_chief_complaint", "value": "wrist pain"}]},
            [q],
        )
        self.assertEqual(updates["chief_complaint"]["text"], "wrist pain")
        self.assertEqual(updates["messages"][0]["content"], "wrist pain")
        self.assertEqual(updates["turn_number"], 1)

    def test_clarify_appends_messages(self) -> None:
        q = QuestionField(
            id="pc_clarify_1",
            kind="single_choice",
            prompt="Where?",
            personalization_note="fake",
            collect_target_id="chief_complaint_clarify",
            options=[
                {"value": "body_part", "label": "Body part"},
                {"value": "Other", "label": "Other"},
            ],
        )
        state = self._state(
            chief_complaint={"text": "hurts"},
            turn_number=1,
        )
        updates = apply_answers(
            state,
            {"answers": [{"question_id": "pc_clarify_1", "value": "body_part"}]},
            [q],
        )
        self.assertNotIn("chief_complaint", updates)
        self.assertIn("body_part", updates["messages"][0]["content"])
        self.assertEqual(updates["turn_number"], 2)


if __name__ == "__main__":
    unittest.main()
