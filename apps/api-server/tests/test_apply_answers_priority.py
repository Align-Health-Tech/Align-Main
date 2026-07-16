"""Unit tests for priority_questions apply — medication + pregnancy."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from engine.helpers.apply import apply_answers
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
            "engine.helpers.translate.agent_bridge.translate_to_english"
        ) as translate_mock:
            translate_mock.side_effect = AssertionError(
                "en session must not call translate"
            )
            updates = apply_answers(
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
        updates = apply_answers(
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
        updates = apply_answers(
            self._state(),
            {"answers": [{"question_id": "preg_q", "value": "Yes"}]},
            [q],
        )
        self.assertEqual(updates["pregnancy_possible"], True)
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
        # Patient-linkage subquery (same shape as patients / consents RLS.md).
        self.assertIn(
            "patient_id = (\n"
            "            SELECT patient_id FROM encounters WHERE id = app.current_encounter_id()",
            src,
        )
        # Must not reinstate direct encounter match as the patient clause in upgrade.
        upgrade = src.split("def downgrade")[0]
        self.assertNotIn(
            "encounter_id = app.current_encounter_id()",
            upgrade,
        )


if __name__ == "__main__":
    unittest.main()
