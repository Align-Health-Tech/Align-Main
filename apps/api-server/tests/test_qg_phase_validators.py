"""QG phase output validators — clarify constraints fail loudly."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from engine.helpers import agent_bridge
from engine.helpers.qg_phase_validators import validate_qg_questions
from engine.nodes.ice import ice
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
    def test_unknown_phase_fails_loudly(self) -> None:
        with self.assertRaises(ValueError) as ctx:
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
        self.assertIn("Unknown QG phase", str(ctx.exception))

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

    def test_priority_comorbidities_rejects_non_multi_choice(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "priority_questions",
                [
                    QuestionField(
                        id="comorbidities",
                        kind="yes_no",
                        prompt="Any ongoing conditions?",
                        personalization_note="t",
                        collect_target_id="comorbidities",
                    )
                ],
            )
        self.assertIn("multi_choice", str(ctx.exception))

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

    def test_redflag_allows_empty(self) -> None:
        validate_qg_questions("redflag_screening", [])

    def test_redflag_rejects_non_yes_no(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "redflag_screening",
                [
                    QuestionField(
                        id="rf_bad",
                        kind="single_choice",
                        prompt="Any chest pain?",
                        personalization_note="t",
                        collect_target_id="CIRCULATION",
                        options=[
                            QuestionOption(value="Yes", label="Yes"),
                            QuestionOption(value="No", label="No"),
                        ],
                    )
                ],
            )
        self.assertIn("yes_no", str(ctx.exception))

    def test_redflag_accepts_yes_no(self) -> None:
        validate_qg_questions(
            "redflag_screening",
            [
                QuestionField(
                    id="rf_circulation_1",
                    kind="yes_no",
                    prompt="Does your hand feel colder than usual?",
                    personalization_note="t",
                    collect_target_id="CIRCULATION",
                )
            ],
        )

    def test_optional_allows_empty(self) -> None:
        validate_qg_questions("optional_questions", [])

    def test_optional_requires_questions_to_be_skippable(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "optional_questions",
                [
                    QuestionField(
                        id="social_history",
                        kind="yes_no",
                        prompt="Do you smoke or vape?",
                        personalization_note="Relevant respiratory context.",
                        collect_target_id="social_history",
                        required=True,
                    )
                ],
            )
        self.assertIn("required must be false", str(ctx.exception))

    def test_optional_past_history_accepts_multi_choice_with_other(self) -> None:
        validate_qg_questions(
            "optional_questions",
            [
                QuestionField(
                    id="past_history",
                    kind="multi_choice",
                    prompt="Which significant health events have you had?",
                    personalization_note="Relevant past history.",
                    collect_target_id="past_history",
                    required=False,
                    options=[
                        QuestionOption(
                            value="Major surgery", label="Major surgery"
                        ),
                        QuestionOption(value="Other", label="Other"),
                    ],
                )
            ],
        )

    def test_optional_other_multi_choice_requires_other(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions(
                "optional_questions",
                [
                    QuestionField(
                        id="self_management",
                        kind="multi_choice",
                        prompt="What have you tried?",
                        personalization_note="Self-management check.",
                        collect_target_id="self_management",
                        required=False,
                        options=[
                            QuestionOption(value="rest", label="Rest"),
                        ],
                    )
                ],
            )
        self.assertIn("must include 'Other' or 'other'", str(ctx.exception))

    def test_optional_rejects_more_than_four_questions(self) -> None:
        questions = [
            QuestionField(
                id=f"optional_{i}",
                kind="yes_no",
                prompt=f"Optional question {i}?",
                personalization_note="test",
                collect_target_id="self_management",
                required=False,
            )
            for i in range(5)
        ]
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions("optional_questions", questions)
        self.assertIn("at most 4", str(ctx.exception))

    def test_ice_requires_exact_three_free_text_targets(self) -> None:
        valid = [
            QuestionField(
                id=target,
                kind="free_text",
                prompt=f"Prompt for {target}",
                personalization_note="test",
                collect_target_id=target,
            )
            for target in ("ice_idea", "ice_concern", "ice_expectation")
        ]
        validate_qg_questions("ice", valid)

        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions("ice", valid[:2])
        self.assertIn("exactly", str(ctx.exception))

        invalid_kind = [q.model_copy() for q in valid]
        invalid_kind[0] = invalid_kind[0].model_copy(update={"kind": "yes_no"})
        with self.assertRaises(ValueError) as ctx:
            validate_qg_questions("ice", invalid_kind)
        self.assertIn("free_text", str(ctx.exception))


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


class TestIceNodeValidatesWithoutDevise(unittest.TestCase):
    def test_ice_validates_direct_qg_and_never_calls_devise(self) -> None:
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
        )
        bad = QuestionGenerationResult(
            reason="drift",
            questions=[
                QuestionField(
                    id="ice_idea",
                    kind="yes_no",
                    prompt="Do you think this is a sprain?",
                    personalization_note="test",
                    collect_target_id="ice_idea",
                )
            ],
        )
        with patch.object(
            agent_bridge, "run_question_generation", return_value=bad
        ), patch.object(agent_bridge, "run_devise_and_prioritise") as devise:
            with self.assertRaises(ValueError):
                ice(state)
            devise.assert_not_called()


if __name__ == "__main__":
    unittest.main()
