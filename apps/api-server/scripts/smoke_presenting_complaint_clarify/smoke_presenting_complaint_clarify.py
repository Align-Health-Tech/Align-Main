"""Local Azure smoke for presenting_complaint_clarify (Devise + QG). NOT for CI.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_presenting_complaint_clarify/smoke_presenting_complaint_clarify.py

Drives each case through classifier → require ready=false → devise_then_generate,
then runs validate_qg_questions on the QG output.

For ``vague_hurts``, also simulates tapping Arm → re-classify → apply
``chief_complaint`` overwrite from ``chiefComplaintSummary``.

Results under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt`` (never overwrite).
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
    conversation_from_state,
    devise_then_generate,
    run_classifier,
)
from engine.session_state_mappers.ai import map_classifier_result
from intelligence.qg_phase_validators import validate_qg_questions
from schemas.clinical_ai_io import ClassifierInput
from schemas.session_states import SessionState

CASES: list[tuple[str, str, str]] = [
    ("wrist_ambiguous", "it hurts sometimes", "localised wrist → ambiguous"),
    ("fever_ambiguous", "I feel a bit off", "systemic fever → vague unwell"),
    ("vague_hurts", "something hurts", "same as slice-1 vague"),
]

_PHASE = "presenting_complaint_clarify"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _state_for(text: str) -> SessionState:
    return SessionState(
        session_id="smoke-pc-clarify",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="female",
        chief_complaint={"text": text, "source": "free_text"},
        messages=[{"role": "user", "content": text}],
    )


def _classify(state: SessionState):
    return run_classifier(
        ClassifierInput(
            prompt_name="presenting_complaint",
            conversation=conversation_from_state(state),
            context=build_agent_context(state),
        )
    )


def _check_qg(questions: list) -> list[str]:
    notes: list[str] = []
    try:
        validate_qg_questions(_PHASE, questions)
        notes.append("validate_qg_questions: OK")
    except ValueError as exc:
        notes.append(f"validate_qg_questions: REJECTED — {exc}")

    for q in questions:
        dumped = q.model_dump(mode="json")
        if "allow_other" in dumped:
            notes.append(f"allow_other: REJECTED — still present on {q.id!r}")
        else:
            notes.append(f"allow_other absent on {q.id!r}: OK")

        en_ok = q.en_prompt is None and all(
            o.en_label is None for o in (q.options or [])
        )
        if en_ok:
            notes.append(f"en_prompt/en_label null on {q.id!r}: OK")
        else:
            notes.append(
                f"en_fields: REJECTED — {q.id!r} has en_prompt="
                f"{q.en_prompt!r} or an option en_label set "
                f"(session_language=en)"
            )
    return notes


def _vague_tap_arm_reclassify(raw: str, state: SessionState) -> list[str]:
    """Simulate clarify answer → re-classify → apply chief_complaint summary.

    Bare majorRegion taps (e.g. \"Arm\") often stay ``ready: false`` under the
    classifier's broad-region rule. Use a reply that names a specific site so
    this smoke can exercise the ``ai_summary`` overwrite path.
    """
    notes: list[str] = []
    # majorRegion alone is usually not enough (prompt: clarify within region).
    tapped = "right wrist"
    state = state.model_copy(
        update={
            "messages": list(state.messages or [])
            + [{"role": "user", "content": tapped}],
        }
    )
    print(f"--- re-classify after clarify reply {tapped!r} ---")
    print(
        "(note: bare 'Arm' often stays ready=false per broad-region rule; "
        "using a specific site to exercise chiefComplaintSummary overwrite)"
    )
    clf2 = _classify(state)
    print(
        json.dumps(
            clf2.model_dump(mode="json", by_alias=True),
            indent=2,
            ensure_ascii=False,
        )
    )
    if not clf2.ready:
        notes.append(
            "reclassify: REJECTED — expected ready=true after specific site"
        )
        return notes
    if not clf2.chief_complaint_summary:
        notes.append(
            "reclassify: REJECTED — ready=true but chiefComplaintSummary missing"
        )
        return notes

    updates = map_classifier_result(state, clf2)
    merged = state.model_copy(update=updates)
    cc = merged.chief_complaint or {}
    print("applied chief_complaint:", json.dumps(cc, ensure_ascii=False))
    print("messages still:", json.dumps(merged.messages, ensure_ascii=False))

    if cc.get("source") != "ai_summary":
        notes.append(
            f"chief_complaint source: REJECTED — expected ai_summary, "
            f"got {cc.get('source')!r}"
        )
    elif cc.get("text") == raw:
        notes.append(
            "chief_complaint text: REJECTED — still raw input, expected summary"
        )
    else:
        notes.append(
            f"chief_complaint overwrite: OK (summary={cc.get('text')!r})"
        )

    msgs = merged.messages or []
    if not any(
        isinstance(m, dict) and m.get("content") == raw for m in msgs
    ):
        notes.append(
            "messages: REJECTED — original raw input missing after overwrite"
        )
    else:
        notes.append("messages preserve original raw input: OK")
    return notes


def _run() -> int:
    print("=== presenting_complaint_clarify Devise+QG Azure smoke ===\n")
    failures = 0
    for label, text, note in CASES:
        print(f"--- case: {label} ({note}) ---")
        print(f"input: {text!r}")
        state = _state_for(text)
        try:
            clf = _classify(state)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR classifier: {exc}\n")
            failures += 1
            continue

        print("classifier:")
        print(
            json.dumps(
                clf.model_dump(mode="json", by_alias=True),
                indent=2,
                ensure_ascii=False,
            )
        )
        if clf.ready:
            print(
                "WARN: classifier ready=true — clarify path would not fire in "
                "production; skipping Devise+QG for this case.\n"
            )
            failures += 1
            continue

        try:
            topics, questions = devise_then_generate(_PHASE, state)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR devise_then_generate: {exc}\n")
            failures += 1
            continue

        print("devise topics:")
        print(
            json.dumps(
                [t.model_dump(mode="json") for t in topics],
                indent=2,
                ensure_ascii=False,
            )
        )
        print("qg questions:")
        print(
            json.dumps(
                [q.model_dump(mode="json") for q in questions],
                indent=2,
                ensure_ascii=False,
            )
        )

        for line in _check_qg(questions):
            print(line)
            if "REJECTED" in line:
                failures += 1

        if label == "vague_hurts":
            for line in _vague_tap_arm_reclassify(text, state):
                print(line)
                if "REJECTED" in line:
                    failures += 1
        print()

    print(f"done; failures={failures}")
    return 1 if failures else 0


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
