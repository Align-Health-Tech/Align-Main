"""Exploratory Azure probe: Devise with an EMPTY candidate_pool.

NOT for CI. Does not change production — empties the pool only for this run
via a temporary patch of ``_get_candidate_pool``.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_devise_empty_pool/smoke_devise_empty_pool.py

Compares:
  A. priority_questions Devise with candidate_pool=[] (forced empty)
  B. Same context with the normal registry pool (control)

Context: wrist fall + Eliquis (same scenario as priority_questions case 4).

Results under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt``.
"""
from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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
from intelligence.llm_client import get_last_tool_loop
from schemas.clinical_ai_io import ClassifierInput
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_PHASE = "priority_questions"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"

_ELIQUIS_TEXT = (
    "Hurt my wrist yesterday after a fall, still swollen and bruised. "
    "I'm on Eliquis (apixaban) for a heart condition."
)


def _state(text: str) -> SessionState:
    return SessionState(
        session_id="smoke-devise-empty-pool",
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


def _run_devise(label: str, context: dict, *, empty_pool: bool) -> list[TopicCandidate]:
    print(f"--- {label} ---")
    print(f"candidate_pool forced empty: {empty_pool}")
    try:
        if empty_pool:
            with patch(
                "intelligence.agents._get_candidate_pool",
                return_value=[],
            ):
                topics = run_devise_and_prioritise(_PHASE, context)
        else:
            topics = run_devise_and_prioritise(_PHASE, context)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR run_devise_and_prioritise: {exc}")
        _print_tool_telemetry(label)
        return []

    loop = _print_tool_telemetry(label)
    print("devise topics:")
    print(_dump(topics))
    _print_ranking_brief(label, topics)
    print(
        f"{label} notes:",
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
    print("=== devise empty-pool exploratory probe ===\n")
    print(
        "Exploratory (not pass/fail). Same wrist+Eliquis context as "
        "priority_questions case 4. Production registry lookup unchanged.\n"
    )

    state = _classify_and_apply(_state(_ELIQUIS_TEXT))
    context = build_agent_context(state)
    print("context.known_collect_values:", context.get("known_collect_values"))
    print("context.presentation_category:", context.get("presentation_category"))
    print("context.chief_complaint:", context.get("chief_complaint"))
    print()

    empty_topics = _run_devise("A_empty_pool", context, empty_pool=True)
    control_topics = _run_devise("B_full_registry_pool", context, empty_pool=False)

    print("--- comparison notes (human) ---")
    print(
        {
            "empty_topic_count": len(empty_topics),
            "control_topic_count": len(control_topics),
            "empty_ids": [t.topic for t in empty_topics],
            "control_ids": [t.topic for t in control_topics],
            "empty_only": sorted(
                set(t.topic for t in empty_topics) - set(t.topic for t in control_topics)
            ),
            "control_only": sorted(
                set(t.topic for t in control_topics) - set(t.topic for t in empty_topics)
            ),
        }
    )
    print(
        "Interpretation cues: without a pool, does Devise invent free-form "
        "topic strings vs registry ids? Does it search more? Do ranks still "
        "elevate medication / injury mechanism for Eliquis + wrist trauma?"
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
