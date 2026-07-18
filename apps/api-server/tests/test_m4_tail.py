"""M4 ice → silent review → complete; Pattern E translate via agent_bridge."""
from __future__ import annotations

import unittest

from engine.runner import SessionRunner
from tests.helpers import (
    answer_ice,
    snap_values,
    walk_to_optional,
)
from tests.mock_clinical_ai import MockClinicalAiTestCase


class TestM4TailAndTranslate(MockClinicalAiTestCase, unittest.TestCase):
    def test_full_tail_to_complete(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        walk_to_optional(runner, session_id)

        ice_step = runner.resume(session_id, {"skip": True})
        self.assertEqual(ice_step.phase, "ice")
        self.assertEqual(self.ai.fake_ice_qg_call_count, 1)
        self.assertEqual(
            [q.id for q in (ice_step.questions or [])],
            ["ice_idea", "ice_concern", "ice_expectation"],
        )
        for q in ice_step.questions or []:
            self.assertEqual(q.kind, "multi_choice")

        # Ice answer → silent review → complete (survey is router-level, not here).
        done = answer_ice(runner, session_id)
        self.assertEqual(done.step_type, "complete")
        self.assertEqual(self.ai.fake_nurse_call_count, 1)

        values = snap_values(runner, session_id)
        self.assertEqual(values["ice_idea"]["text"], "Maybe a sprain")
        self.assertEqual(values["ice_idea"].get("source"), "option")
        self.assertIn("ice", values["completed_phases"])
        self.assertIn("review", values["completed_phases"])
        self.assertIn("wrist", values["encounter_summary"] or "")
        self.assertTrue(values["is_session_complete"])
        self.assertEqual(self.ai.fake_nurse_call_count, 1)

    def test_pattern_e_translate_on_non_en_ice(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start(session_language="ko")
        walk_to_optional(runner, session_id)
        runner.resume(session_id, {"skip": True})

        before = self.ai.fake_translate_call_count
        answer_ice(runner, session_id, as_other_free_text=True)
        self.assertEqual(self.ai.fake_translate_call_count, before + 3)

        values = snap_values(runner, session_id)
        self.assertEqual(values["ice_idea"]["text"], "maybe a sprain")
        self.assertEqual(values["ice_idea"]["en_text"], "[en] maybe a sprain")
        self.assertEqual(
            values["ice_concern"]["en_text"], "[en] worried about fracture"
        )

    def test_pattern_e_no_translate_when_en(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start(session_language="en")
        walk_to_optional(runner, session_id)
        runner.resume(session_id, {"skip": True})
        before = self.ai.fake_translate_call_count
        answer_ice(runner, session_id)
        self.assertEqual(self.ai.fake_translate_call_count, before)
        values = snap_values(runner, session_id)
        self.assertIsNone(values["ice_idea"].get("en_text"))


if __name__ == "__main__":
    unittest.main()
