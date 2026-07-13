"""M1 presenting_complaint — free_text gate, clarify self-loop, branch to detail."""
from __future__ import annotations

import unittest

from engine.nodes import presenting_complaint as pc_mod
from engine.nodes import priority_questions as pri_mod
from engine.runner import SessionRunner
from schemas.clinical_ai_io import ClassifierResult
from tests.helpers import answer_pc_free_text, snap_values


class TestM1PresentingComplaint(unittest.TestCase):
    def setUp(self) -> None:
        pri_mod.reset_priority_fakes()
        pc_mod.reset_presenting_complaint_fakes()

    def test_localised_ready_path(self) -> None:
        runner = SessionRunner()
        session_id, step0 = runner.start()
        self.assertEqual(step0.phase, "presenting_complaint")

        step = answer_pc_free_text(
            runner, session_id, "sharp pain in my left ankle"
        )
        self.assertEqual(step.phase, "localised_detail")
        self.assertEqual(pc_mod.fake_classifier_call_count, 1)
        self.assertEqual(pc_mod.fake_clarify_qg_call_count, 0)

        values = snap_values(runner, session_id)
        self.assertEqual(values["presentation_category"], "LOCALISED")
        self.assertIn("presenting_complaint", values["completed_phases"])
        self.assertEqual(
            values["chief_complaint"]["text"],
            "sharp pain in my left ankle",
        )

    def test_not_localised_ready_path(self) -> None:
        runner = SessionRunner()
        session_id, _ = runner.start()

        step = answer_pc_free_text(
            runner, session_id, "I have a fever and feel unwell"
        )
        self.assertEqual(step.phase, "non_localised_detail")
        values = snap_values(runner, session_id)
        self.assertEqual(values["presentation_category"], "NOT_LOCALISED")

    def test_clarify_loop_then_ready(self) -> None:
        pc_mod.set_classifier_script(
            [
                ClassifierResult(ready=False, reason="vague"),
                ClassifierResult(
                    ready=True, category="LOCALISED", confidence=0.9, reason="ok"
                ),
            ]
        )
        runner = SessionRunner()
        session_id, _ = runner.start()

        clarify_step = answer_pc_free_text(runner, session_id, "something hurts")
        self.assertEqual(clarify_step.phase, "presenting_complaint")
        self.assertEqual(clarify_step.questions[0].id, "pc_clarify_1")
        self.assertEqual(pc_mod.fake_classifier_call_count, 1)
        self.assertEqual(pc_mod.fake_clarify_qg_call_count, 1)

        after = runner.resume(
            session_id,
            {
                "answers": [
                    {
                        "question_id": "pc_clarify_1",
                        "value": "right wrist pain when lifting",
                    },
                ]
            },
        )
        self.assertEqual(pc_mod.fake_clarify_qg_call_count, 1)
        self.assertEqual(pc_mod.fake_classifier_call_count, 2)
        self.assertEqual(after.phase, "localised_detail")

        values = snap_values(runner, session_id)
        self.assertEqual(values["presentation_category"], "LOCALISED")
        self.assertGreaterEqual(len(values.get("messages") or []), 2)

    def test_two_clarify_rounds_replace_pending(self) -> None:
        pc_mod.set_classifier_script(
            [
                ClassifierResult(ready=False, reason="vague"),
                ClassifierResult(ready=False, reason="still vague"),
                ClassifierResult(
                    ready=True, category="LOCALISED", confidence=0.92, reason="ok"
                ),
            ]
        )
        runner = SessionRunner()
        session_id, _ = runner.start()

        round1 = answer_pc_free_text(runner, session_id, "something hurts")
        self.assertEqual(round1.questions[0].id, "pc_clarify_1")

        round2 = runner.resume(
            session_id,
            {"answers": [{"question_id": "pc_clarify_1", "value": "not sure"}]},
        )
        self.assertEqual(round2.phase, "presenting_complaint")
        self.assertEqual(round2.questions[0].id, "pc_clarify_2")
        self.assertEqual(pc_mod.fake_clarify_qg_call_count, 2)

        values = snap_values(runner, session_id)
        pending_ids = [q["id"] for q in values["pending_questions"]]
        self.assertEqual(pending_ids, ["pc_clarify_2"])

        done = runner.resume(
            session_id,
            {
                "answers": [
                    {
                        "question_id": "pc_clarify_2",
                        "value": "right wrist pain when lifting",
                    },
                ]
            },
        )
        self.assertEqual(pc_mod.fake_clarify_qg_call_count, 2)
        self.assertEqual(pc_mod.fake_classifier_call_count, 3)
        self.assertEqual(done.phase, "localised_detail")


if __name__ == "__main__":
    unittest.main()
