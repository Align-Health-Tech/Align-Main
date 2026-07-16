"""QG phase output validators — clarify constraints fail loudly."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from engine.helpers import agent_bridge
from engine.helpers.qg_phase_validators import validate_qg_questions
from schemas.clinical_ai_io import QuestionGenerationResult
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate
from tests.mock_clinical_ai import MockClinicalAiTestCase


def _pc_ok(**kwargs) -> QuestionField:
    base = dict(
        id="pc_clarify_1",
        kind="single_choice",
        prompt="Which fits?",
        personalization_note="t",
        options=[
            QuestionOption(value="a", label="A"),
            QuestionOption(value="Other", label="Other"),
        ],
    )
    base.update(kwargs)
    return QuestionField(**base)


def _nl_ok(**kwargs) -> QuestionField:
    base = dict(
        id="nl_clarify_1",
        kind="single_choice",
        prompt="Fever?",
        personalization_note="t",
        options=[
            QuestionOption(value="Yes", label="Yes"),
            QuestionOption(value="No", label="No"),
            QuestionOption(value="I don't know", label="I don't know"),
        ],
    )
    base.update(kwargs)
    return QuestionField(**base)


class TestValidateQgQuestions(unittest.TestCase):
    def test_unknown_phase_skips(self) -> None:
        validate_qg_questions(
            "not_a_registered_phase",
            [
                QuestionField(
                    id="x",
                    kind="free_text",
                    prompt="p",
                    personalization_note="n",
                )
            ],
        )

    def test_priority_comorbidities_rejects_other(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "priority_questions",
                [
                    QuestionField(
                        id="comorbidities",
                        kind="multi_choice",
                        prompt="Conditions?",
                        personalization_note="t",
                        collect_target_id="comorbidities",
                        options=[
                            QuestionOption(value="Asthma", label="Asthma"),
                            QuestionOption(value="Other", label="Other"),
                        ],
                    )
                ],
            )
        self.assertIn("Other", str(ctx.exception))

    def test_priority_comorbidities_requires_none_of_these(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "priority_questions",
                [
                    QuestionField(
                        id="comorbidities",
                        kind="multi_choice",
                        prompt="Conditions?",
                        personalization_note="t",
                        collect_target_id="comorbidities",
                        options=[
                            QuestionOption(value="Asthma", label="Asthma"),
                        ],
                    )
                ],
            )
        self.assertIn("None of these", str(ctx.exception))

    def test_priority_comorbidities_accepts_valid(self) -> None:
        validate_qg_questions(
            "priority_questions",
            [
                QuestionField(
                    id="comorbidities",
                    kind="multi_choice",
                    prompt="Conditions?",
                    personalization_note="t",
                    collect_target_id="comorbidities",
                    options=[
                        QuestionOption(value="Asthma", label="Asthma"),
                        QuestionOption(value="None of these", label="None of these"),
                    ],
                )
            ],
        )

    def test_priority_non_comorbid_passes(self) -> None:
        validate_qg_questions(
            "priority_questions",
            [
                QuestionField(
                    id="allergy",
                    kind="multi_choice",
                    prompt="Allergies?",
                    personalization_note="t",
                    collect_target_id="allergy",
                    options=[
                        QuestionOption(value="Other", label="Other"),
                    ],
                )
            ],
        )

    def test_pc_clarify_rejects_free_text(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "presenting_complaint_clarify",
                [_pc_ok(kind="free_text", options=None)],
            )
        self.assertIn("single_choice", str(ctx.exception))

    def test_pc_clarify_rejects_missing_other(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "presenting_complaint_clarify",
                [
                    _pc_ok(
                        options=[
                            QuestionOption(value="a", label="A"),
                            QuestionOption(value="b", label="B"),
                        ]
                    )
                ],
            )
        self.assertIn("Other", str(ctx.exception))

    def test_pc_clarify_rejects_option_count(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "presenting_complaint_clarify",
                [
                    _pc_ok(
                        options=[QuestionOption(value="Other", label="Other")]
                    )
                ],
            )
        self.assertIn("2–5", str(ctx.exception))

    def test_pc_clarify_accepts_valid(self) -> None:
        validate_qg_questions("presenting_complaint_clarify", [_pc_ok()])

    def test_nl_clarify_rejects_wrong_options(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "non_localised_clarify",
                [
                    _nl_ok(
                        options=[
                            QuestionOption(value="Yes", label="Yes"),
                            QuestionOption(value="No", label="No"),
                        ]
                    )
                ],
            )
        self.assertIn("exactly", str(ctx.exception))

    def test_nl_clarify_accepts_valid(self) -> None:
        validate_qg_questions("non_localised_clarify", [_nl_ok()])


class TestDeviseThenGenerateValidates(MockClinicalAiTestCase, unittest.TestCase):
    def test_bad_qg_output_raises_through_bridge(self) -> None:
        state = SessionState(
            session_id="s", patient_id="p", organization_id="o"
        )
        bad = QuestionGenerationResult(
            reason="drift",
            questions=[
                QuestionField(
                    id="pc_clarify_1",
                    kind="free_text",
                    prompt="oops",
                    personalization_note="n",
                )
            ],
        )
        with patch.object(
            agent_bridge,
            "run_devise_and_prioritise",
            return_value=[
                TopicCandidate(
                    topic="t",
                    relevance_score=0.5,
                    is_red_flag=False,
                    source="base_reasoning",
                )
            ],
        ), patch.object(
            agent_bridge, "run_question_generation", return_value=bad
        ):
            with self.assertRaises(ValueError) as ctx:
                agent_bridge.devise_then_generate(
                    "presenting_complaint_clarify", state
                )
            self.assertIn("single_choice", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
