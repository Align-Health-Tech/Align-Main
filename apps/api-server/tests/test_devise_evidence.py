"""Devise evidence tool use, attribution validation, and fallback."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from intelligence import agents
from schemas.clinical_ai_io import (
    QuestionGenerationInput,
    QuestionGenerationResult,
)
from schemas.topic_candidates import TopicCandidate

URL_1 = "https://healthify.nz/health-a-z/b/broken-wrist"
URL_2 = (
    "https://www.healthnz.govt.nz/health-topics/conditions-treatments/"
    "bones-and-joints/care-of-your-wrist-and-hand-after-a-fracture"
)
URL_3 = "https://healthify.nz/health-a-z/h/hand-and-wrist-conditions"


def _trace(successful_urls: list[str], failed_urls: list[str] | None = None) -> str:
    return json.dumps(
        {
            "query": "concise query",
            "successful_sources": [
                {
                    "title": "Source",
                    "url": url,
                    "bm25_score": 1.0,
                    "latency_ms": 1,
                    "content": "content",
                }
                for url in successful_urls
            ],
            "failed_sources": [
                {
                    "title": "Failed",
                    "url": url,
                    "bm25_score": 0.5,
                    "latency_ms": 8_000,
                    "error_code": "timeout",
                }
                for url in (failed_urls or [])
            ],
            "batch_latency_ms": 2,
        }
    )


class _Raw:
    def __init__(self, candidates: list[object]) -> None:
        self.candidates = candidates


def _candidate(
    topic: str,
    *,
    source: str = "web_search",
    evidence_urls: list[str] | None = None,
    score: float = 0.8,
) -> object:
    return type(
        "Candidate",
        (),
        {
            "topic": topic,
            "relevance_score": score,
            "source": source,
            "rationale": "brief rationale",
            "evidence_urls": evidence_urls or [],
        },
    )()


class TestDeviseEvidence(unittest.TestCase):
    def test_priority_and_redflag_force_one_tool_call(self) -> None:
        def run_with_tools(*args, **kwargs):
            kwargs["tool_trace"].append(
                {
                    "name": "web_search",
                    "args": {"query": "concise query"},
                    "result": _trace([]),
                }
            )
            return _Raw([])

        with (
            patch.object(
                agents, "run_agent_with_tools", side_effect=run_with_tools
            ) as run,
            patch.object(agents, "run_agent") as reasoning,
        ):
            agents.run_devise_and_prioritise("priority_questions", {})
            agents.run_devise_and_prioritise("redflag_screening", {})

        self.assertEqual(run.call_count, 2)
        reasoning.assert_not_called()
        for call in run.call_args_list:
            self.assertEqual(call.kwargs["tool_choice"], "required")
            self.assertEqual(len(call.kwargs["tools"]), 1)
            self.assertTrue(call.kwargs["tool_default_args"]["web_search"]["query"])

    def test_optional_and_clarification_are_reasoning_only(self) -> None:
        with (
            patch.object(agents, "run_agent", return_value=_Raw([])) as reasoning,
            patch.object(agents, "run_agent_with_tools") as with_tools,
        ):
            agents.run_devise_and_prioritise("optional_questions", {})
            agents.run_devise_and_prioritise(
                "presenting_complaint_clarify",
                {},
            )
            agents.run_devise_and_prioritise("non_localised_clarify", {})

        self.assertEqual(reasoning.call_count, 3)
        with_tools.assert_not_called()

    def test_urls_are_deduplicated_filtered_and_restored_to_bm25_order(self) -> None:
        raw = _Raw(
            [
                _candidate(
                    "medication",
                    evidence_urls=[URL_1, URL_2, URL_1, "https://invented.test"],
                )
            ]
        )

        def run_with_tools(*args, **kwargs):
            kwargs["tool_trace"].append(
                {
                    "name": "web_search",
                    "args": {"query": "query"},
                    "result": _trace([URL_2, URL_1, URL_3]),
                }
            )
            return raw

        with patch.object(
            agents,
            "run_agent_with_tools",
            side_effect=run_with_tools,
        ):
            output = agents.run_devise_and_prioritise(
                "priority_questions",
                {},
            )

        self.assertEqual(output[0].evidence_urls, [URL_2, URL_1])
        self.assertEqual(output[0].source, "web_search")

    def test_partial_success_and_complete_failure_attribution(self) -> None:
        raw = _Raw(
            [
                _candidate("BREATHING", evidence_urls=[URL_1]),
                _candidate("CIRCULATION", evidence_urls=[URL_2]),
            ]
        )

        def partial(*args, **kwargs):
            kwargs["tool_trace"].append(
                {
                    "name": "web_search",
                    "args": {"query": "query"},
                    "result": _trace([URL_1], [URL_2]),
                }
            )
            return raw

        with patch.object(agents, "run_agent_with_tools", side_effect=partial):
            output = agents.run_devise_and_prioritise(
                "redflag_screening",
                {},
            )
        self.assertEqual(output[0].source, "web_search")
        self.assertEqual(output[0].evidence_urls, [URL_1])
        self.assertEqual(output[1].source, "base_reasoning")
        self.assertEqual(output[1].evidence_urls, [])

        def failed(*args, **kwargs):
            kwargs["tool_trace"].append(
                {
                    "name": "web_search",
                    "args": {"query": "query"},
                    "result": _trace([], [URL_1, URL_2]),
                }
            )
            return raw

        with patch.object(agents, "run_agent_with_tools", side_effect=failed):
            output = agents.run_devise_and_prioritise(
                "redflag_screening",
                {},
            )
        self.assertTrue(all(item.source == "base_reasoning" for item in output))
        self.assertTrue(all(item.evidence_urls == [] for item in output))

    def test_redflag_normalization_and_score_are_preserved(self) -> None:
        raw = _Raw(
            [
                _candidate(
                    "breathing",
                    source="base_reasoning",
                    evidence_urls=[],
                    score=0.65,
                )
            ]
        )

        def failed(*args, **kwargs):
            kwargs["tool_trace"].append(
                {
                    "name": "web_search",
                    "args": {"query": "query"},
                    "result": _trace([]),
                }
            )
            return raw

        with patch.object(agents, "run_agent_with_tools", side_effect=failed):
            output = agents.run_devise_and_prioritise(
                "redflag_screening",
                {},
            )
        self.assertEqual(output[0].topic, "BREATHING")
        self.assertEqual(output[0].relevance_score, 0.65)

    def test_pool_and_redflag_confidence_limits_are_enforced(self) -> None:
        optional_raw = _Raw(
            [
                _candidate("past_history"),
                _candidate("invented_target"),
            ]
        )
        with patch.object(agents, "run_agent", return_value=optional_raw):
            optional = agents.run_devise_and_prioritise(
                "optional_questions",
                {"presentation_category": "LOCALISED"},
            )
        self.assertEqual([item.topic for item in optional], ["past_history"])

        redflag_raw = _Raw(
            [
                _candidate("AIRWAY", score=0.9),
                _candidate("BREATHING", score=0.8),
                _candidate("CIRCULATION", score=0.7),
                _candidate("DISABILITY", score=0.69),
                _candidate("TEMPERATURE", score=0.64),
            ]
        )

        def failed(*args, **kwargs):
            kwargs["tool_trace"].append(
                {
                    "name": "web_search",
                    "args": {"query": "query"},
                    "result": _trace([]),
                }
            )
            return redflag_raw

        with patch.object(agents, "run_agent_with_tools", side_effect=failed):
            redflags = agents.run_devise_and_prioritise(
                "redflag_screening",
                {},
            )
        self.assertEqual(
            [item.topic for item in redflags],
            ["AIRWAY", "BREATHING", "CIRCULATION"],
        )

    def test_qg_receives_evidence_urls_but_no_page_content(self) -> None:
        topic = TopicCandidate(
            topic="medication",
            relevance_score=0.8,
            is_red_flag=False,
            source="web_search",
            rationale="brief",
            evidence_urls=[URL_1],
        )
        captured: dict = {}

        def run_agent(*args):
            captured.update(args[2])
            return QuestionGenerationResult(reason="ok", questions=[])

        with patch.object(agents, "run_agent", side_effect=run_agent):
            agents.run_question_generation(
                QuestionGenerationInput(
                    prompt_name="priority_questions",
                    prioritised_topics=[topic],
                )
            )

        serialized = captured["prioritised_topics"][0]
        self.assertEqual(serialized["evidence_urls"], [URL_1])
        self.assertNotIn("content", serialized)


if __name__ == "__main__":
    unittest.main()
