"""ClassifierResult aliases, supplement backfill, already_known_ids."""
from __future__ import annotations

import unittest

from engine.helpers.agent_bridge import build_agent_context
from engine.helpers.apply_classifier_result import apply_classifier_result
from external_systems.clinical_ai.registry import get_eligible_targets
from schemas.clinical_ai_io import (
    ClassifierResult,
    EncounterIntakeSupplement,
    LocalisedAnatomySite,
)
from schemas.session_states import SessionState
from tests.mock_clinical_ai import MockClinicalAiTestCase


class TestClassifierResultAliases(unittest.TestCase):
    def test_camel_case_llm_json_round_trip(self) -> None:
        result = ClassifierResult.model_validate(
            {
                "ready": True,
                "category": "LOCALISED",
                "confidence": 0.9,
                "reason": "focal wrist",
                "chiefComplaintSummary": "Sharp pain in the right wrist.",
                "localisedAnatomySites": [
                    {
                        "bodyPart": "wrist",
                        "side": "right",
                        "surface": "front",
                        "majorRegion": "arm",
                        "confidence": 0.95,
                        "evidence": "right wrist",
                    }
                ],
                "encounterIntakeSupplement": {
                    "onsetCircumstance": "twisted it",
                    "character": ["sharp"],
                    "accClaimSuspected": False,
                },
            }
        )
        self.assertEqual(
            result.chief_complaint_summary, "Sharp pain in the right wrist."
        )
        assert result.localised_anatomy_sites is not None
        self.assertEqual(result.localised_anatomy_sites[0].body_part, "wrist")
        assert result.encounter_intake_supplement is not None
        self.assertEqual(
            result.encounter_intake_supplement.onset_circumstance, "twisted it"
        )
        self.assertEqual(result.encounter_intake_supplement.character, ["sharp"])
        self.assertIs(result.encounter_intake_supplement.acc_claim_suspected, False)

    def test_snake_case_construction(self) -> None:
        result = ClassifierResult(
            ready=True,
            category="LOCALISED",
            localised_anatomy_sites=[
                LocalisedAnatomySite(
                    body_part="ankle",
                    side="left",
                    surface="front",
                    major_region="leg",
                    confidence=0.9,
                    evidence="left ankle",
                )
            ],
            encounter_intake_supplement=EncounterIntakeSupplement(
                duration="2 days",
                weight_change="lost 2kg",
            ),
        )
        assert result.localised_anatomy_sites is not None
        self.assertEqual(result.localised_anatomy_sites[0].major_region, "leg")
        assert result.encounter_intake_supplement is not None
        self.assertEqual(result.encounter_intake_supplement.duration, "2 days")


class TestApplyClassifierResult(MockClinicalAiTestCase, unittest.TestCase):
    def test_supplement_backfill_narrative_and_scalars(self) -> None:
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            session_language="ko",
        )
        result = ClassifierResult(
            ready=True,
            category="LOCALISED",
            localised_anatomy_sites=[
                LocalisedAnatomySite(
                    body_part="wrist",
                    side="right",
                    surface="front",
                    major_region="arm",
                    confidence=0.9,
                    evidence="wrist",
                )
            ],
            encounter_intake_supplement=EncounterIntakeSupplement(
                onset_circumstance="넘어짐",
                character=["쑤심"],
                weight_change="none",
                acc_claim_suspected=True,
                acc_can_work=False,
            ),
        )
        updates = apply_classifier_result(state, result)
        self.assertEqual(updates["presentation_category"], "LOCALISED")
        self.assertEqual(
            updates["presenting_complaint_hint"]["localisedAnatomySites"][0][
                "bodyPart"
            ],
            "wrist",
        )
        self.assertEqual(updates["onset_circumstance"]["text"], "넘어짐")
        self.assertEqual(updates["onset_circumstance"]["en_text"], "[en] 넘어짐")
        self.assertEqual(updates["onset_circumstance"]["source"], "free_text")
        self.assertEqual(updates["character"][0]["text"], "쑤심")
        self.assertEqual(updates["character"][0]["en_text"], "[en] 쑤심")
        self.assertEqual(updates["weight_change"], "none")
        self.assertIs(updates["acc_claim_suspected"], True)
        self.assertIs(updates["acc_can_work"], False)
        self.assertNotIn("duration", updates)

    def test_omit_none_supplement_keys(self) -> None:
        state = SessionState(
            session_id="s", patient_id="p", organization_id="o"
        )
        result = ClassifierResult(
            ready=True,
            category="NOT_LOCALISED",
            encounter_intake_supplement=EncounterIntakeSupplement(
                duration="since yesterday"
            ),
        )
        updates = apply_classifier_result(state, result)
        self.assertEqual(updates["duration"]["text"], "since yesterday")
        self.assertNotIn("onset_circumstance", updates)
        self.assertEqual(updates["presenting_complaint_hint"], {})

    def test_overwrite_chief_complaint_with_ai_summary(self) -> None:
        raw = "something hurts"
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            session_language="en",
            chief_complaint={"text": raw, "source": "free_text"},
            messages=[
                {"role": "user", "content": raw},
                {"role": "user", "content": "Arm"},
            ],
        )
        summary = (
            "Patient reports pain mainly in the arm after clarifying "
            "a vague initial complaint."
        )
        result = ClassifierResult(
            ready=True,
            category="LOCALISED",
            confidence=0.9,
            reason="arm named",
            chief_complaint_summary=summary,
            localised_anatomy_sites=[
                LocalisedAnatomySite(
                    body_part="arm",
                    side="unknown",
                    surface="unknown",
                    major_region="arm",
                    confidence=0.85,
                    evidence="Arm",
                )
            ],
        )
        updates = apply_classifier_result(state, result)
        self.assertEqual(updates["chief_complaint"]["text"], summary)
        self.assertEqual(updates["chief_complaint"]["source"], "ai_summary")
        self.assertNotIn("en_text", updates["chief_complaint"])

        merged = state.model_copy(update=updates)
        self.assertEqual(merged.messages[0]["content"], raw)
        self.assertEqual(merged.messages[1]["content"], "Arm")
        self.assertNotEqual(merged.chief_complaint["text"], raw)

    def test_ai_summary_sets_en_text_when_session_not_en(self) -> None:
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            session_language="ko",
            chief_complaint={"text": "아파요", "source": "free_text"},
            messages=[{"role": "user", "content": "아파요"}],
        )
        summary = "Patient reports arm pain."
        result = ClassifierResult(
            ready=True,
            category="LOCALISED",
            chief_complaint_summary=summary,
        )
        updates = apply_classifier_result(state, result)
        self.assertEqual(updates["chief_complaint"]["text"], summary)
        self.assertEqual(updates["chief_complaint"]["en_text"], summary)
        self.assertEqual(updates["chief_complaint"]["source"], "ai_summary")


class TestAlreadyKnownFromSupplement(unittest.TestCase):
    def test_backfill_excludes_registry_targets(self) -> None:
        state = SessionState(
            session_id="s", patient_id="p", organization_id="o"
        )
        result = ClassifierResult(
            ready=True,
            category="LOCALISED",
            encounter_intake_supplement=EncounterIntakeSupplement(
                onset_circumstance="fell",
                character=["sharp"],
                comorbidities=["asthma"],
                self_management="ibuprofen",
                weight_change="stable",
                exacerbating_factors=["walking"],
                mitigating_factors=["rest"],
            ),
        )
        updates = apply_classifier_result(state, result)
        merged = state.model_copy(update=updates)
        ctx = build_agent_context(merged)
        known = set(ctx["already_known_ids"])
        self.assertEqual(
            known,
            {
                "onset_circumstance",
                "symptom_characteristics",
                "comorbidities",
                "self_management",
                "weight_change",
                "exacerbating_factors",
                "mitigating_factors",
            },
        )
        priority_ids = {
            t.id for t in get_eligible_targets("priority", known, None)
        }
        optional_ids = {
            t.id for t in get_eligible_targets("optional", known, None)
        }
        self.assertNotIn("onset_circumstance", priority_ids)
        self.assertNotIn("symptom_characteristics", priority_ids)
        self.assertNotIn("comorbidities", priority_ids)
        self.assertNotIn("self_management", optional_ids)
        self.assertNotIn("weight_change", optional_ids)
        self.assertNotIn("exacerbating_factors", optional_ids)
        self.assertNotIn("mitigating_factors", optional_ids)


if __name__ == "__main__":
    unittest.main()
