"""optional_questions apply — past_history / social_history intake facts."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from engine.session_state_mappers import map_patient_answers
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState


class TestApplyAnswersOptionalPastHistory(unittest.TestCase):
    def _state(self, **kwargs) -> SessionState:
        base = {
            "session_id": "s1",
            "patient_id": "p1",
            "organization_id": "o1",
            "session_language": "en",
            "awaiting_phase": "optional_questions",
            "turn_number": 5,
        }
        base.update(kwargs)
        return SessionState(**base)

    @staticmethod
    def _question() -> QuestionField:
        return QuestionField(
            id="past_history",
            kind="multi_choice",
            prompt="Which significant health events have you had before?",
            personalization_note="Past history could help contextualise this visit.",
            collect_target_id="past_history",
            required=False,
            options=[
                QuestionOption(value="Major surgery", label="Major surgery"),
                QuestionOption(
                    value="Hospital stay for serious illness",
                    label="Hospital stay for serious illness",
                ),
                QuestionOption(
                    value="Cancer treatment in the past",
                    label="Cancer treatment in the past",
                ),
                QuestionOption(value="Other", label="Other"),
            ],
        )

    def test_multi_select_creates_past_history_rows(self) -> None:
        existing = {
            "kind": "ALLERGY",
            "source": "PATIENT_INTAKE",
            "display": {"text": "penicillin", "source": "free_text"},
        }
        updates = map_patient_answers(
            self._state(intake_facts=[existing]),
            {
                "answers": [
                    {
                        "question_id": "past_history",
                        "value": [
                            "Major surgery",
                            "Hospital stay for serious illness",
                            "Cancer treatment in the past",
                            "Other: previous heart condition",
                        ],
                    }
                ]
            },
            [self._question()],
        )

        self.assertEqual(updates["turn_number"], 6)
        facts = updates["intake_facts"]
        self.assertEqual(facts[0], existing)
        self.assertEqual(
            [(f["kind"], f["display"]["text"]) for f in facts[1:]],
            [
                ("PAST_HISTORY", "Major surgery"),
                ("PAST_HISTORY", "Hospital stay for serious illness"),
                ("PAST_HISTORY", "Cancer treatment in the past"),
                ("PAST_HISTORY", "previous heart condition"),
            ],
        )
        self.assertTrue(all(f["source"] == "PATIENT_INTAKE" for f in facts[1:]))
        self.assertEqual(facts[-1]["display"]["source"], "free_text")

    def test_unknown_chip_stored_as_free_text_past_history(self) -> None:
        updates = map_patient_answers(
            self._state(),
            {
                "answers": [
                    {
                        "question_id": "past_history",
                        "value": ["Childhood rheumatic fever"],
                    }
                ]
            },
            [self._question()],
        )
        fact = updates["intake_facts"][0]
        self.assertEqual(fact["kind"], "PAST_HISTORY")
        self.assertEqual(fact["display"]["text"], "Childhood rheumatic fever")
        self.assertEqual(fact["display"]["source"], "free_text")

    def test_other_free_text_translates_when_not_english(self) -> None:
        with patch(
            "engine.agent_bridge.translate_to_english"
        ) as translate_mock:
            translate_mock.return_value = MagicMock(en_text="previous heart surgery")
            updates = map_patient_answers(
                self._state(session_language="mi"),
                {
                    "answers": [
                        {
                            "question_id": "past_history",
                            "value": ["Other: pokanga ngakau o mua"],
                        }
                    ]
                },
                [self._question()],
            )
        translate_mock.assert_called_once_with("pokanga ngakau o mua", "mi")
        fact = updates["intake_facts"][0]
        self.assertEqual(fact["kind"], "PAST_HISTORY")
        self.assertEqual(fact["display"]["text"], "pokanga ngakau o mua")
        self.assertEqual(fact["display"]["en_text"], "previous heart surgery")
        self.assertEqual(fact["display"]["source"], "free_text")

    def test_parent_yes_no_is_not_stored(self) -> None:
        parent = QuestionField(
            id="past_history_yes_no",
            kind="yes_no",
            prompt="Any significant past health events?",
            personalization_note="Past history check.",
            collect_target_id="past_history",
            required=False,
        )
        updates = map_patient_answers(
            self._state(),
            {"answers": [{"question_id": parent.id, "value": True}]},
            [parent],
        )
        self.assertNotIn("intake_facts", updates)

    def test_unanswered_past_history_leaves_existing_facts_untouched(self) -> None:
        updates = map_patient_answers(
            self._state(
                intake_facts=[
                    {
                        "kind": "PAST_HISTORY",
                        "source": "PATIENT_INTAKE",
                        "display": {"text": "appendectomy"},
                    }
                ]
            ),
            {"answers": []},
            [self._question()],
        )
        self.assertNotIn("intake_facts", updates)


class TestApplyAnswersOptionalSocialHistory(unittest.TestCase):
    """NOT_LOCALISED optional pool — social_history → SOCIAL_HISTORY facts."""

    def _state(self, **kwargs) -> SessionState:
        base = {
            "session_id": "s1",
            "patient_id": "p1",
            "organization_id": "o1",
            "session_language": "en",
            "awaiting_phase": "optional_questions",
            "presentation_category": "NOT_LOCALISED",
            "turn_number": 5,
        }
        base.update(kwargs)
        return SessionState(**base)

    @staticmethod
    def _multi_question() -> QuestionField:
        return QuestionField(
            id="social_history",
            kind="multi_choice",
            prompt="Which of these apply to you?",
            personalization_note="Social context for this presentation.",
            collect_target_id="social_history",
            required=False,
            options=[
                QuestionOption(value="Smoke or vape", label="Smoke or vape"),
                QuestionOption(value="Drink alcohol", label="Drink alcohol"),
                QuestionOption(value="Other", label="Other"),
            ],
        )

    def test_multi_select_creates_social_history_rows(self) -> None:
        updates = map_patient_answers(
            self._state(),
            {
                "answers": [
                    {
                        "question_id": "social_history",
                        "value": ["Smoke or vape", "Other: works night shifts"],
                    }
                ]
            },
            [self._multi_question()],
        )
        self.assertEqual(
            [(f["kind"], f["display"]["text"], f["display"]["source"])
             for f in updates["intake_facts"]],
            [
                ("SOCIAL_HISTORY", "Smoke or vape", "option"),
                ("SOCIAL_HISTORY", "works night shifts", "free_text"),
            ],
        )

    def test_free_text_question_stores_social_history_with_translate(self) -> None:
        question = QuestionField(
            id="social_history",
            kind="free_text",
            prompt="Tell us about smoking or alcohol use, if any.",
            personalization_note="Open social-history check.",
            collect_target_id="social_history",
            required=False,
        )
        with patch(
            "engine.agent_bridge.translate_to_english"
        ) as translate_mock:
            translate_mock.return_value = MagicMock(
                en_text="smokes 5 cigarettes a day"
            )
            updates = map_patient_answers(
                self._state(session_language="mi"),
                {
                    "answers": [
                        {
                            "question_id": "social_history",
                            "value": "e toru hikareti ia ra",
                        }
                    ]
                },
                [question],
            )
        translate_mock.assert_called_once_with("e toru hikareti ia ra", "mi")
        fact = updates["intake_facts"][0]
        self.assertEqual(fact["kind"], "SOCIAL_HISTORY")
        self.assertEqual(fact["display"]["text"], "e toru hikareti ia ra")
        self.assertEqual(fact["display"]["en_text"], "smokes 5 cigarettes a day")


class TestApplyAnswersOptionalEncounterFields(unittest.TestCase):
    def _state(self, **kwargs) -> SessionState:
        base = {
            "session_id": "s1",
            "patient_id": "p1",
            "organization_id": "o1",
            "session_language": "en",
            "awaiting_phase": "optional_questions",
            "turn_number": 5,
        }
        base.update(kwargs)
        return SessionState(**base)

    def test_family_history_and_encounter_optional_fields(self) -> None:
        questions = [
            QuestionField(
                id="family_history",
                kind="multi_choice",
                prompt="Family conditions?",
                personalization_note="t",
                collect_target_id="family_history",
                required=False,
                options=[
                    QuestionOption(value="Heart disease", label="Heart disease"),
                    QuestionOption(value="Other", label="Other"),
                ],
            ),
            QuestionField(
                id="self_management",
                kind="multi_choice",
                prompt="What have you tried?",
                personalization_note="t",
                collect_target_id="self_management",
                required=False,
                options=[
                    QuestionOption(value="Rest", label="Rest"),
                    QuestionOption(value="Ice", label="Ice"),
                    QuestionOption(value="Other", label="Other"),
                ],
            ),
            QuestionField(
                id="weight_change",
                kind="single_choice",
                prompt="Any weight change?",
                personalization_note="t",
                collect_target_id="weight_change",
                required=False,
                options=[
                    QuestionOption(value="Lost weight", label="Lost weight"),
                    QuestionOption(value="Other", label="Other"),
                ],
            ),
            QuestionField(
                id="exacerbating_factors",
                kind="free_text",
                prompt="What makes it worse?",
                personalization_note="t",
                collect_target_id="exacerbating_factors",
                required=False,
            ),
            QuestionField(
                id="mitigating_factors",
                kind="free_text",
                prompt="What helps?",
                personalization_note="t",
                collect_target_id="mitigating_factors",
                required=False,
            ),
        ]
        updates = map_patient_answers(
            self._state(),
            {
                "answers": [
                    {
                        "question_id": "family_history",
                        "value": ["Heart disease"],
                    },
                    {
                        "question_id": "self_management",
                        "value": ["Rest", "Ice"],
                    },
                    {"question_id": "weight_change", "value": "Lost weight"},
                    {
                        "question_id": "exacerbating_factors",
                        "value": "twisting the wrist",
                    },
                    {"question_id": "mitigating_factors", "value": "keeping still"},
                ]
            },
            questions,
        )
        self.assertEqual(updates["intake_facts"][0]["kind"], "FAMILY_HISTORY")
        self.assertEqual(updates["intake_facts"][0]["display"]["text"], "Heart disease")
        self.assertEqual(updates["self_management"]["text"], "Rest; Ice")
        self.assertEqual(updates["self_management"]["source"], "option")
        self.assertEqual(updates["weight_change"], "Lost weight")
        self.assertEqual(
            updates["exacerbating_factors"][0]["text"], "twisting the wrist"
        )
        self.assertEqual(updates["mitigating_factors"][0]["text"], "keeping still")


if __name__ == "__main__":
    unittest.main()
