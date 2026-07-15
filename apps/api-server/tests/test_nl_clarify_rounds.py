"""NL clarify round counter + code-level force-commit hard stop."""
from __future__ import annotations

import unittest

from engine.helpers.agent_bridge import build_agent_context
from engine.runner import SessionRunner
from schemas.clinical_ai_io import ClassifierResult
from schemas.session_states import SessionState
from tests.helpers import answer_pc_free_text, snap_values
from tests.mock_clinical_ai import MockClinicalAiTestCase


def _always_false_lean(category: str = "GASTROINTESTINAL") -> ClassifierResult:
    return ClassifierResult(
        ready=False,
        category=category,
        confidence=0.55,
        reason=f"Ambiguous; lean {category}",
    )


class TestNlClarifyRounds(MockClinicalAiTestCase, unittest.TestCase):
    def test_round_increments_once_per_clarify_batch_not_interrupt_reentry(
        self,
    ) -> None:
        self.ai.set_nl_classifier_script(
            [
                _always_false_lean("SYSTEMIC"),
                ClassifierResult(
                    ready=True, category="SYSTEMIC", confidence=0.9
                ),
            ]
        )
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        step = answer_pc_free_text(
            runner, session_id, "I have a fever and feel unwell"
        )
        self.assertEqual(step.questions[0].id, "nl_clarify_1")
        values = snap_values(runner, session_id)
        # Enqueue pass increments once; Option-2 interrupt re-entry must not.
        self.assertEqual(values["non_localised_clarify_rounds"], 1)
        self.assertEqual(values["non_localised_category_lean"], "SYSTEMIC")
        self.assertEqual(self.ai.fake_nl_classifier_call_count, 1)

        ctx = build_agent_context(
            SessionState(
                session_id="s",
                patient_id="p",
                organization_id="o",
                non_localised_clarify_rounds=1,
                non_localised_category_lean="SYSTEMIC",
            )
        )
        self.assertEqual(ctx["non_localised_clarify_rounds"], 1)
        self.assertEqual(ctx["non_localised_category_lean"], "SYSTEMIC")

    def test_force_commit_after_three_rounds_without_fourth_classifier_call(
        self,
    ) -> None:
        # ready:false forever — engine must hard-stop after 3 enqueues.
        self.ai.set_nl_classifier_script(
            [
                _always_false_lean("GASTROINTESTINAL"),
                _always_false_lean("GASTROINTESTINAL"),
                _always_false_lean("NEUROLOGICAL"),  # lean updates each round
            ]
        )
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        step = answer_pc_free_text(
            runner, session_id, "I have a fever and feel unwell"
        )
        self.assertEqual(step.questions[0].id, "nl_clarify_1")

        for expected_rounds in (1, 2, 3):
            values = snap_values(runner, session_id)
            self.assertEqual(
                values["non_localised_clarify_rounds"], expected_rounds
            )
            qid = values["pending_questions"][0]["id"]
            step = runner.resume(
                session_id,
                {"answers": [{"question_id": qid, "value": "Yes"}]},
            )
            if expected_rounds < 3:
                self.assertTrue(
                    (step.questions or [])
                    and step.questions[0].id.startswith("nl_clarify_")
                )

        # After answering the 3rd clarify batch: force-commit, no 4th call.
        self.assertEqual(self.ai.fake_nl_classifier_call_count, 3)
        values = snap_values(runner, session_id)
        self.assertEqual(values["non_localised_clarify_rounds"], 3)
        # Last lean stored was NEUROLOGICAL (3rd ready:false).
        self.assertEqual(values["non_localised_category"], "NEUROLOGICAL")
        self.assertEqual(
            [q.id for q in (step.questions or [])],
            ["nl_onset", "nl_severity", "nl_functional"],
        )

    def test_force_commit_defaults_to_systemic_when_no_lean(self) -> None:
        self.ai.set_nl_classifier_script(
            [
                ClassifierResult(ready=False, reason="unclear", confidence=0.4),
                ClassifierResult(ready=False, reason="still unclear"),
                ClassifierResult(ready=False, reason="still unclear"),
            ]
        )
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        answer_pc_free_text(
            runner, session_id, "I have a fever and feel unwell"
        )
        for _ in range(3):
            values = snap_values(runner, session_id)
            qid = values["pending_questions"][0]["id"]
            runner.resume(
                session_id,
                {"answers": [{"question_id": qid, "value": "No"}]},
            )
        values = snap_values(runner, session_id)
        self.assertEqual(self.ai.fake_nl_classifier_call_count, 3)
        self.assertEqual(values["non_localised_category"], "SYSTEMIC")

    def test_early_ready_unaffected_by_round_counter(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        step = answer_pc_free_text(
            runner, session_id, "I have a fever and feel unwell"
        )
        self.assertEqual(
            [q.id for q in (step.questions or [])],
            ["nl_onset", "nl_severity", "nl_functional"],
        )
        values = snap_values(runner, session_id)
        self.assertEqual(values["non_localised_clarify_rounds"], 0)
        self.assertEqual(values["non_localised_category"], "SYSTEMIC")
        self.assertEqual(self.ai.fake_nl_classifier_call_count, 1)


if __name__ == "__main__":
    unittest.main()
