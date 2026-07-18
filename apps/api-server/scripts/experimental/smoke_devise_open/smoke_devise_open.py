"""Exploratory Azure probe: OPEN Devise (no registry candidate_pool).

NOT for CI. Does not change production wiring — loads exploratory prompt from
``scripts/experimental/prompts/priority_questions_open.md``.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_devise_open/smoke_devise_open.py

Compares:
  A. Open Devise — context only, empty pool, open prompt
  B. Registry Devise — normal ``priority_questions`` + full pool (control)

Context: wrist fall + Eliquis (same as priority_questions case 4).

Results under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt``.
"""
from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _smoke_results import next_result_path
from engine.agent_bridge import (
    build_agent_context,
    conversation_from_state,
    run_classifier,
    run_devise_and_prioritise,
)
from engine.session_state_mappers.ai import map_classifier_result
from intelligence.llm_client import (
    chat_with_tools_then_structured,
    get_last_tool_loop,
)
from intelligence.tools import web_search
from schemas.clinical_ai_io import ClassifierInput
from schemas.literals import TopicSource
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_RESULTS_DIR = Path(__file__).resolve().parent / "results"
_OPEN_PROMPT = (
    Path(__file__).resolve().parents[1] / "prompts" / "priority_questions_open.md"
)

_ELIQUIS_TEXT = (
    "Hurt my wrist yesterday after a fall, still swollen and bruised. "
    "I'm on Eliquis (apixaban) for a heart condition."
)


class _DeviseCandidate(BaseModel):
    topic: str
    relevance_score: float = Field(ge=0, le=1)
    source: TopicSource = "base_reasoning"
    rationale: Optional[str] = None


class _DeviseTopicsResult(BaseModel):
    candidates: list[_DeviseCandidate]


def _state(text: str) -> SessionState:
    return SessionState(
        session_id="smoke-devise-open",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="male",
        chief_complaint={"text": text, "source": "free_text"},
        messages=[{"role": "user", "content": text}],
    )


def _dump(obj: object) -> str:
    if hasattr(obj, "model_dump"):
        return json.dumps(
            obj.model_dump(mode="json", by_alias=True),
            indent=2,
            ensure_ascii=False,
        )
    if isinstance(obj, list):
        return json.dumps(
            [
                x.model_dump(mode="json", by_alias=True)
                if hasattr(x, "model_dump")
                else x
                for x in obj
            ],
            indent=2,
            ensure_ascii=False,
        )
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _classify_and_apply(state: SessionState) -> SessionState:
    clf = run_classifier(
        ClassifierInput(
            prompt_name="presenting_complaint",
            conversation=conversation_from_state(state),
            context=build_agent_context(state),
        )
    )
    print("classifier:")
    print(_dump(clf))
    if not clf.ready:
        print("WARN: classifier ready=false — applying partial / skipping supplement")
    updates = map_classifier_result(state, clf)
    print("apply keys:", sorted(updates.keys()))
    return state.model_copy(update=updates)


def _print_tool_telemetry(label: str) -> dict:
    loop = get_last_tool_loop()
    calls = loop.get("tool_calls") or []
    print(
        f"{label} tool_loop:",
        {
            "tool_choice": loop.get("tool_choice"),
            "tool_call_count": len(calls),
            "tool_calls": calls,
        },
    )
    return loop


def _print_ranking_brief(label: str, topics: list[TopicCandidate]) -> None:
    print(
        f"{label} ranking brief:",
        [
            {
                "topic": t.topic,
                "score": t.relevance_score,
                "source": t.source,
                "rationale": t.rationale,
            }
            for t in topics
        ],
    )


def _to_topics(raw: _DeviseTopicsResult) -> list[TopicCandidate]:
    return [
        TopicCandidate(
            topic=c.topic,
            relevance_score=c.relevance_score,
            is_red_flag=False,
            source=c.source,
            rationale=c.rationale,
        )
        for c in raw.candidates
    ]


def _run_open(context: dict) -> list[TopicCandidate]:
    """Open Devise: no registry pool; exploratory prompt only."""
    print("--- A_open_devise (no candidate_pool) ---")
    try:
        if not _OPEN_PROMPT.is_file():
            raise FileNotFoundError(f"missing exploratory prompt: {_OPEN_PROMPT}")
        system = _OPEN_PROMPT.read_text(encoding="utf-8")
        import json as _json

        raw = chat_with_tools_then_structured(
            _DeviseTopicsResult,
            system,
            _json.dumps({"context": context}, default=str),
            tools=[web_search],
        )
        topics = _to_topics(raw)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR open devise: {exc}")
        _print_tool_telemetry("A_open")
        return []

    loop = _print_tool_telemetry("A_open")
    print("devise topics:")
    print(_dump(topics))
    _print_ranking_brief("A_open", topics)
    print(
        "A_open notes:",
        {
            "topic_count": len(topics),
            "searched": bool(loop.get("tool_calls")),
            "self_reported_web_search": any(t.source == "web_search" for t in topics),
            "topic_ids": [t.topic for t in topics],
            "non_registry_looking_ids": [
                t.topic
                for t in topics
                if t.topic
                not in {
                    "medication",
                    "character",
                    "onset_circumstance",
                    "allergy",
                    "comorbidities",
                    "pregnancy",
                }
            ],
        },
    )
    print()
    return topics


def _run_registry(context: dict) -> list[TopicCandidate]:
    print("--- B_registry_devise (control) ---")
    try:
        topics = run_devise_and_prioritise("priority_questions", context)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR registry devise: {exc}")
        _print_tool_telemetry("B_registry")
        return []

    loop = _print_tool_telemetry("B_registry")
    print("devise topics:")
    print(_dump(topics))
    _print_ranking_brief("B_registry", topics)
    print(
        "B_registry notes:",
        {
            "topic_count": len(topics),
            "searched": bool(loop.get("tool_calls")),
            "self_reported_web_search": any(t.source == "web_search" for t in topics),
            "topic_ids": [t.topic for t in topics],
        },
    )
    print()
    return topics


def _run() -> int:
    print("=== open Devise exploratory probe ===\n")
    print(
        "Exploratory (not pass/fail). Open prompt has no registry pool. "
        "Production engine still uses registry priority_questions only.\n"
    )

    state = _classify_and_apply(_state(_ELIQUIS_TEXT))
    context = build_agent_context(state)
    print("context.known_collect_values:", context.get("known_collect_values"))
    print("context.presentation_category:", context.get("presentation_category"))
    print("context.chief_complaint:", context.get("chief_complaint"))
    print()

    open_topics = _run_open(context)
    registry_topics = _run_registry(context)

    open_ids = [t.topic for t in open_topics]
    reg_ids = [t.topic for t in registry_topics]
    print("--- comparison notes (human) ---")
    print(
        {
            "open_topic_count": len(open_topics),
            "registry_topic_count": len(registry_topics),
            "open_ids": open_ids,
            "registry_ids": reg_ids,
            "shared_ids": sorted(set(open_ids) & set(reg_ids)),
            "open_only": sorted(set(open_ids) - set(reg_ids)),
            "registry_only": sorted(set(reg_ids) - set(open_ids)),
            "open_top": open_ids[:3],
            "registry_top": reg_ids[:3],
        }
    )
    print(
        "Interpretation: does open Devise propose sensible gaps without a "
        "pool? Does it search more? Does it invent non-registry topic keys "
        "that would need a mapper before QG/apply?"
    )
    print("\ndone; exploratory (exit 0)")
    return 0


def main() -> int:
    buf = StringIO()
    with redirect_stdout(buf):
        code = _run()
    text = buf.getvalue()
    out_path = next_result_path(_RESULTS_DIR)
    out_path.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    sys.stdout.write(f"\n[wrote results → {out_path}]\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
