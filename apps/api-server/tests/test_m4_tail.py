"""M4 ice → silent review → complete; Pattern E fake translate."""
from __future__ import annotations

import unittest

from engine import translate as translate_mod
from engine.nodes import ice as ice_mod
from engine.nodes import optional_questions as opt_mod
from engine.nodes import presenting_complaint as pc_mod
from engine.nodes import priority_questions as pri_mod
from engine.nodes import redflag_screening as rf_mod
from engine.nodes import review as review_mod
from engine.runner import SessionRunner
from tests.helpers import (
    answer_ice,
    snap_values,
    walk_to_optional,
)


class TestM4TailAndTranslate(unittest.TestCase):
    def setUp(self) -> None:
        pc_mod.reset_presenting_complaint_fakes()
        pri_mod.reset_priority_fakes()
        rf_mod.reset_redflag_fakes()
        opt_mod.reset_optional_fakes()
        ice_mod.reset_ice_fakes()
        review_mod.reset_review_fakes()
        translate_mod.reset_translate_fakes()

    def test_full_tail_to_complete(self) -> None:
        runner = SessionRunner()
        session_id, _ = runner.start()
        walk_to_optional(runner, session_id)

        ice_step = runner.resume(session_id, {"skip": True})
        self.assertEqual(ice_step.phase, "ice")
        self.assertEqual(ice_mod.fake_ice_qg_call_count, 1)
        self.assertEqual(
            [q.id for q in (ice_step.questions or [])],
            ["ice_idea", "ice_concern", "ice_expectation"],
        )

        # Ice answer → silent review → complete (survey is router-level, not here).
        done = answer_ice(runner, session_id)
        self.assertEqual(done.step_type, "complete")
        self.assertEqual(review_mod.fake_nurse_call_count, 1)

        values = snap_values(runner, session_id)
        self.assertEqual(values["ice_idea"]["text"], "maybe a sprain")
        self.assertEqual(values["ice_idea"].get("source"), "free_text")
        self.assertIn("ice", values["completed_phases"])
        self.assertIn("review", values["completed_phases"])
        self.assertIn("wrist", values["encounter_summary"] or "")
        self.assertTrue(values["is_session_complete"])
        self.assertEqual(review_mod.fake_nurse_call_count, 1)

    def test_pattern_e_translate_on_non_en_ice(self) -> None:
        runner = SessionRunner()
        session_id, _ = runner.start(session_language="ko")
        walk_to_optional(runner, session_id)
        runner.resume(session_id, {"skip": True})

        before = translate_mod.fake_translate_call_count
        answer_ice(runner, session_id)
        self.assertEqual(translate_mod.fake_translate_call_count, before + 3)

        values = snap_values(runner, session_id)
        self.assertEqual(values["ice_idea"]["text"], "maybe a sprain")
        self.assertEqual(values["ice_idea"]["en_text"], "[en] maybe a sprain")
        self.assertEqual(values["ice_concern"]["en_text"], "[en] worried about fracture")

    def test_pattern_e_no_translate_when_en(self) -> None:
        runner = SessionRunner()
        session_id, _ = runner.start(session_language="en")
        walk_to_optional(runner, session_id)
        runner.resume(session_id, {"skip": True})
        before = translate_mod.fake_translate_call_count
        answer_ice(runner, session_id)
        self.assertEqual(translate_mod.fake_translate_call_count, before)
        values = snap_values(runner, session_id)
        self.assertIsNone(values["ice_idea"].get("en_text"))


if __name__ == "__main__":
    unittest.main()
