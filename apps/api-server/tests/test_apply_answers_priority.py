"""Unit tests for priority_questions apply."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from engine.session_state_mappers import map_patient_answers
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState


class TestApplyAnswersPriorityMedication(unittest.TestCase):
    def _state(self, **kwargs) -> SessionState:
        base = dict(
            session_id="s1",
            patient_id="p1",
            organization_id="o1",
            awaiting_phase="priority_questions",
            session_language="en",
            turn_number=3,
        )
        base.update(kwargs)
        return SessionState(**base)

    def _med_questions(self) -> list[QuestionField]:
        return [
            QuestionField(
                id="med_parent",
                kind="yes_no",
                prompt="Are you taking any medicines for your current symptoms?",
                personalization_note="test",
                collect_target_id="medication",
            ),
            QuestionField(
                id="med_which",
                kind="multi_choice",
                prompt="Which ones?",
                personalization_note="test",
                collect_target_id="medication",
                options=[
                    QuestionOption(value="Panadol", label="Panadol"),
                    QuestionOption(value="Ibuprofen", label="Ibuprofen"),
                    QuestionOption(value="Voltaren", label="Voltaren"),
                    QuestionOption(value="Other", label="Other"),
                ],
            ),
        ]

    def test_parent_yes_plus_multi_choice_writes_encounter_medication_only(
        self,
    ) -> None:
        with patch(
            "engine.agent_bridge.translate_to_english"
        ) as translate_mock:
            translate_mock.side_effect = AssertionError(
                "en session must not call translate"
            )
            updates = map_patient_answers(
                self._state(intake_facts=[{"kind": "ALLERGY", "display": {"text": "x"}}]),
                {
                    "answers": [
                        {"question_id": "med_parent", "value": True},
                        {
                            "question_id": "med_which",
                            "value": ["Panadol", "Other: fish oil"],
                        },
                    ]
                },
                self._med_questions(),
            )

        self.assertIn("encounter_medication", updates)
        meds = updates["encounter_medication"]
        self.assertEqual(len(meds), 2)
        self.assertEqual(meds[0]["text"], "Panadol")
        self.assertEqual(meds[0]["source"], "option")
        self.assertEqual(meds[1]["text"], "fish oil")
        self.assertEqual(meds[1]["source"], "free_text")
        self.assertNotIn("intake_facts", updates)
        self.assertEqual(updates["turn_number"], 4)

    def test_parent_no_clears_encounter_medication(self) -> None:
        updates = map_patient_answers(
            self._state(encounter_medication=[{"text": "stale", "source": "option"}]),
            {"answers": [{"question_id": "med_parent", "value": False}]},
            self._med_questions(),
        )
        self.assertEqual(updates["encounter_medication"], [])
        self.assertNotIn("intake_facts", updates)

    def test_pregnancy_sets_bool_not_intake_facts(self) -> None:
        q = QuestionField(
            id="preg_q",
            kind="yes_no",
            prompt="Is there any chance you could be pregnant?",
            personalization_note="test",
            collect_target_id="pregnancy",
        )
        updates = map_patient_answers(
            self._state(),
            {"answers": [{"question_id": "preg_q", "value": "Yes"}]},
            [q],
        )
        self.assertEqual(updates["pregnancy_possible"], True)
        self.assertNotIn("intake_facts", updates)


class TestApplyAnswersPriorityRest(unittest.TestCase):
    def _state(self, **kwargs) -> SessionState:
        base = dict(
            session_id="s1",
            patient_id="p1",
            organization_id="o1",
            awaiting_phase="priority_questions",
            session_language="en",
            turn_number=3,
        )
        base.update(kwargs)
        return SessionState(**base)

    def test_character_and_comorbidities_and_onset(self) -> None:
        questions = [
            QuestionField(
                id="character",
                kind="multi_choice",
                prompt="What does it feel like?",
                personalization_note="t",
                collect_target_id="character",
                options=[
                    QuestionOption(value="Sharp", label="Sharp"),
                    QuestionOption(value="Other", label="Other"),
                ],
            ),
            QuestionField(
                id="comorbidities",
                kind="multi_choice",
                prompt="Any long-term conditions?",
                personalization_note="t",
                collect_target_id="comorbidities",
                options=[
                    QuestionOption(value="Asthma", label="Asthma"),
                    QuestionOption(
                        value="None of these", label="None of these"
                    ),
                ],
            ),
            QuestionField(
                id="onset",
                kind="single_choice",
                prompt="When did this start?",
                personalization_note="t",
                collect_target_id="onset_circumstance",
                options=[
                    QuestionOption(
                        value="LAST_24_HOURS", label="Last 24 hours"
                    ),
                ],
            ),
        ]
        updates = map_patient_answers(
            self._state(),
            {
                "answers": [
                    {
                        "question_id": "character",
                        "value": ["Sharp", "Other: throbbing"],
                    },
                    {"question_id": "comorbidities", "value": ["Asthma"]},
                    {"question_id": "onset", "value": "LAST_24_HOURS"},
                ]
            },
            questions,
        )
        self.assertEqual(
            [(c["text"], c["source"]) for c in updates["character"]],
            [("Sharp", "option"), ("throbbing", "free_text")],
        )
        self.assertEqual(updates["comorbidities"][0]["text"], "Asthma")
        self.assertEqual(updates["onset_circumstance"]["text"], "Last 24 hours")
        self.assertEqual(updates["onset_circumstance"]["source"], "option")

    def test_comorbidities_none_of_these_clears(self) -> None:
        q = QuestionField(
            id="comorbidities",
            kind="multi_choice",
            prompt="Any long-term conditions?",
            personalization_note="t",
            collect_target_id="comorbidities",
            options=[
                QuestionOption(value="Asthma", label="Asthma"),
                QuestionOption(value="None of these", label="None of these"),
            ],
        )
        updates = map_patient_answers(
            self._state(comorbidities=[{"text": "Asthma", "source": "option"}]),
            {"answers": [{"question_id": "comorbidities", "value": ["None of these"]}]},
            [q],
        )
        self.assertEqual(updates["comorbidities"], [])

    def test_allergy_appends_intake_facts_with_translate(self) -> None:
        q = QuestionField(
            id="allergy",
            kind="multi_choice",
            prompt="Any allergies?",
            personalization_note="t",
            collect_target_id="allergy",
            options=[
                QuestionOption(value="Penicillin", label="Penicillin"),
                QuestionOption(value="Other", label="Other"),
            ],
        )
        existing = {
            "kind": "PAST_HISTORY",
            "source": "PATIENT_INTAKE",
            "display": {"text": "appendectomy", "source": "option"},
        }
        with patch(
            "engine.agent_bridge.translate_to_english"
        ) as translate_mock:
            translate_mock.return_value = MagicMock(en_text="peanut allergy")
            updates = map_patient_answers(
                self._state(session_language="mi", intake_facts=[existing]),
                {
                    "answers": [
                        {
                            "question_id": "allergy",
                            "value": ["Penicillin", "Other: mate pīnati"],
                        }
                    ]
                },
                [q],
            )
        translate_mock.assert_called_once_with("mate pīnati", "mi")
        facts = updates["intake_facts"]
        self.assertEqual(facts[0], existing)
        self.assertEqual(facts[1]["kind"], "ALLERGY")
        self.assertEqual(facts[1]["display"]["text"], "Penicillin")
        self.assertEqual(facts[2]["display"]["text"], "mate pīnati")
        self.assertEqual(facts[2]["display"]["en_text"], "peanut allergy")

    def test_no_allergies_does_not_create_intake_fact(self) -> None:
        q = QuestionField(
            id="allergy",
            kind="multi_choice",
            prompt="Any allergies?",
            personalization_note="t",
            collect_target_id="allergy",
            options=[
                QuestionOption(value="Medicines", label="Medicines"),
                QuestionOption(value="No allergies", label="No allergies"),
                QuestionOption(
                    value="No known allergies",
                    label="No known allergies",
                ),
                QuestionOption(
                    value="No allergies that I know of",
                    label="No allergies that I know of",
                ),
                QuestionOption(value="Other", label="Other"),
            ],
        )
        existing = {
            "kind": "PAST_HISTORY",
            "source": "PATIENT_INTAKE",
            "display": {"text": "appendectomy", "source": "option"},
        }

        for value in (
            "No allergies",
            "No known allergies",
            "No allergies that I know of",
        ):
            with self.subTest(value=value):
                updates = map_patient_answers(
                    self._state(intake_facts=[existing]),
                    {
                        "answers": [
                            {
                                "question_id": "allergy",
                                "value": [value],
                            }
                        ]
                    },
                    [q],
                )
                self.assertNotIn("intake_facts", updates)


class TestIntakeFactItemsRlsMigration(unittest.TestCase):
    """Policy in intake_patient_scope_meds_001 must use patient-linkage, not encounter_id."""

    def test_upgrade_sql_mirrors_patients_linkage(self) -> None:
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "intake_patient_scope_meds.py"
        )
        src = path.read_text()
        self.assertIn(
            "patient_id = (\n"
            "            SELECT patient_id FROM encounters WHERE id = app.current_encounter_id()",
            src,
        )
        upgrade = src.split("def downgrade")[0]
        self.assertNotIn(
            "encounter_id = app.current_encounter_id()",
            upgrade,
        )


if __name__ == "__main__":
    unittest.main()
