"""ClassifierResult aliases, supplement backfill, known_collect_values."""
from __future__ import annotations

import unittest

from engine.agent_bridge import build_agent_context
from engine.session_state_mappers.ai import map_classifier_result
from intelligence.registry import get_eligible_targets
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
        updates = map_classifier_result(state, result)
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
        updates = map_classifier_result(state, result)
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
        updates = map_classifier_result(state, result)
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
        updates = map_classifier_result(state, result)
        self.assertEqual(updates["chief_complaint"]["text"], summary)
        self.assertEqual(updates["chief_complaint"]["en_text"], summary)
        self.assertEqual(updates["chief_complaint"]["source"], "ai_summary")

    def test_non_localised_categoriser_sets_bucket_not_presentation(self) -> None:
        state = SessionState(
            session_id="s",
            patient_id="p",
            organization_id="o",
            presentation_category="NOT_LOCALISED",
            chief_complaint={
                "text": "Fever and malaise.",
                "source": "ai_summary",
            },
        )
        result = ClassifierResult(
            ready=True,
            category="SYSTEMIC",
            confidence=0.91,
            reason="fever + malaise",
            # If a model wrongly echoed PC fields, still must not apply them here.
            chief_complaint_summary="SHOULD_NOT_APPLY",
        )
        updates = map_classifier_result(
            state, result, prompt_name="non_localised_categoriser"
        )
        self.assertEqual(updates, {"non_localised_category": "SYSTEMIC"})
        self.assertNotIn("presentation_category", updates)
        self.assertNotIn("chief_complaint", updates)

    def test_null_pc_only_fields_strips_nl_echo(self) -> None:
        from intelligence.agents import _null_pc_only_fields

        dirty = ClassifierResult(
            ready=True,
            category="SYSTEMIC",
            confidence=0.9,
            reason="fever",
            chief_complaint_summary="SHOULD_NULL",
            localised_anatomy_sites=[
                LocalisedAnatomySite(
                    body_part="wrist",
                    side="right",
                    surface="unknown",
                    major_region="arm",
                    confidence=0.9,
                    evidence="n/a",
                )
            ],
            encounter_intake_supplement=EncounterIntakeSupplement(
                character=["sharp"]
            ),
        )
        clean = _null_pc_only_fields(dirty)
        self.assertIsNone(clean.chief_complaint_summary)
        self.assertIsNone(clean.localised_anatomy_sites)
        self.assertIsNone(clean.encounter_intake_supplement)
        self.assertEqual(clean.category, "SYSTEMIC")
        self.assertEqual(clean.reason, "fever")


class TestKnownCollectValuesFromSupplement(unittest.TestCase):
    def test_backfill_marks_known_but_keeps_targets_eligible(self) -> None:
        """known_collect_values keys are ranking/prefill signal — not an exclusion filter."""
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
        updates = map_classifier_result(state, result)
        merged = state.model_copy(update=updates)
        ctx = build_agent_context(merged)
        known = set(ctx["known_collect_values"])
        self.assertEqual(
            known,
            {
                "onset_circumstance",
                "character",
                "comorbidities",
                "self_management",
                "weight_change",
                "exacerbating_factors",
                "mitigating_factors",
            },
        )
        self.assertEqual(
            ctx["known_collect_values"]["onset_circumstance"], "fell"
        )
        self.assertEqual(
            ctx["known_collect_values"]["character"], ["sharp"]
        )
        priority_ids = {
            t.id for t in get_eligible_targets("priority", None)
        }
        optional_ids = {
            t.id for t in get_eligible_targets("optional", None)
        }
        # Prefill-and-confirm: known targets stay in the pool.
        self.assertIn("onset_circumstance", priority_ids)
        self.assertIn("character", priority_ids)
        self.assertIn("comorbidities", priority_ids)
        self.assertIn("self_management", optional_ids)
        self.assertIn("weight_change", optional_ids)
        self.assertIn("exacerbating_factors", optional_ids)
        self.assertIn("mitigating_factors", optional_ids)

    def test_pregnancy_only_when_female(self) -> None:
        ids_female = {
            t.id for t in get_eligible_targets("priority", "female")
        }
        ids_male = {
            t.id for t in get_eligible_targets("priority", "male")
        }
        self.assertIn("pregnancy", ids_female)
        self.assertNotIn("pregnancy", ids_male)

    def test_locality_filters_onset_and_optional(self) -> None:
        loc = {t.id for t in get_eligible_targets("priority", "male", "LOCALISED")}
        nl = {
            t.id for t in get_eligible_targets("priority", "male", "NOT_LOCALISED")
        }
        self.assertIn("onset_circumstance", loc)
        self.assertNotIn("onset_circumstance", nl)
        self.assertIn("medication", nl)
        self.assertIn("character", nl)

        opt_loc = {
            t.id for t in get_eligible_targets("optional", None, "LOCALISED")
        }
        opt_nl = {
            t.id for t in get_eligible_targets("optional", None, "NOT_LOCALISED")
        }
        self.assertIn("past_history", opt_loc)
        self.assertNotIn("past_history", opt_nl)
        self.assertIn("family_history", opt_nl)
        self.assertNotIn("family_history", opt_loc)
        self.assertIn("weight_change", opt_nl)
        self.assertNotIn("weight_change", opt_loc)
        self.assertIn("social_history", opt_nl)
        self.assertNotIn("social_history", opt_loc)

    def test_only_pregnancy_keeps_suggestion_fields(self) -> None:
        from intelligence.registry import (
            OPTIONAL_TARGETS,
            PRIORITY_TARGETS,
        )

        for t in PRIORITY_TARGETS + OPTIONAL_TARGETS:
            if t.id == "pregnancy":
                self.assertEqual(
                    t.example_prompt,
                    "Is there any chance you could be pregnant?",
                )
                self.assertEqual(t.suggested_options, ["No", "Yes"])
            else:
                self.assertIsNone(t.example_prompt, t.id)
                self.assertIsNone(t.suggested_options, t.id)


if __name__ == "__main__":
    unittest.main()
