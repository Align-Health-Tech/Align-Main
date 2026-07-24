"""Local Azure smoke for duration QG (loc/nl detail). NOT for CI.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_duration/smoke_duration.py

Calls ``devise_then_generate("duration", devise=False)`` for two contexts
(LOCALISED acute wrist vs NOT_LOCALISED longer illness) and checks:

  - exactly one question, ``collect_target_id == "duration"``
  - ``single_choice`` with 3–6 options including Other
  - ``validate_qg_questions`` passes
  - no Devise / no ``web_search``

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
from engine.agent_bridge import devise_then_generate
from intelligence.llm_client import get_last_tool_loop, reset_last_tool_loop
from schemas.session_states import SessionState

_PHASE = "duration"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _state_localised_acute() -> SessionState:
    return SessionState(
        session_id="smoke-duration-loc",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="male",
        chief_complaint={
            "text": "Twisted my right ankle this morning",
            "source": "free_text",
        },
        presentation_category="LOCALISED",
        messages=[
            {
                "role": "user",
                "content": "Twisted my right ankle this morning playing football.",
            }
        ],
        severity_score=6,
        completed_phases=["presenting_complaint"],
        turn_number=3,
    )


def _state_non_localised_gradual() -> SessionState:
    return SessionState(
        session_id="smoke-duration-nl",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="female",
        chief_complaint={
            "text": "Feeling exhausted and feverish for a while",
            "source": "free_text",
        },
        presentation_category="NOT_LOCALISED",
        non_localised_category="SYSTEMIC",
        messages=[
            {
                "role": "user",
                "content": (
                    "I've been exhausted with on-and-off fever. "
                    "Not sure exactly when it started."
                ),
            }
        ],
        severity_score=5,
        functional_impact_score=6,
        completed_phases=["presenting_complaint", "non_localised_detail"],
        turn_number=5,
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


def _web_search_count(tool: object) -> int:
    if not isinstance(tool, dict):
        return 0
    calls = tool.get("tool_calls") or []
    return sum(
        1
        for c in calls
        if isinstance(c, dict) and c.get("name") == "web_search"
    )


def _print_tool_telemetry(label: str) -> dict | None:
    tool = get_last_tool_loop()
    print(f"{label} tool_loop web_search_count={_web_search_count(tool)}")
    return tool


def _run_case(label: str, state: SessionState) -> tuple[int, dict]:
    print(f"=== {label} ===\n")
    failures = 0
    reset_last_tool_loop()
    try:
        topics, questions = devise_then_generate(
            _PHASE, state, devise=False
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR duration QG: {exc}")
        tool = _print_tool_telemetry(label)
        return 1, {"error": str(exc), "tool_loop": tool}

    tool = _print_tool_telemetry(label)
    print(f"{label} topics (expect []): {_dump(topics)}")
    print(f"{label} questions:")
    print(_dump(questions))

    if topics:
        print(f"REJECTED: expected no Devise topics, got {len(topics)}")
        failures += 1
    if len(questions) != 1:
        print(
            f"REJECTED: expected exactly 1 question, got {len(questions)}"
        )
        failures += 1
    else:
        q = questions[0]
        if q.collect_target_id != "duration":
            print(
                f"REJECTED: collect_target_id={q.collect_target_id!r} "
                "(want 'duration')"
            )
            failures += 1
        if q.kind != "single_choice":
            print(f"REJECTED: kind={q.kind!r} (want single_choice)")
            failures += 1
        values = [o.value for o in (q.options or [])]
        if "Other" not in values:
            print(f"REJECTED: missing Other; values={values!r}")
            failures += 1
        if not 3 <= len(values) <= 6:
            print(
                f"REJECTED: expected 3–6 options, got {len(values)}"
            )
            failures += 1

    web_n = _web_search_count(tool)
    if web_n:
        print(f"REJECTED: {web_n} web_search call(s) (want 0)")
        failures += 1
    else:
        print(f"{label} web_search_count=0 OK")
    print()
    return failures, {
        "questions": [q.model_dump(mode="json") for q in questions],
        "topics": [t.model_dump(mode="json") for t in topics],
        "tool_loop": tool,
        "web_search_count": web_n,
    }


def _run() -> int:
    print("=== duration QG Azure smoke ===\n")
    loc_fail, loc_data = _run_case(
        "LOCALISED acute ankle", _state_localised_acute()
    )
    nl_fail, nl_data = _run_case(
        "NOT_LOCALISED gradual systemic", _state_non_localised_gradual()
    )

    print("=== SUMMARY ===")
    print(
        f"LOCALISED: "
        f"{'PASS' if loc_fail == 0 else 'FAIL'} "
        f"(failures={loc_fail}, "
        f"questions={len(loc_data.get('questions') or [])})"
    )
    print(
        f"NOT_LOCALISED: "
        f"{'PASS' if nl_fail == 0 else 'FAIL'} "
        f"(failures={nl_fail}, "
        f"questions={len(nl_data.get('questions') or [])})"
    )
    total = loc_fail + nl_fail
    print(f"\ntotal_failures={total}")
    return 1 if total else 0


def main() -> None:
    buf = StringIO()
    with redirect_stdout(buf):
        code = _run()
    text = buf.getvalue()
    path = next_result_path(_RESULTS_DIR)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {path}")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
