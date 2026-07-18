"""ICE apply — multi_choice chips + Other free text."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from engine.session_state_mappers import map_patient_answers
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState


def _ice_questions() -> list[QuestionField]:
    return [
        QuestionField(
            id="ice_idea",
            kind="multi_choice",
            prompt="Idea?",
            personalization_note="t",
            collect_target_id="ice_idea",
            options=[
                QuestionOption(value="Just a cold", label="Just a cold"),
                QuestionOption(value="Allergies", label="Allergies"),
                QuestionOption(value="Other", label="Other"),
            ],
        ),
        QuestionField(
            id="ice_concern",
            kind="multi_choice",
            prompt="Concern?",
            personalization_note="t",
            collect_target_id="ice_concern",
            options=[
                QuestionOption(value="Won't get better", label="Won't get better"),
                QuestionOption(value="Other", label="Other"),
            ],
        ),
        QuestionField(
            id="ice_expectation",
            kind="multi_choice",
            prompt="Expectation?",
            personalization_note="t",
            collect_target_id="ice_expectation",
            options=[
                QuestionOption(value="Medicine", label="Medicine"),
                QuestionOption(value="Other", label="Other"),
            ],
        ),
    ]


class TestApplyAnswersIce(unittest.TestCase):
    def _state(self, **kwargs) -> SessionState:
        base = dict(
            session_id="s1",
            patient_id="p1",
            organization_id="o1",
            awaiting_phase="ice",
            session_language="en",
        )
        base.update(kwargs)
        return SessionState(**base)

    def test_chip_option_writes_source_option(self) -> None:
        updates = map_patient_answers(
            self._state(),
            {
                "answers": [
                    {"question_id": "ice_idea", "value": "Just a cold"},
                    {"question_id": "ice_concern", "value": "Won't get better"},
                    {"question_id": "ice_expectation", "value": "Medicine"},
                ]
            },
            _ice_questions(),
        )
        self.assertEqual(updates["ice_idea"]["text"], "Just a cold")
        self.assertEqual(updates["ice_idea"]["source"], "option")
        self.assertIsNone(updates["ice_idea"].get("en_text"))

    def test_multi_select_joins_into_one_narrative(self) -> None:
        updates = map_patient_answers(
            self._state(),
            {
                "answers": [
                    {
                        "question_id": "ice_idea",
                        "value": ["Just a cold", "Allergies"],
                    },
                    {"question_id": "ice_concern", "value": "Won't get better"},
                    {"question_id": "ice_expectation", "value": "Medicine"},
                ]
            },
            _ice_questions(),
        )
        self.assertEqual(updates["ice_idea"]["text"], "Just a cold; Allergies")
        self.assertEqual(updates["ice_idea"]["source"], "option")

    def test_other_free_text_translates_when_not_english(self) -> None:
        with patch(
            "engine.agent_bridge.translate_to_english"
        ) as translate_mock:
            translate_mock.return_value = MagicMock(en_text="I think it is strep")
            updates = map_patient_answers(
                self._state(session_language="ko"),
                {
                    "answers": [
                        {
                            "question_id": "ice_idea",
                            "value": "Other:연쇄구균인 것 같아요",
                        },
                        {"question_id": "ice_concern", "value": "Won't get better"},
                        {"question_id": "ice_expectation", "value": "Medicine"},
                    ]
                },
                _ice_questions(),
            )
        translate_mock.assert_called_once_with("연쇄구균인 것 같아요", "ko")
        self.assertEqual(updates["ice_idea"]["text"], "연쇄구균인 것 같아요")
        self.assertEqual(updates["ice_idea"]["en_text"], "I think it is strep")
        self.assertEqual(updates["ice_idea"]["source"], "free_text")


if __name__ == "__main__":
    unittest.main()
