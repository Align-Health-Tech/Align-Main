"""loc_onset default_value prefill from classifier onset_circumstance."""
from __future__ import annotations

import unittest

from engine.helpers.apply_answers import apply_answers
from engine.runner import SessionRunner
from schemas.clinical_ai_io import (
    ClassifierResult,
    EncounterIntakeSupplement,
    LocalisedAnatomySite,
)
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState
from tests.helpers import answer_body_diagram, answer_pc_free_text
from tests.mock_clinical_ai import MockClinicalAiTestCase


class TestLocOnsetDefaultValue(MockClinicalAiTestCase, unittest.TestCase):
    def test_default_value_when_onset_already_set(self) -> None:
        self.ai.set_classifier_script(
            [
                ClassifierResult(
                    ready=True,
                    category="LOCALISED",
                    confidence=0.9,
                    reason="wrist",
                    localised_anatomy_sites=[
                        LocalisedAnatomySite(
                            body_part="wrist",
                            side="right",
                            surface="front",
                            major_region="arm",
                            confidence=0.95,
                            evidence="right wrist",
                        )
                    ],
                    encounter_intake_supplement=EncounterIntakeSupplement(
                        onset_circumstance="twisted it yesterday"
                    ),
                )
            ]
        )
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        answer_pc_free_text(runner, session_id, "pain in my right wrist")
        step = answer_body_diagram(runner, session_id)
        self.assertEqual(step.step_type, "question_batch")
        onset = next(q for q in (step.questions or []) if q.id == "loc_onset")
        self.assertEqual(onset.default_value, "twisted it yesterday")

    def test_default_value_none_when_onset_missing(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        answer_pc_free_text(runner, session_id, "pain in my right wrist")
        step = answer_body_diagram(runner, session_id)
        onset = next(q for q in (step.questions or []) if q.id == "loc_onset")
        self.assertIsNone(onset.default_value)


class TestLocOnsetApplyAnswers(unittest.TestCase):
    def test_apply_answers_accepts_unchanged_default_and_edited(self) -> None:
        q = QuestionField(
            id="loc_onset",
            kind="free_text",
            prompt="How did this start?",
            personalization_note="deterministic",
            collect_target_id="onset_circumstance",
            default_value="twisted it",
        )
        severity = QuestionField(
            id="loc_severity",
            kind="single_choice",
            prompt="severity",
            personalization_note="deterministic",
            collect_target_id="severity_score",
            options=[],
        )
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            awaiting_phase="localised_detail",
            body_structures=[{"region_detail": {"layman_term": "right wrist"}}],
            onset_circumstance={"text": "twisted it", "source": "free_text"},
        )

        accepted = apply_answers(
            state,
            {
                "answers": [
                    {"question_id": "loc_severity", "value": "7"},
                    {"question_id": "loc_onset", "value": "twisted it"},
                ]
            },
            [severity, q],
        )
        self.assertEqual(accepted["onset_circumstance"]["text"], "twisted it")
        self.assertEqual(accepted["severity_score"], 7)

        edited = apply_answers(
            state,
            {
                "answers": [
                    {"question_id": "loc_severity", "value": "5"},
                    {"question_id": "loc_onset", "value": "fell on ice"},
                ]
            },
            [severity, q],
        )
        self.assertEqual(edited["onset_circumstance"]["text"], "fell on ice")
        self.assertEqual(edited["severity_score"], 5)


if __name__ == "__main__":
    unittest.main()
