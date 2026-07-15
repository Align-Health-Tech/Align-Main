"""Body diagram catalogue + localised_detail SVG round-trip."""
from __future__ import annotations

import unittest

from engine.static.body_diagram_catalogue import (
    resolve_coding,
    resolve_prefill_candidates,
)
from engine.runner import SessionRunner
from schemas.clinical_ai_io import LocalisedAnatomySite
from tests.helpers import (
    answer_body_diagram,
    answer_localised_detail,
    answer_localised_detail_questions,
    answer_pc_free_text,
    snap_values,
)
from tests.mock_clinical_ai import MockClinicalAiTestCase


def _site(
    body_part: str,
    side: str,
    surface: str,
    confidence: float,
    *,
    major_region: str = "unknown",
    evidence: str = "test",
) -> LocalisedAnatomySite:
    return LocalisedAnatomySite(
        body_part=body_part,
        side=side,
        surface=surface,
        major_region=major_region,
        confidence=confidence,
        evidence=evidence,
    )


class TestResolvePrefillCandidates(unittest.TestCase):
    def test_converges_on_highest_confidence_diagram_and_unions_regions(
        self,
    ) -> None:
        # Wrist (0.95) wins Front sheet; hand unions in; tricep (Back) dropped.
        sites = [
            _site("hand", "right", "front", 0.5, major_region="arm"),
            _site("wrist", "right", "front", 0.95, major_region="arm"),
            _site("tricep", "right", "back", 0.4, major_region="arm"),
        ]
        prefill = resolve_prefill_candidates(sites, patient_sex=None)
        assert prefill is not None
        self.assertEqual(prefill.diagram_file, "Arm Right Front.svg")
        self.assertEqual(
            prefill.highlighted_region_ids,
            ["Select_RightWrist", "Select_RightHand"],
        )

    def test_sex_split_ankle(self) -> None:
        sites = [_site("ankle", "right", "front", 0.9, major_region="leg")]
        male = resolve_prefill_candidates(sites, patient_sex="male")
        female = resolve_prefill_candidates(sites, patient_sex="female")
        assert male is not None and female is not None
        self.assertEqual(male.diagram_file, "Male Legs Front 1.svg")
        self.assertEqual(
            male.highlighted_region_ids, ["Select_MaleLegs_Front_RightAnkle"]
        )
        self.assertEqual(female.diagram_file, "Female Legs Front 1.svg")
        self.assertEqual(
            female.highlighted_region_ids, ["Select_FemaleLegs_Front_RightAnkle"]
        )

    def test_new_vocab_body_parts_resolve(self) -> None:
        """chin / forehead / cheek / upper_abdomen prefill rows."""
        cases: list[tuple[LocalisedAnatomySite, str | None, str]] = [
            (_site("chin", "midline", "front", 0.9, major_region="face"), None, "Select_Chin"),
            (
                _site("forehead", "midline", "front", 0.9, major_region="face"),
                None,
                "Select_Forehead",
            ),
            (
                _site("cheek", "left", "front", 0.9, major_region="face"),
                None,
                "Select_LeftSide",
            ),
            (
                _site("upper_abdomen", "right", "front", 0.9, major_region="torso"),
                "male",
                "Select_Right_UpperQuadrant",
            ),
        ]
        for site, sex, region_id in cases:
            prefill = resolve_prefill_candidates([site], patient_sex=sex)
            assert prefill is not None
            self.assertIn(region_id, prefill.highlighted_region_ids)

    def test_unknown_surface_falls_back_to_first_catalogue_hit(self) -> None:
        """surface=unknown → ignore surface; first PREFILL_MAPPINGS match wins."""
        # Right wrist: back entry appears before front in arms.PREFILL_MAPPINGS.
        wrist = resolve_prefill_candidates(
            [_site("wrist", "right", "unknown", 0.95, major_region="arm")],
            patient_sex=None,
        )
        assert wrist is not None
        self.assertEqual(wrist.diagram_file, "Arm Right Back.svg")
        self.assertEqual(wrist.highlighted_region_ids, ["Select_RightWrist"])

        # Tricep is back-only — unknown must still hit that entry, not invent front.
        tricep = resolve_prefill_candidates(
            [_site("tricep", "right", "unknown", 0.9, major_region="arm")],
            patient_sex=None,
        )
        assert tricep is not None
        self.assertEqual(tricep.diagram_file, "Arm Right Back.svg")
        self.assertEqual(tricep.highlighted_region_ids, ["Select_RightTricep"])

    def test_known_wrong_surface_does_not_fallback(self) -> None:
        """Exact surface miss with a concrete surface stays None (no inventing)."""
        prefill = resolve_prefill_candidates(
            [_site("tricep", "right", "front", 0.9, major_region="arm")],
            patient_sex=None,
        )
        self.assertIsNone(prefill)


class TestLocalisedDetailBodyDiagram(MockClinicalAiTestCase, unittest.TestCase):
    def test_round_trip_no_laterality_mcq_and_coding_matches(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        step = answer_pc_free_text(runner, session_id, "pain in my right wrist")
        self.assertEqual(step.phase, "localised_detail")
        self.assertEqual(step.step_type, "body_diagram")
        self.assertEqual(step.diagram_file, "Arm Right Front.svg")
        self.assertEqual(step.highlighted_region_ids, ["Select_RightWrist"])
        self.assertIsNone(step.questions)

        after_tap = answer_body_diagram(
            runner, session_id, region_id="Select_RightWrist"
        )
        self.assertEqual(after_tap.phase, "localised_detail")
        self.assertEqual(after_tap.step_type, "question_batch")
        ids = [q.id for q in (after_tap.questions or [])]
        self.assertEqual(ids, ["loc_severity", "loc_onset"])
        self.assertNotIn("loc_laterality", ids)
        self.assertNotIn("loc_region", ids)

        expected = resolve_coding("Select_RightWrist")
        assert expected is not None
        values = snap_values(runner, session_id)
        body = values["body_structures"][0]
        self.assertEqual(body["region_detail"], expected.model_dump())
        self.assertEqual(body["laterality"], "right")

        next_step = answer_localised_detail_questions(runner, session_id)
        self.assertEqual(next_step.phase, "priority_questions")

        values = snap_values(runner, session_id)
        self.assertIn("localised_detail", values["completed_phases"])
        self.assertEqual(values["severity_score"], 7)
        self.assertEqual(values["onset_circumstance"]["text"], "Within 48 hours")
        self.assertEqual(values["onset_circumstance"]["source"], "option")
        self.assertEqual(
            values["body_structures"][0]["region_detail"], expected.model_dump()
        )
        self.assertEqual(values["body_structures"][0]["severity_score"], 7)

    def test_interrupt_matches_current_rebuild_mid_await(self) -> None:
        """Pause-time body_diagram NextStep must match GET rebuild via current()."""
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        interrupted = answer_pc_free_text(
            runner, session_id, "pain in my right wrist"
        )
        self.assertEqual(interrupted.step_type, "body_diagram")

        rebuilt = runner.current(session_id)
        assert rebuilt is not None
        self.assertEqual(rebuilt.step_type, "body_diagram")
        self.assertEqual(rebuilt.phase, interrupted.phase)
        self.assertEqual(rebuilt.diagram_file, interrupted.diagram_file)
        self.assertEqual(
            rebuilt.highlighted_region_ids, interrupted.highlighted_region_ids
        )
        self.assertEqual(rebuilt.turn_number, interrupted.turn_number)

    def test_helper_walk_still_reaches_priority(self) -> None:
        runner = SessionRunner(segment_type="URGENT_CARE")
        session_id, _ = runner.start()
        answer_pc_free_text(runner, session_id, "pain in my right wrist")
        next_step = answer_localised_detail(runner, session_id)
        self.assertEqual(next_step.phase, "priority_questions")


if __name__ == "__main__":
    unittest.main()
