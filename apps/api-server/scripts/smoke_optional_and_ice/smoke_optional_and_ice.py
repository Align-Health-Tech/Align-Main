"""Local Azure smoke for optional_questions + ice. NOT for CI.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_optional_and_ice/smoke_optional_and_ice.py

Reports optional and ICE separately. For optional, if past_history appears,
simulates answers and dumps ``intake_facts`` (expect kind=PAST_HISTORY).
For ICE, confirms QG-only (no Devise) and zero ``web_search`` tool calls.

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
    run_question_generation,
)
from engine.session_state_mappers import map_patient_answers
from intelligence.qg_phase_validators import validate_qg_questions
from intelligence.llm_client import (
    _get_last_tool_trace,
    _reset_last_tool_trace,
)
from schemas.clinical_ai_io import QuestionGenerationInput
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_OPTIONAL_PHASE = "optional_questions"
_ICE_PHASE = "ice"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _state_localised_wrist() -> SessionState:
    return SessionState(
        session_id="smoke-optional-ice",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="male",
        chief_complaint={
            "text": "Twisted my wrist playing tennis yesterday",
            "source": "free_text",
        },
        presentation_category="LOCALISED",
        messages=[
            {
                "role": "user",
                "content": "Twisted my wrist playing tennis yesterday. Swollen.",
            }
        ],
        onset_circumstance={
            "text": "Twisted it playing tennis yesterday",
            "source": "free_text",
        },
        character=[{"text": "Sharp", "source": "option"}],
        severity_score=4,
        functional_impact_score=3,
        completed_phases=[
            "presenting_complaint",
            "localised_detail",
            "priority_questions",
            "redflag_screening",
        ],
        turn_number=8,
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


def _print_tool_telemetry(label: str) -> dict:
    loop = _get_last_tool_trace()
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


def _web_search_count(loop: dict) -> int:
    return sum(
        1
        for call in (loop.get("tool_calls") or [])
        if isinstance(call, dict) and call.get("name") == "web_search"
    )


def _check_optional_questions(questions: list[QuestionField]) -> list[str]:
    fails: list[str] = []
    for q in questions:
        if q.required:
            fails.append(f"optional {q.id}: required must be false")
        if q.en_prompt is not None or any(
            o.en_label is not None for o in (q.options or [])
        ):
            fails.append(f"optional {q.id}: en_* set while session=en")
    return fails


def _simulate_past_history_apply(
    state: SessionState,
    questions: list[QuestionField],
) -> tuple[int, list[dict]]:
    """If past_history multi_choice present, apply sample answers and dump facts."""
    ph = next(
        (
            q
            for q in questions
            if q.collect_target_id == "past_history" and q.kind == "multi_choice"
        ),
        None,
    )
    if ph is None:
        print("past_history apply: SKIPPED (no past_history multi_choice in batch)")
        return 0, []

    values: list[str] = []
    for opt in ph.options or []:
        if (opt.value or "").casefold() == "other":
            values.append(f"{opt.value}: previous wrist surgery abroad")
        else:
            values.append(opt.value)
    if not values:
        values = ["Major surgery", "Other: previous wrist surgery abroad"]

    state_awaiting = state.model_copy(
        update={"awaiting_phase": _OPTIONAL_PHASE}
    )
    updates = map_patient_answers(
        state_awaiting,
        {"answers": [{"question_id": ph.id, "value": values}]},
        questions,
    )
    facts = updates.get("intake_facts") or []
    print("past_history apply intake_facts:")
    print(_dump(facts))
    failures = 0
    new_facts = [
        f
        for f in facts
        if isinstance(f, dict) and f.get("kind") == "PAST_HISTORY"
    ]
    if not new_facts:
        print("REJECTED: expected at least one PAST_HISTORY intake_fact")
        failures += 1
    for fact in new_facts:
        if fact.get("kind") != "PAST_HISTORY":
            print(f"REJECTED: fact kind={fact.get('kind')!r} (want PAST_HISTORY)")
            failures += 1
    return failures, facts


def _run_optional(state: SessionState) -> tuple[int, dict]:
    print("=== OPTIONAL_QUESTIONS ===\n")
    failures = 0
    _reset_last_tool_trace()
    topics: list[TopicCandidate] = []
    questions: list[QuestionField] = []
    try:
        topics, questions = devise_then_generate(
            _OPTIONAL_PHASE, state, max_questions=4
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR optional devise_then_generate: {exc}")
        tool = _print_tool_telemetry("optional")
        return 1, {"error": str(exc), "tool_loop": tool}

    print("optional devise topics:")
    print(_dump(topics))
    tool = _print_tool_telemetry("optional")
    print("optional qg questions:")
    print(_dump(questions))

    for msg in _check_optional_questions(questions):
        print(f"REJECTED: {msg}")
        failures += 1
    if len(questions) > 4:
        print(f"REJECTED: got {len(questions)} questions (max 4)")
        failures += 1

    apply_failures, facts = _simulate_past_history_apply(state, questions)
    failures += apply_failures
    print()
    return failures, {
        "topics": [t.model_dump(mode="json") for t in topics],
        "questions": [q.model_dump(mode="json") for q in questions],
        "intake_facts": facts,
        "tool_loop": tool,
        "web_search_count": _web_search_count(tool),
    }


def _run_ice(state: SessionState) -> tuple[int, dict]:
    print("=== ICE (QG only) ===\n")
    failures = 0
    _reset_last_tool_trace()
    try:
        result = run_question_generation(
            QuestionGenerationInput(
                prompt_name=_ICE_PHASE,
                prioritised_topics=[],
                eligible_targets=[],
                context=build_agent_context(state),
            )
        )
        validate_qg_questions(_ICE_PHASE, result.questions)
        questions = result.questions
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR ice QG: {exc}")
        tool = _print_tool_telemetry("ice")
        return 1, {"error": str(exc), "tool_loop": tool, "devise_called": False}

    tool = _print_tool_telemetry("ice")
    print("ice qg questions:")
    print(_dump(questions))

    ids = tuple(q.id for q in questions)
    targets = tuple(q.collect_target_id for q in questions)
    expected = ("ice_idea", "ice_concern", "ice_expectation")
    if ids != expected or targets != expected:
        print(
            f"REJECTED: ice expected {expected!r} in order; "
            f"got ids={ids!r} targets={targets!r}"
        )
        failures += 1
    for q in questions:
        if q.kind != "multi_choice":
            print(f"REJECTED: ice {q.id} kind={q.kind!r} (want multi_choice)")
            failures += 1
            continue
        values = [o.value for o in (q.options or [])]
        if "Other" not in values:
            print(f"REJECTED: ice {q.id} missing Other; values={values!r}")
            failures += 1
        if not 3 <= len(values) <= 7:
            print(
                f"REJECTED: ice {q.id} expected 3–7 options, got {len(values)}"
            )
            failures += 1

    web_n = _web_search_count(tool)
    if web_n:
        print(f"REJECTED: ice made {web_n} web_search call(s) (want 0)")
        failures += 1
    else:
        print("ice web_search_count=0 OK")
    print("ice devise_called=False OK (QG-only path)")
    print()
    return failures, {
        "questions": [q.model_dump(mode="json") for q in questions],
        "tool_loop": tool,
        "web_search_count": web_n,
        "devise_called": False,
    }


def _run() -> int:
    print("=== optional_questions + ice Azure smoke ===\n")
    state = _state_localised_wrist()
    opt_fail, opt_data = _run_optional(state)
    ice_fail, ice_data = _run_ice(state)

    print("=== PHASE SUMMARY ===")
    print(
        f"optional_questions: "
        f"{'PASS' if opt_fail == 0 else 'FAIL'} "
        f"(failures={opt_fail}, "
        f"topics={len(opt_data.get('topics') or [])}, "
        f"questions={len(opt_data.get('questions') or [])}, "
        f"web_search={opt_data.get('web_search_count', '?')})"
    )
    print(
        f"ice: "
        f"{'PASS' if ice_fail == 0 else 'FAIL'} "
        f"(failures={ice_fail}, "
        f"web_search={ice_data.get('web_search_count', '?')}, "
        f"devise_called={ice_data.get('devise_called')})"
    )
    total = opt_fail + ice_fail
    print(f"\ntotal_failures={total}")
    return 1 if total else 0


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
