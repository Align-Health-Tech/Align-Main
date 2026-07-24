"""M5 — agent_bridge + ClinicalAiMock wiring (no Azure)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from engine import agent_bridge
from schemas.clinical_ai_io import ClassifierInput, ClassifierResult
from schemas.session_states import SessionState
from tests.mock_clinical_ai import MockClinicalAiTestCase


class TestM5AgentBridgeMocks(MockClinicalAiTestCase, unittest.TestCase):
    def test_classifier_order_script(self) -> None:
        self.ai.set_classifier_script(
            [
                ClassifierResult(ready=False, reason="a"),
                ClassifierResult(ready=True, category="LOCALISED", reason="b"),
            ]
        )
        inp = ClassifierInput(
            prompt_name="presenting_complaint",
            conversation=[],
            context={"chief_complaint": {"text": "x"}},
        )
        self.assertFalse(agent_bridge.run_classifier(inp).ready)
        self.assertTrue(agent_bridge.run_classifier(inp).ready)
        self.assertEqual(self.ai.fake_classifier_call_count, 2)

    def test_devise_qg_branch_by_phase_not_call_order(self) -> None:
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
        )
        # Call redflag before priority — phase fn must not confuse them.
        rf_topics, rf_qs = agent_bridge.devise_then_generate(
            "redflag_screening", state
        )
        pri_topics, pri_qs = agent_bridge.devise_then_generate(
            "priority_questions", state
        )
        self.assertEqual(rf_qs[0].id, "rf_chest_pain")
        self.assertEqual(pri_qs[0].id, "meds_q1")
        self.assertEqual(rf_topics[0].topic, "chest_pain")
        self.assertEqual(pri_topics[0].topic, "medication")
        self.assertEqual(self.ai.fake_redflag_qg_call_count, 1)
        self.assertEqual(self.ai.fake_priority_qg_call_count, 1)

    def test_clarify_phases_pass_validation(self) -> None:
        state = SessionState(
            session_id="s", patient_id="p", organization_id="o"
        )
        _, pc_qs = agent_bridge.devise_then_generate(
            "presenting_complaint_clarify", state
        )
        _, nl_qs = agent_bridge.devise_then_generate(
            "non_localised_clarify", state
        )
        self.assertEqual(pc_qs[0].kind, "single_choice")
        self.assertEqual(nl_qs[0].kind, "single_choice")
        self.assertEqual(
            [o.value for o in (nl_qs[0].options or [])],
            ["Yes", "No", "I don't know"],
        )

    def test_clarify_devise_and_qg_receive_conversation(self) -> None:
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            messages=[
                {"role": "user", "content": "I have a headache"},
                {
                    "role": "user",
                    "content": "Where is it mainly? One side only",
                },
            ],
        )
        captured: dict[str, list[dict]] = {}

        def capture_devise(phase: str, context: dict, **kwargs):
            captured["devise"] = context["conversation"]
            return self.ai.run_devise_and_prioritise(phase, context, **kwargs)

        def capture_qg(input):
            captured["qg"] = input.context["conversation"]
            return self.ai.run_question_generation(input)

        with (
            patch.object(
                agent_bridge,
                "run_devise_and_prioritise",
                side_effect=capture_devise,
            ),
            patch.object(
                agent_bridge,
                "run_question_generation",
                side_effect=capture_qg,
            ),
        ):
            agent_bridge.devise_then_generate("presenting_complaint_clarify", state)

        expected = agent_bridge.conversation_from_state(state)
        self.assertEqual(captured["devise"], expected)
        self.assertEqual(captured["qg"], expected)

    def test_translate_via_bridge(self) -> None:
        out = agent_bridge.translate_to_english("안녕", "ko")
        self.assertEqual(out.en_text, "[en] 안녕")
        self.assertEqual(self.ai.fake_translate_call_count, 1)


if __name__ == "__main__":
    unittest.main()
