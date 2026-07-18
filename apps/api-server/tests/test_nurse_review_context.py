"""Nurse-review context projection + ReviewSummaryResult alias."""
from __future__ import annotations

import unittest

from engine.agent_bridge import build_agent_context
from schemas.clinical_ai_io import ReviewSummaryResult
from schemas.session_states import SessionState


class TestReviewSummaryResultAlias(unittest.TestCase):
    def test_one_line_summary_alias_round_trip(self) -> None:
        parsed = ReviewSummaryResult.model_validate(
            {"oneLineSummary": "R) wrist pain, no red flags"}
        )
        self.assertEqual(parsed.summary, "R) wrist pain, no red flags")
        dumped = parsed.model_dump(by_alias=True)
        self.assertEqual(dumped["oneLineSummary"], "R) wrist pain, no red flags")
        self.assertNotIn("summary", dumped)


class TestNurseReviewAgentContext(unittest.TestCase):
    def test_context_includes_full_clinical_picture(self) -> None:
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            patient_sex="male",
            chief_complaint={
                "text": "Twisted wrist playing tennis yesterday",
                "source": "free_text",
            },
            presentation_category="LOCALISED",
            severity_score=5,
            functional_impact_score=4,
            body_structures=[
                {
                    "structure_type": "PRIMARY",
                    "coding": {
                        "system": "http://snomed.info/sct",
                        "code": "8205005",
                        "display": "Wrist",
                    },
                    "laterality": "RIGHT",
                }
            ],
            onset_circumstance={
                "text": "Twisted playing tennis yesterday",
                "source": "free_text",
            },
            character=[{"text": "Sharp", "source": "option"}],
            encounter_medication=[
                {"text": "ibuprofen", "source": "free_text"}
            ],
            intake_facts=[
                {
                    "kind": "ALLERGY",
                    "display_name": "penicillin",
                    "source": "patient",
                }
            ],
            raised_flag_topics=["Chest pain at rest"],
            ice_idea={"text": "sprain", "source": "free_text"},
            ice_concern={"text": "fracture", "source": "free_text"},
            ice_expectation={"text": "x-ray", "source": "free_text"},
            completed_phases=["ice"],
        )
        ctx = build_agent_context(state)
        self.assertEqual(ctx["body_structures"], state.body_structures)
        self.assertEqual(ctx["onset_circumstance"], state.onset_circumstance)
        self.assertEqual(ctx["character"], state.character)
        self.assertEqual(ctx["encounter_medication"], state.encounter_medication)
        self.assertEqual(ctx["intake_facts"], state.intake_facts)
        self.assertEqual(ctx["raised_flag_topics"], ["Chest pain at rest"])
        self.assertEqual(ctx["ice_idea"]["text"], "sprain")
        self.assertEqual(ctx["ice_concern"]["text"], "fracture")
        self.assertEqual(ctx["ice_expectation"]["text"], "x-ray")
        self.assertEqual(ctx["severity_score"], 5)
        self.assertEqual(ctx["functional_impact_score"], 4)

    def test_not_localised_body_structures_empty_list(self) -> None:
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            presentation_category="NOT_LOCALISED",
            non_localised_category="SYSTEMIC",
            chief_complaint={"text": "Fever and fatigue", "source": "free_text"},
            body_structures=[],
        )
        ctx = build_agent_context(state)
        self.assertEqual(ctx["body_structures"], [])
        self.assertIsNone(ctx["onset_circumstance"])
        self.assertEqual(ctx["intake_facts"], [])


if __name__ == "__main__":
    unittest.main()
