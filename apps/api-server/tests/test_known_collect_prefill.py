"""known_collect_values → QG prefill shape across priority categories (mock)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from engine.helpers.agent_bridge import build_agent_context, devise_then_generate
from schemas.clinical_ai_io import QuestionGenerationInput, QuestionGenerationResult
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate


def _state_with_multi_known() -> SessionState:
    """Onset + character + allergy + comorbidities already known (beyond onset alone)."""
    return SessionState(
        session_id="s",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="male",
        presentation_category="LOCALISED",
        onset_circumstance={"text": "I twisted it", "source": "free_text"},
        character=[{"text": "Sharp", "source": "option"}],
        comorbidities=[{"text": "Asthma", "source": "option"}],
        intake_facts=[
            {
                "kind": "ALLERGY",
                "source": "PATIENT_INTAKE",
                "display": {"text": "penicillin", "source": "free_text"},
            }
        ],
    )


class TestKnownCollectValuesMultiCategory(unittest.TestCase):
    def test_context_seeds_allergy_and_comorbidities_beyond_onset(self) -> None:
        ctx = build_agent_context(_state_with_multi_known())
        known = ctx["known_collect_values"]
        self.assertIn("onset_circumstance", known)
        self.assertIn("character", known)
        self.assertIn("allergy", known)
        self.assertIn("comorbidities", known)
        self.assertEqual(known["allergy"], "penicillin")
        self.assertEqual(known["comorbidities"], ["Asthma"])

    def test_qg_receives_known_values_and_prefills_all_seeded_targets(self) -> None:
        """Mock QG: for every known target id, emit a question with default_*(s)."""
        state = _state_with_multi_known()
        captured: dict = {}

        def fake_devise(
            phase: str, context: dict, *, tool_choice: str | None = None
        ) -> list[TopicCandidate]:
            return [
                TopicCandidate(
                    topic=tid,
                    relevance_score=0.9,
                    is_red_flag=False,
                    source="base_reasoning",
                )
                for tid in (
                    "onset_circumstance",
                    "character",
                    "allergy",
                    "comorbidities",
                )
            ]

        def fake_qg(inp: QuestionGenerationInput) -> QuestionGenerationResult:
            captured["known"] = dict(inp.context.get("known_collect_values") or {})
            known = captured["known"]
            questions: list[QuestionField] = []
            # Onset — multi_choice prefill
            if "onset_circumstance" in known:
                questions.append(
                    QuestionField(
                        id="onset_circumstance",
                        kind="multi_choice",
                        prompt="How did this happen?",
                        personalization_note="prefill onset",
                        collect_target_id="onset_circumstance",
                        default_values=["I twisted it"],
                        options=[
                            QuestionOption(value="I twisted it", label="I twisted it"),
                            QuestionOption(value="Other", label="Other"),
                        ],
                    )
                )
            # Character — multi_choice prefill
            if "character" in known:
                questions.append(
                    QuestionField(
                        id="character",
                        kind="multi_choice",
                        prompt="How does the pain feel?",
                        personalization_note="prefill character",
                        collect_target_id="character",
                        default_values=["Sharp"],
                        options=[
                            QuestionOption(value="Sharp", label="Sharp"),
                            QuestionOption(value="Other", label="Other"),
                        ],
                    )
                )
            # Allergy — beyond onset
            if "allergy" in known:
                questions.append(
                    QuestionField(
                        id="allergy",
                        kind="multi_choice",
                        prompt="Do you have any allergies?",
                        personalization_note="prefill allergy",
                        collect_target_id="allergy",
                        default_values=["Medicines"],
                        options=[
                            QuestionOption(value="Medicines", label="Medicines"),
                            QuestionOption(value="Other", label="Other"),
                        ],
                    )
                )
            # Comorbidities — beyond onset
            if "comorbidities" in known:
                questions.append(
                    QuestionField(
                        id="comorbidities",
                        kind="multi_choice",
                        prompt="Any long-term conditions?",
                        personalization_note="prefill comorbidities",
                        collect_target_id="comorbidities",
                        default_values=["Asthma"],
                        options=[
                            QuestionOption(value="Asthma", label="Asthma"),
                            QuestionOption(value="None of these", label="None of these"),
                        ],
                    )
                )
            return QuestionGenerationResult(reason="mock multi-prefill", questions=questions)

        with (
            patch(
                "engine.helpers.agent_bridge.run_devise_and_prioritise",
                side_effect=fake_devise,
            ),
            patch(
                "engine.helpers.agent_bridge.run_question_generation",
                side_effect=fake_qg,
            ),
        ):
            _topics, questions = devise_then_generate("priority_questions", state)

        self.assertEqual(
            set(captured["known"]),
            {"onset_circumstance", "character", "allergy", "comorbidities"},
        )
        by_target = {q.collect_target_id: q for q in questions}
        for tid in ("onset_circumstance", "character", "allergy", "comorbidities"):
            self.assertIn(tid, by_target, f"missing question for {tid}")
            q = by_target[tid]
            self.assertTrue(
                bool(q.default_value) or bool(q.default_values),
                f"{tid} missing prefill",
            )


if __name__ == "__main__":
    unittest.main()
