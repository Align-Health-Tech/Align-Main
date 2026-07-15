"""M1 presenting_complaint — free_text gate, clarify self-loop, branch to detail."""
from __future__ import annotations

import unittest

from engine.runner import SessionRunner
from schemas.clinical_ai_io import ClassifierResult
from tests.helpers import answer_pc_free_text, snap_values
from tests.mock_clinical_ai import MockClinicalAiTestCase


class TestM1PresentingComplaint(MockClinicalAiTestCase, unittest.TestCase):
    def test_localised_ready_path(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, step0 = runner.start()
        self.assertEqual(step0.phase, "presenting_complaint")

        step = answer_pc_free_text(
            runner, session_id, "sharp pain in my left ankle"
        )
        self.assertEqual(step.phase, "localised_detail")
        self.assertEqual(self.ai.fake_classifier_call_count, 1)
        self.assertEqual(self.ai.fake_clarify_qg_call_count, 0)

        values = snap_values(runner, session_id)
        self.assertEqual(values["presentation_category"], "LOCALISED")
        self.assertIn("presenting_complaint", values["completed_phases"])
        self.assertEqual(
            values["chief_complaint"]["text"],
            "Patient presents with: sharp pain in my left ankle",
        )
        self.assertEqual(values["chief_complaint"]["source"], "ai_summary")
        first_msg = values["messages"][0]
        first_content = (
            first_msg["content"]
            if isinstance(first_msg, dict)
            else getattr(first_msg, "content", None)
        )
        self.assertEqual(first_content, "sharp pain in my left ankle")

    def test_not_localised_ready_path(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()

        step = answer_pc_free_text(
            runner, session_id, "I have a fever and feel unwell"
        )
        self.assertEqual(step.phase, "non_localised_detail")
        values = snap_values(runner, session_id)
        self.assertEqual(values["presentation_category"], "NOT_LOCALISED")

    def test_clarify_loop_then_ready(self) -> None:
        self.ai.set_classifier_script(
            [
                ClassifierResult(ready=False, reason="vague"),
                ClassifierResult(
                    ready=True,
                    category="LOCALISED",
                    confidence=0.9,
                    reason="ok",
                    chief_complaint_summary=(
                        "Patient reports pain in a body part after clarifying "
                        "a vague initial complaint."
                    ),
                ),
            ]
        )
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()

        clarify_step = answer_pc_free_text(runner, session_id, "something hurts")
        self.assertEqual(clarify_step.phase, "presenting_complaint")
        self.assertEqual(clarify_step.questions[0].id, "pc_clarify_1")
        self.assertEqual(self.ai.fake_classifier_call_count, 1)
        self.assertEqual(self.ai.fake_clarify_qg_call_count, 1)

        after = runner.resume(
            session_id,
            {
                "answers": [
                    {
                        "question_id": "pc_clarify_1",
                        "value": "body_part",
                    },
                ]
            },
        )
        self.assertEqual(self.ai.fake_clarify_qg_call_count, 1)
        self.assertEqual(self.ai.fake_classifier_call_count, 2)
        self.assertEqual(after.phase, "localised_detail")

        values = snap_values(runner, session_id)
        self.assertEqual(values["presentation_category"], "LOCALISED")
        self.assertGreaterEqual(len(values.get("messages") or []), 2)
        first_msg = values["messages"][0]
        first_content = (
            first_msg["content"]
            if isinstance(first_msg, dict)
            else getattr(first_msg, "content", None)
        )
        self.assertEqual(first_content, "something hurts")
        self.assertEqual(
            values["chief_complaint"]["text"],
            "Patient reports pain in a body part after clarifying "
            "a vague initial complaint.",
        )
        self.assertEqual(values["chief_complaint"]["source"], "ai_summary")

    def test_two_clarify_rounds_replace_pending(self) -> None:
        self.ai.set_classifier_script(
            [
                ClassifierResult(ready=False, reason="vague"),
                ClassifierResult(ready=False, reason="still vague"),
                ClassifierResult(
                    ready=True,
                    category="LOCALISED",
                    confidence=0.92,
                    reason="ok",
                    chief_complaint_summary=(
                        "Patient reports a body-part problem after two "
                        "clarification rounds."
                    ),
                ),
            ]
        )
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()

        round1 = answer_pc_free_text(runner, session_id, "something hurts")
        self.assertEqual(round1.questions[0].id, "pc_clarify_1")

        round2 = runner.resume(
            session_id,
            {"answers": [{"question_id": "pc_clarify_1", "value": "Other"}]},
        )
        self.assertEqual(round2.phase, "presenting_complaint")
        self.assertEqual(round2.questions[0].id, "pc_clarify_2")
        self.assertEqual(self.ai.fake_clarify_qg_call_count, 2)

        values = snap_values(runner, session_id)
        pending_ids = [q["id"] for q in values["pending_questions"]]
        self.assertEqual(pending_ids, ["pc_clarify_2"])

        done = runner.resume(
            session_id,
            {
                "answers": [
                    {
                        "question_id": "pc_clarify_2",
                        "value": "body_part",
                    },
                ]
            },
        )
        self.assertEqual(self.ai.fake_clarify_qg_call_count, 2)
        self.assertEqual(self.ai.fake_classifier_call_count, 3)
        self.assertEqual(done.phase, "localised_detail")


if __name__ == "__main__":
    unittest.main()
