"""Local Azure smoke for redflag_screening (Devise + QG). NOT for CI.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_redflag_screening/smoke_redflag_screening.py

Cases:
  1. Ordinary localised wrist injury — full subcategory pool; yes_no QG;
     is_red_flag stamped true on any candidates.
  2. Wrist + chest tightness mentioned in priority answers — expect
     BREATHING/CIRCULATION bias; report whether Devise actually searched.
  3. Genuinely unremarkable minor bruise — prefer empty / no over-trigger.
  4. Sore throat / allergic-immune (CLI walkthrough) — expect AIRWAY
     Pilot-style observables as multiple yes_no (not one bundled OR;
     typically 2–3 per topic, no Mild/Moderate/Severe).

Results under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt``.
"""

from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _smoke_results import next_result_path
from engine.agent_bridge import (
    build_agent_context,
    devise_then_generate,
)
from intelligence.agents import _get_candidate_pool
from intelligence.llm_client import _get_last_tool_trace
from intelligence.registry import REDFLAG_TARGETS
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_PHASE = "redflag_screening"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"
_POOL_SUBS = {t.subcategory for t in REDFLAG_TARGETS}
_EXPECTED_POOL = [
    {"subcategory": t.subcategory, "clinical_hint": t.clinical_hint}
    for t in REDFLAG_TARGETS
]


def _state(
    *,
    text: str,
    presentation_category: str = "LOCALISED",
    character: list[dict] | None = None,
    onset: str | None = None,
    severity: int | None = 3,
    functional: int | None = 2,
) -> SessionState:
    updates: dict = {
        "session_id": "smoke-redflag",
        "patient_id": "p",
        "organization_id": "o",
        "session_language": "en",
        "patient_sex": "male",
        "chief_complaint": {"text": text, "source": "free_text"},
        "presentation_category": presentation_category,
        "messages": [{"role": "user", "content": text}],
        "severity_score": severity,
        "functional_impact_score": functional,
        "completed_phases": [
            "presenting_complaint",
            "localised_detail",
            "priority_questions",
        ],
    }
    if onset:
        updates["onset_circumstance"] = {"text": onset, "source": "free_text"}
    if character:
        updates["character"] = character
    return SessionState(**updates)


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


def _print_tool_telemetry(label: str) -> dict:
    loop = _get_last_tool_trace()
    calls = loop.get("tool_calls") or []
    results: list[dict] = []
    for traced in loop.get("tool_results") or []:
        raw = traced.get("result") if isinstance(traced, dict) else None
        try:
            result = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            result = None
        if not isinstance(result, dict):
            continue
        results.append(
            {
                "query": result.get("query"),
                "successful": [
                    {
                        "url": source.get("url"),
                        "bm25_score": source.get("bm25_score"),
                        "latency_ms": source.get("latency_ms"),
                    }
                    for source in result.get("successful_sources") or []
                ],
                "failed": [
                    {
                        "url": source.get("url"),
                        "error_code": source.get("error_code"),
                        "bm25_score": source.get("bm25_score"),
                        "latency_ms": source.get("latency_ms"),
                    }
                    for source in result.get("failed_sources") or []
                ],
                "batch_latency_ms": result.get("batch_latency_ms"),
            }
        )
    summary = {
        "tool_choice": loop.get("tool_choice"),
        "tool_call_count": len(calls),
        "tool_calls": calls,
        "tool_results": results,
    }
    print(
        f"{label} tool_loop:",
        summary,
    )
    return summary


def _check_topics(topics: list[TopicCandidate], label: str) -> list[str]:
    fails: list[str] = []
    for t in topics:
        if not t.is_red_flag:
            fails.append(f"{label}: topic {t.topic!r} is_red_flag=False (must be True)")
        if t.topic not in _POOL_SUBS:
            fails.append(f"{label}: topic {t.topic!r} not in REDFLAG_TARGETS")
    return fails


def _check_questions(questions: list[QuestionField], label: str) -> list[str]:
    fails: list[str] = []
    for q in questions:
        if q.kind != "yes_no":
            fails.append(f"{label}: {q.id} kind={q.kind!r} (must be yes_no)")
        if q.en_prompt is not None or any(
            o.en_label is not None for o in (q.options or [])
        ):
            fails.append(f"{label}: en_* set on {q.id} while session=en")
        prompt = (q.prompt or "").casefold()
        # Bundled OR questions: several clauses joined with commas + " or ".
        if prompt.count(",") >= 2 and " or " in prompt:
            fails.append(
                f"{label}: {q.id} looks bundled (comma list + 'or'): {q.prompt!r}"
            )
    return fails


def _run_case(
    label: str,
    state: SessionState,
    *,
    expect_empty_preferred: bool = False,
    expect_abc_bias: bool = False,
    expect_split_airway: bool = False,
) -> tuple[int, dict]:
    print(f"--- {label} ---")
    ctx = build_agent_context(state)
    print("context presentation_category:", ctx.get("presentation_category"))
    print("known_collect_values:", ctx.get("known_collect_values"))
    pool = _get_candidate_pool(_PHASE, ctx)
    print("candidate_pool:", pool)
    failures = 0
    if pool != _EXPECTED_POOL:
        print("REJECTED: pool not full REDFLAG_TARGETS with clinical_hint")
        failures += 1

    topics: list[TopicCandidate] = []
    questions: list[QuestionField] = []
    try:
        topics, questions = devise_then_generate(_PHASE, state, max_questions=9)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR devise_then_generate: {exc}")
        failures += 1
        tool = _print_tool_telemetry(label)
        return failures, {"error": str(exc), "tool_loop": tool}

    print("devise topics:")
    print(_dump(topics))
    tool = _print_tool_telemetry(label)
    if tool["tool_call_count"] != 1:
        print(f"REJECTED: {label}: expected exactly one web_search call")
        failures += 1
    print("qg questions:")
    print(_dump(questions))

    for msg in _check_topics(topics, label):
        print(f"REJECTED: {msg}")
        failures += 1
    for msg in _check_questions(questions, label):
        print(f"REJECTED: {msg}")
        failures += 1
    if topics and len(questions) < len(topics):
        print(
            f"WARN: {label}: {len(topics)} topics but only "
            f"{len(questions)} questions (expected ≥1 finding/topic)"
        )
    if expect_split_airway:
        airway_qs = [q for q in questions if (q.collect_target_id or "") == "AIRWAY"]
        if len(airway_qs) < 2:
            print(
                f"REJECTED: {label}: expected ≥2 AIRWAY finding questions, "
                f"got {len(airway_qs)}"
            )
            failures += 1
        else:
            print(
                f"case AIRWAY split OK: {len(airway_qs)} questions — "
                + "; ".join(q.prompt for q in airway_qs)
            )
    if expect_empty_preferred and topics:
        print(
            f"WARN: {label}: expected lean/empty Devise but got "
            f"{[t.topic for t in topics]} (over-trigger check — soft)"
        )
    if expect_abc_bias:
        tops = {t.topic for t in topics}
        abc = tops & {"AIRWAY", "BREATHING", "CIRCULATION"}
        if not abc:
            print(
                f"WARN: {label}: expected AIRWAY/BREATHING/CIRCULATION "
                f"bias, got {[t.topic for t in topics]}"
            )
        else:
            print(f"case ABC bias OK: {sorted(abc)}")
    print()
    return failures, {
        "topics": [t.model_dump(mode="json") for t in topics],
        "questions": [q.model_dump(mode="json") for q in questions],
        "tool_loop": tool,
    }


def _run() -> int:
    print("=== redflag_screening Azure smoke ===\n")
    failures = 0
    telemetry: dict[str, dict] = {}

    # Case 1 — ordinary localised wrist, no red-flag indicators
    f1, t1 = _run_case(
        "case1_ordinary_wrist",
        _state(
            text=(
                "Twisted my wrist playing tennis yesterday. "
                "Swollen and bruised, sharp when I move it."
            ),
            onset="Twisted it playing tennis yesterday",
            character=[{"text": "Sharp", "source": "option"}],
            severity=4,
            functional=3,
        ),
    )
    failures += f1
    telemetry["case1"] = t1

    # Case 2 — chest tightness mentioned in priority-era answers
    f2, t2 = _run_case(
        "case2_chest_tightness_in_priority",
        _state(
            text=(
                "Fell on my outstretched hand — wrist swollen. "
                "Also mentioned mild chest tightness when climbing stairs."
            ),
            onset="Fall onto outstretched hand yesterday",
            character=[
                {
                    "text": (
                        "Sharp at the wrist; also mild chest tightness "
                        "when climbing stairs (mentioned during priority)"
                    ),
                    "source": "free_text",
                }
            ],
            severity=4,
            functional=3,
        ),
        expect_abc_bias=True,
    )
    failures += f2
    telemetry["case2"] = t2

    # Case 3 — unremarkable minor bruise
    f3, t3 = _run_case(
        "case3_unremarkable_bruise",
        _state(
            text=(
                "Small bruise on my shin from bumping the coffee table "
                "yesterday. Barely hurts, just wanted it checked."
            ),
            onset="Bumped coffee table yesterday",
            character=[{"text": "Mild ache", "source": "free_text"}],
            severity=1,
            functional=1,
        ),
        expect_empty_preferred=True,
    )
    failures += f3
    telemetry["case3"] = t3

    # Case 4 — sore throat + allergic/airway concern (CLI walkthrough shape)
    f4, t4 = _run_case(
        "case4_sore_throat_airway_split",
        _state(
            text=(
                "Feeling cold and sore throat for more than a week. "
                "Painful swallowing; mentioned fever, widespread rash, "
                "and lip/face/throat swelling during clarify."
            ),
            presentation_category="NOT_LOCALISED",
            onset="More than 1 week",
            character=[
                {"text": "It is there all the time", "source": "option"},
                {"text": "It hurts more when I swallow", "source": "option"},
            ],
            severity=6,
            functional=4,
        ),
        expect_abc_bias=True,
        expect_split_airway=True,
    )
    failures += f4
    telemetry["case4"] = t4

    print("=== search-bias summary ===")
    c2_calls = (
        (telemetry.get("case2") or {}).get("tool_loop", {}).get("tool_call_count", "?")
    )
    print(
        f"case2 (redflag, uncertain safety) tool_call_count={c2_calls}; "
        "priority and redflag phases both require exactly one curated "
        "web_search call."
    )
    print(f"\nfailures={failures}")
    return 1 if failures else 0


def main() -> None:
    buf = StringIO()
    with redirect_stdout(buf):
        code = _run()
    text = buf.getvalue()
    path = next_result_path(_RESULTS_DIR)
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {path}")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
