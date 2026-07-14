"""M0 Option-2 — graph starts at presenting_complaint free-text gate."""
from __future__ import annotations

import unittest

from engine.runner import SessionRunner
from tests.helpers import answer_localised_detail, answer_pc_free_text
from tests.mock_clinical_ai import MockClinicalAiTestCase


class TestM0Option2(MockClinicalAiTestCase, unittest.TestCase):
    def test_pc_localised_priority_option2(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")

        session_id, step1 = runner.start()
        self.assertEqual(step1.phase, "presenting_complaint")
        self.assertEqual(step1.questions[0].id, "pc_chief_complaint")
        self.assertEqual(self.ai.fake_priority_qg_call_count, 0)

        step2 = answer_pc_free_text(runner, session_id, "pain in my right wrist")
        self.assertEqual(step2.phase, "localised_detail")
        self.assertEqual(self.ai.fake_classifier_call_count, 1)

        step3 = answer_localised_detail(runner, session_id)
        self.assertEqual(step3.phase, "priority_questions")
        self.assertEqual(self.ai.fake_priority_qg_call_count, 1)

        step4 = runner.resume(
            session_id,
            {"answers": [{"question_id": "meds_q1", "value": "yes"}]},
        )
        self.assertEqual(
            self.ai.fake_priority_qg_call_count,
            1,
            "resume must not re-call priority QG",
        )
        self.assertEqual(step4.phase, "redflag_screening")


if __name__ == "__main__":
    unittest.main()
