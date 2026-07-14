"""M3 priority → redflag → optional; raised_flag_topics + optional skip → ice."""
from __future__ import annotations

import unittest

from engine.runner import SessionRunner
from tests.helpers import (
    answer_localised_detail,
    answer_pc_free_text,
    snap_values,
)
from tests.mock_clinical_ai import MockClinicalAiTestCase


def _to_priority(runner: SessionRunner, session_id: str):
    answer_pc_free_text(runner, session_id, "pain in my right wrist")
    return answer_localised_detail(runner, session_id)


class TestM3SharedTail(MockClinicalAiTestCase, unittest.TestCase):
    def test_priority_redflag_optional_to_ice_with_flags(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()

        pri = _to_priority(runner, session_id)
        self.assertEqual(pri.phase, "priority_questions")

        rf = runner.resume(
            session_id,
            {"answers": [{"question_id": "meds_q1", "value": "yes"}]},
        )
        self.assertEqual(rf.phase, "redflag_screening")

        opt = runner.resume(
            session_id,
            {
                "answers": [
                    {"question_id": "rf_chest_pain", "value": "yes"},
                    {"question_id": "rf_neuro", "value": "no"},
                ]
            },
        )
        self.assertEqual(self.ai.fake_redflag_qg_call_count, 1)
        self.assertEqual(opt.phase, "optional_questions")

        values = snap_values(runner, session_id)
        self.assertEqual(values["raised_flag_topics"], ["chest_pain"])

        ice_step = runner.resume(
            session_id,
            {"answers": [{"question_id": "opt_sleep", "value": "yes"}]},
        )
        self.assertEqual(self.ai.fake_optional_qg_call_count, 1)
        self.assertEqual(ice_step.phase, "ice")
        self.assertIn(
            "optional_questions",
            snap_values(runner, session_id)["completed_phases"],
        )

    def test_optional_skip_goes_to_ice(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        _to_priority(runner, session_id)
        runner.resume(
            session_id,
            {"answers": [{"question_id": "meds_q1", "value": "no"}]},
        )
        runner.resume(
            session_id,
            {
                "answers": [
                    {"question_id": "rf_chest_pain", "value": "no"},
                    {"question_id": "rf_neuro", "value": "no"},
                ]
            },
        )

        ice_step = runner.resume(session_id, {"skip": True})
        self.assertEqual(ice_step.phase, "ice")
        self.assertIn(
            "optional_questions",
            snap_values(runner, session_id)["completed_phases"],
        )

    def test_redflag_yes_dedupes_topics(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        _to_priority(runner, session_id)
        runner.resume(
            session_id,
            {"answers": [{"question_id": "meds_q1", "value": "no"}]},
        )
        runner.resume(
            session_id,
            {
                "answers": [
                    {"question_id": "rf_chest_pain", "value": "yes"},
                    {"question_id": "rf_neuro", "value": "yes"},
                ]
            },
        )
        values = snap_values(runner, session_id)
        self.assertEqual(
            values["raised_flag_topics"],
            ["chest_pain", "neurological_deficit"],
        )


if __name__ == "__main__":
    unittest.main()
