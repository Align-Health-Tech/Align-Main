#!/usr/bin/env python3
"""Interactive session walkthrough — consent → graph → survey → complete.

NOT for CI. Same spirit as M5 smoke scripts.

Usage (from apps/api-server):

  ./venv/bin/python scripts/cli_session.py
  ./venv/bin/python scripts/cli_session.py --session_language ko --patient_sex male
  ./venv/bin/python scripts/cli_session.py --real-azure   # spot-check (needs Azure env)

Default: mocked clinical_ai (no Azure). Choice questions use ↑↓ + Enter.
Commands (type at any free-text prompt, or pick from action menu):
  skip / state / quit / complete - AI generated UI for quick path validation
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _cli_menu import prompt_text, select_many, select_one
from schemas.question_fields import NextStep, QuestionField
from services.session_lifecycle import SessionLifecycle
from services.session_store import SessionStore

_PHASE_TRACE: dict[str, str] = {
    "consent": (
        "→ routers/session (lifecycle): build_consent_questions + "
        "build_next_step_raw — no graph"
    ),
    "presenting_complaint": (
        "→ engine/nodes/presenting_complaint.py: "
        "run_classifier → (optional) devise_then_generate clarify"
    ),
    "localised_detail": (
        "→ engine/nodes/localised_detail.py: deterministic body_diagram / "
        "severity+onset chips — no LLM"
    ),
    "non_localised_detail": (
        "→ engine/nodes/non_localised_detail.py: "
        "non_localised_categoriser (+ clarify) then timing chips"
    ),
    "priority_questions": (
        "→ engine/nodes/priority_questions.py: devise_then_generate → "
        "agent_bridge.run_devise_and_prioritise → "
        "agent_bridge.run_question_generation"
    ),
    "redflag_screening": (
        "→ engine/nodes/redflag_screening.py: devise_then_generate "
        "(redflag pool) → QG yes_no; flags stamped in apply"
    ),
    "optional_questions": (
        "→ engine/nodes/optional_questions.py: devise_then_generate "
        "(skippable) → QG"
    ),
    "ice": (
        "→ engine/nodes/ice.py: run_question_generation only "
        "(no Devise); then silent review → nurse_review summary"
    ),
    "survey": (
        "→ routers/session (lifecycle): build_survey_questions + "
        "build_next_step — no graph; status still IN_PROGRESS"
    ),
    "complete": (
        "→ patient terminal NextStep; clinician "
        "POST /clinician/sessions/{id}/complete → COMPLETED"
    ),
}

_WATCH_KEYS = (
    "presentation_category",
    "chief_complaint",
    "severity_score",
    "functional_impact_score",
    "raised_flag_topics",
    "body_structures",
    "encounter_summary",
    "intake_facts",
    "encounter_medication",
    "ice_idea",
    "ice_concern",
    "ice_expectation",
    "completed_phases",
    "is_session_complete",
    "awaiting_phase",
)

# Sentinel from collect_answer for meta-commands.
_CMD_QUIT = object()
_CMD_STATE = object()
_CMD_SKIP = object()
_CMD_COMPLETE = object()


def _print_step(step: NextStep, status: str) -> None:
    print()
    print("=" * 60)
    print(
        f"status={status}  step_type={step.step_type}  "
        f"phase={step.phase}  turn={step.turn_number}"
    )
    if step.step_type == "complete":
        print(_PHASE_TRACE["complete"])
    else:
        trace = _PHASE_TRACE.get(step.phase or "", "")
        if trace:
            print(trace)
    if step.diagram_file:
        print(f"  [body_diagram] file={step.diagram_file}")
        print(f"  highlights={step.highlighted_region_ids}")
    for q in step.questions or []:
        print(f"  • [{q.id}] ({q.kind}) {q.prompt}")
        if q.options:
            opts = ", ".join(o.label or o.value for o in q.options)
            print(f"      options: {opts}")
    if step.step_type == "complete":
        print("  (patient complete — pick Complete on the next menu)")


def _snapshot(lifecycle: SessionLifecycle, session_id: str) -> dict[str, Any]:
    state = lifecycle.get_graph_state(session_id)
    if state is None:
        return {}
    data = state.model_dump()
    return {k: data.get(k) for k in _WATCH_KEYS}


def _diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in sorted(set(before) | set(after)):
        if before.get(k) != after.get(k):
            out[k] = {"from": before.get(k), "to": after.get(k)}
    return out


def _option_labels(q: QuestionField) -> list[str]:
    return [o.label or o.value for o in (q.options or [])]


def _option_value(q: QuestionField, label: str) -> str:
    for o in q.options or []:
        if (o.label or o.value) == label:
            return o.value
    return label


def _ask_choice_question(q: QuestionField) -> Any | None:
    """Return value for one choice question, or None if user quit."""
    if q.kind == "yes_no":
        pick = select_one(q.prompt, ["Yes", "No"])
        if pick is None:
            return None
        return "yes" if pick == "Yes" else "no"

    if q.kind == "consent_accept":
        pick = select_one(q.prompt, ["Accept", "Decline"])
        if pick is None:
            return None
        return pick == "Accept"

    if q.kind == "single_choice":
        labels = _option_labels(q)
        if not labels:
            return prompt_text(q.prompt, default=q.default_value or "")
        pick = select_one(q.prompt, labels)
        if pick is None:
            return None
        value = _option_value(q, pick)
        if value.casefold() == "other":
            detail = prompt_text("Other — type your answer")
            if detail is None:
                return None
            return f"Other:{detail}"
        return value

    if q.kind == "multi_choice":
        labels = _option_labels(q)
        if not labels:
            raw = prompt_text(q.prompt)
            return None if raw is None else [raw]
        picks = select_many(q.prompt, labels)
        if picks is None:
            return None
        values: list[str] = []
        for p in picks:
            value = _option_value(q, p)
            if value.casefold() == "other":
                detail = prompt_text("Other — type your answer")
                if detail is None:
                    return None
                values.append(f"Other:{detail}")
            else:
                values.append(value)
        return values

    # free_text / unknown
    return prompt_text(q.prompt, default=q.default_value or "")


def collect_answer(
    step: NextStep, *, status: str
) -> Any:
    """Interactive answer (menus for choices). Returns answer dict or sentinel."""
    # Meta actions always available as a first menu when not free-text-only.
    actions = ["Answer questions"]
    if step.phase == "optional_questions" or (
        step.questions and all(not q.required for q in step.questions)
    ):
        actions.append("Skip phase")
    actions.extend(["Show state", "Quit"])
    if step.step_type == "complete" and status == "AWAITING_REVIEW":
        pick = select_one(
            "Session awaiting clinician review",
            ["Mark complete (clinician)", "Show state", "Quit"],
        )
        if pick is None or pick == "Quit":
            return _CMD_QUIT
        if pick == "Show state":
            return _CMD_STATE
        return _CMD_COMPLETE

    if step.step_type == "body_diagram":
        regions = list(step.highlighted_region_ids or [])
        if not regions:
            regions = ["Select_RightWrist"]  # last-resort demo default
        action = select_one(
            f"Body diagram — {step.diagram_file or 'region'}",
            [*regions, "Show state", "Quit"],
        )
        if action is None or action == "Quit":
            return _CMD_QUIT
        if action == "Show state":
            return _CMD_STATE
        return {"region_id": action}

    # Choice / free-text questions
    questions = step.questions or []
    if not questions:
        action = select_one("No questions on this step", ["Show state", "Quit"])
        if action == "Show state":
            return _CMD_STATE
        return _CMD_QUIT

    # Offer skip/state/quit when useful; otherwise jump straight into answers
    # for single free_text (faster PC typing).
    only_free = len(questions) == 1 and questions[0].kind == "free_text"
    if not only_free:
        action = select_one("What next?", actions)
        if action is None or action == "Quit":
            return _CMD_QUIT
        if action == "Show state":
            return _CMD_STATE
        if action == "Skip phase":
            return _CMD_SKIP

    answers: list[dict[str, Any]] = []
    for q in questions:
        print()
        value = _ask_choice_question(q)
        if value is None:
            return _CMD_QUIT
        if isinstance(value, str) and value.lower() == "skip" and not q.required:
            return _CMD_SKIP
        answers.append({"question_id": q.id, "value": value})
    return {"answers": answers}


def _print_signals(
    ai: Any, before_calls: dict[str, int], lifecycle: SessionLifecycle, sid: str
) -> None:
    if ai is None:
        try:
            from intelligence.llm_client import get_last_tool_loop

            loop = get_last_tool_loop()
            tools = loop.get("tool_calls") or []
            print(f"  signals: azure tool_calls={len(tools)}")
            for t in tools[:5]:
                print(f"    • {t.get('name')} {t.get('args')}")
        except Exception:  # noqa: BLE001
            print("  signals: (real Azure)")
        return
    print("  signals:")
    print(
        f"    translate_calls: {before_calls['translate']} → {ai.translate_calls} "
        f"(+{ai.translate_calls - before_calls['translate']})"
    )
    print(
        f"    nurse_calls: {before_calls['nurse']} → {ai.nurse_calls} "
        f"(+{ai.nurse_calls - before_calls['nurse']})"
    )
    print(f"    qg_by_phase: {dict(ai.qg_calls_by_phase)}")
    state = lifecycle.get_graph_state(sid)
    if state is not None and state.raised_flag_topics:
        print(f"    raised_flag_topics: {state.raised_flag_topics}")


def run_interactive(args: argparse.Namespace) -> int:
    session_store = SessionStore()
    lifecycle = SessionLifecycle(session_store)

    ai = None
    patches: list[Any] = []
    if not args.real_azure:
        from tests.mock_clinical_ai import ClinicalAiMock, patch_clinical_ai

        ai = ClinicalAiMock()
        patches = patch_clinical_ai(ai)
        print("clinical_ai: MOCKED (pass --real-azure for Azure)")
    else:
        from dotenv import load_dotenv
        from intelligence.llm_client import get_model

        load_dotenv()
        get_model()  # fail fast if Azure env missing
        print("clinical_ai: REAL Azure")

    try:
        org_id = "org-cli"
        sid, step, status = lifecycle.create_session(
            session_language=args.session_language,
            patient_sex=args.patient_sex,
            organization_id=org_id,
            segment_type=args.segment_type,
            survey_enabled=True,
        )
        print(
            f"session_id={sid}  language={args.session_language}  "
            f"sex={args.patient_sex}  segment={args.segment_type}"
        )
        _print_step(step, status)

        while True:
            try:
                result = collect_answer(step, status=status)
            except (EOFError, KeyboardInterrupt):
                print()
                return 0

            if result is _CMD_QUIT:
                return 0
            if result is _CMD_STATE:
                state = lifecycle.get_graph_state(sid)
                if state is None:
                    print("(no graph state yet — still on consent)")
                else:
                    print(json.dumps(state.model_dump(), indent=2, default=str))
                continue
            if result is _CMD_COMPLETE:
                _sid, status = lifecycle.clinician_complete(sid)
                print(f"→ clinician complete: status={status}")
                return 0
            if result is _CMD_SKIP:
                answer: dict[str, Any] = {"skip": True}
            else:
                answer = result

            print(f"  applying answer: {json.dumps(answer, default=str)}")
            before = _snapshot(lifecycle, sid)
            before_calls = {
                "translate": getattr(ai, "translate_calls", 0) if ai else 0,
                "nurse": getattr(ai, "nurse_calls", 0) if ai else 0,
            }
            try:
                step, status = lifecycle.respond(sid, answer)
            except Exception as exc:  # noqa: BLE001 — CLI surface
                print(f"error: {exc}")
                continue
            after = _snapshot(lifecycle, sid)
            diff = _diff(before, after)
            _print_signals(ai, before_calls, lifecycle, sid)
            if diff:
                print("  state diff:")
                print(json.dumps(diff, indent=2, default=str))
            else:
                print("  state diff: (no watched fields changed)")
            _print_step(step, status)
    finally:
        for p in patches:
            p.stop()

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive Align session CLI")
    parser.add_argument(
        "--segment_type",
        default="URGENT_CARE",
        choices=["URGENT_CARE"],
        help="Organization segment → topology (only URGENT_CARE registered)",
    )
    parser.add_argument("--patient_sex", default=None, choices=["male", "female"])
    parser.add_argument("--session_language", default="en")
    parser.add_argument(
        "--real-azure",
        action="store_true",
        help="Use real clinical_ai agents instead of mocks",
    )
    return run_interactive(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
