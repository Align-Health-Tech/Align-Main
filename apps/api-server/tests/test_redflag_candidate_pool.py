"""Candidate pool + topic clamp for redflag_screening."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from intelligence import agents
from intelligence.agents import _get_candidate_pool
from intelligence.registry import (
    REDFLAG_SUBCATEGORIES,
    REDFLAG_TARGETS,
    normalize_redflag_subcategory,
)


class TestRedflagCandidatePool(unittest.TestCase):
    def test_full_pool_with_hints_regardless_of_presentation(self) -> None:
        expected = [
            {"subcategory": t.subcategory, "clinical_hint": t.clinical_hint}
            for t in REDFLAG_TARGETS
        ]
        for pc in ("LOCALISED", "NOT_LOCALISED", None):
            with self.subTest(presentation_category=pc):
                pool = _get_candidate_pool(
                    "redflag_screening",
                    {"presentation_category": pc, "patient_sex": "female"},
                )
                self.assertEqual(pool, expected)
                self.assertEqual(len(pool), 6)
                self.assertTrue(all(row.get("clinical_hint") for row in pool))


class TestNormalizeRedflagSubcategory(unittest.TestCase):
    def test_exact_and_casefold(self) -> None:
        self.assertEqual(normalize_redflag_subcategory("BREATHING"), "BREATHING")
        self.assertEqual(normalize_redflag_subcategory(" breathing "), "BREATHING")
        self.assertEqual(normalize_redflag_subcategory("Circulation"), "CIRCULATION")

    def test_unknown_falls_back_to_other(self) -> None:
        self.assertEqual(normalize_redflag_subcategory("chest_pain"), "OTHER")
        self.assertEqual(normalize_redflag_subcategory("NEURO"), "OTHER")
        self.assertEqual(normalize_redflag_subcategory(""), "OTHER")

    def test_closed_set_matches_targets(self) -> None:
        self.assertEqual(
            list(REDFLAG_SUBCATEGORIES),
            [t.subcategory for t in REDFLAG_TARGETS],
        )


class TestDeviseClampsRedflagTopics(unittest.TestCase):
    def test_hallucinated_topic_becomes_other(self) -> None:
        class _Raw:
            candidates = [
                type(
                    "C",
                    (),
                    {
                        "topic": "chest_pain",
                        "relevance_score": 0.9,
                        "source": "base_reasoning",
                        "rationale": "hallucinated",
                    },
                )(),
                type(
                    "C",
                    (),
                    {
                        "topic": "breathing",
                        "relevance_score": 0.8,
                        "source": "base_reasoning",
                        "rationale": "ok",
                    },
                )(),
            ]

        with patch.object(
            agents, "run_agent_with_tools", return_value=_Raw()
        ):
            out = agents.run_devise_and_prioritise(
                "redflag_screening", {"presentation_category": "LOCALISED"}
            )
        self.assertEqual(
            [(t.topic, t.is_red_flag) for t in out],
            [("OTHER", True), ("BREATHING", True)],
        )


if __name__ == "__main__":
    unittest.main()
