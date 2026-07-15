"""loc_onset timing single_choice — default only when stored text matches a chip."""
from __future__ import annotations

import unittest

from engine.helpers.apply_answers import apply_answers
from engine.runner import SessionRunner
from engine.static.onset_timing import ONSET_TIMING_OPTIONS
from schemas.clinical_ai_io import (
    ClassifierResult,
    EncounterIntakeSupplement,
    LocalisedAnatomySite,
)
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState
from tests.helpers import answer_body_diagram, answer_pc_free_text
from tests.mock_clinical_ai import MockClinicalAiTestCase


class TestLocOnsetDefaultValue(MockClinicalAiTestCase, unittest.TestCase):
    def test_default_none_when_classifier_mechanism_text(self) -> None:
        """Free-text mechanism from classifier is not a timing chip — no prefill."""
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
        onset = next(q for q in (step.questions or []) if q.id == "loc_onset")
        self.assertEqual(onset.kind, "single_choice")
        self.assertIsNone(onset.default_value)

    def test_default_value_when_stored_matches_timing_label(self) -> None:
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
                        onset_circumstance="Within 48 hours"
                    ),
                )
            ]
        )
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        answer_pc_free_text(runner, session_id, "pain in my right wrist")
        step = answer_body_diagram(runner, session_id)
        onset = next(q for q in (step.questions or []) if q.id == "loc_onset")
        self.assertEqual(onset.default_value, "WITHIN_48_HOURS")

    def test_default_value_none_when_onset_missing(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        answer_pc_free_text(runner, session_id, "pain in my right wrist")
        step = answer_body_diagram(runner, session_id)
        onset = next(q for q in (step.questions or []) if q.id == "loc_onset")
        self.assertIsNone(onset.default_value)


class TestLocOnsetApplyAnswers(unittest.TestCase):
    def test_apply_answers_stores_option_label(self) -> None:
        q = QuestionField(
            id="loc_onset",
            kind="single_choice",
            prompt="When did this start?",
            personalization_note="deterministic",
            collect_target_id="onset_circumstance",
            options=list(ONSET_TIMING_OPTIONS),
        )
        severity = QuestionField(
            id="loc_severity",
            kind="single_choice",
            prompt="severity",
            personalization_note="deterministic",
            collect_target_id="severity_score",
            options=[
                QuestionOption(value=str(i), label=str(i)) for i in range(0, 11)
            ],
        )
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            awaiting_phase="localised_detail",
            body_structures=[{"region_detail": {"layman_term": "right wrist"}}],
        )

        accepted = apply_answers(
            state,
            {
                "answers": [
                    {"question_id": "loc_severity", "value": "7"},
                    {"question_id": "loc_onset", "value": "WITHIN_48_HOURS"},
                ]
            },
            [severity, q],
        )
        self.assertEqual(accepted["onset_circumstance"]["text"], "Within 48 hours")
        self.assertEqual(accepted["onset_circumstance"]["source"], "option")
        self.assertEqual(accepted["severity_score"], 7)


if __name__ == "__main__":
    unittest.main()
