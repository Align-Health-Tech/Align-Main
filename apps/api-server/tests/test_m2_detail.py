"""M2 localised_detail + non_localised_detail → priority_questions."""
from __future__ import annotations

import unittest

from engine.runner import SessionRunner
from schemas.clinical_ai_io import ClassifierResult
from tests.helpers import (
    answer_localised_detail,
    answer_nl_details,
    answer_pc_free_text,
    snap_values,
)
from tests.mock_clinical_ai import MockClinicalAiTestCase


class TestM2DetailNodes(MockClinicalAiTestCase, unittest.TestCase):
    def test_localised_fills_body_structures_then_priority(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        step = answer_pc_free_text(runner, session_id, "pain in my right wrist")
        self.assertEqual(step.phase, "localised_detail")
        self.assertEqual(step.step_type, "body_diagram")
        self.assertIsNone(step.questions)

        next_step = answer_localised_detail(runner, session_id)
        self.assertEqual(next_step.phase, "priority_questions")
        self.assertEqual(self.ai.fake_priority_qg_call_count, 1)

        values = snap_values(runner, session_id)
        self.assertIn("localised_detail", values["completed_phases"])
        self.assertEqual(values["severity_score"], 7)
        self.assertEqual(values["onset_circumstance"]["text"], "Within 48 hours")
        self.assertEqual(values["onset_circumstance"]["source"], "option")
        self.assertEqual(len(values["body_structures"]), 1)
        body = values["body_structures"][0]
        self.assertEqual(body["region_detail"]["layman_term"], "right wrist")
        self.assertEqual(body["laterality"], "right")
        self.assertEqual(body["severity_score"], 7)

    def test_non_localised_ready_then_details_to_priority(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        step = answer_pc_free_text(
            runner, session_id, "I have a fever and feel unwell"
        )
        self.assertEqual(step.phase, "non_localised_detail")
        ids = [q.id for q in (step.questions or [])]
        self.assertEqual(ids, ["nl_onset", "nl_severity", "nl_functional"])
        self.assertEqual(self.ai.fake_nl_classifier_call_count, 1)

        values = snap_values(runner, session_id)
        self.assertEqual(values["non_localised_category"], "SYSTEMIC")

        next_step = answer_nl_details(runner, session_id)
        self.assertEqual(next_step.phase, "priority_questions")

        values = snap_values(runner, session_id)
        self.assertIn("non_localised_detail", values["completed_phases"])
        self.assertEqual(values["severity_score"], 5)
        self.assertEqual(values["functional_impact_score"], 4)
        self.assertEqual(values["onset_circumstance"]["text"], "Within 1 week")
        self.assertEqual(values["onset_circumstance"]["source"], "option")

    def test_non_localised_clarify_then_details(self) -> None:
        self.ai.set_nl_classifier_script(
            [
                ClassifierResult(
                    ready=False,
                    category="SYSTEMIC",
                    reason="unclear",
                    confidence=0.5,
                ),
                ClassifierResult(
                    ready=True, category="SYSTEMIC", confidence=0.88
                ),
            ]
        )
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        step = answer_pc_free_text(
            runner, session_id, "I have a fever and feel unwell"
        )
        self.assertEqual(step.phase, "non_localised_detail")
        self.assertEqual(step.questions[0].id, "nl_clarify_1")
        self.assertEqual(self.ai.fake_nl_clarify_qg_call_count, 1)

        after_clarify = runner.resume(
            session_id,
            {
                "answers": [
                    {
                        "question_id": "nl_clarify_1",
                        "value": "Yes",
                    }
                ]
            },
        )
        self.assertEqual(self.ai.fake_nl_classifier_call_count, 2)
        self.assertEqual(self.ai.fake_nl_clarify_qg_call_count, 1)
        self.assertEqual(
            [q.id for q in (after_clarify.questions or [])],
            ["nl_onset", "nl_severity", "nl_functional"],
        )

        values = snap_values(runner, session_id)
        self.assertEqual(values["non_localised_category"], "SYSTEMIC")
        self.assertEqual(values["non_localised_clarify_rounds"], 1)

        done = answer_nl_details(runner, session_id)
        self.assertEqual(done.phase, "priority_questions")


if __name__ == "__main__":
    unittest.main()
