"""Local Azure smoke for non_localised_categoriser (+ clarify). NOT for CI.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_non_localised_categoriser/smoke_non_localised_categoriser.py

Cases:
  1. Clear SYSTEMIC → ready=true, category, confidence ≥ 0.85
  2. Ambiguous → ready=false + Devise/QG Yes/No/I don't know contract
  3. (report only) max-3-rounds force-commit trackability

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
    conversation_from_state,
    devise_then_generate,
    run_classifier,
)
from engine.session_state_mappers.ai import map_classifier_result
from intelligence.qg_phase_validators import validate_qg_questions
from schemas.clinical_ai_io import ClassifierInput
from schemas.session_states import SessionState

_CATEGORISER = "non_localised_categoriser"
_CLARIFY = "non_localised_clarify"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"
_NL_VALUES = ("Yes", "No", "I don't know")


def _state_for(text: str) -> SessionState:
    """Post–PC NOT_LOCALISED: chief_complaint already ai_summary-shaped."""
    return SessionState(
        session_id="smoke-nl-categoriser",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="female",
        presentation_category="NOT_LOCALISED",
        chief_complaint={"text": text, "source": "ai_summary"},
        messages=[{"role": "user", "content": text}],
    )


def _classify(state: SessionState):
    return run_classifier(
        ClassifierInput(
            prompt_name=_CATEGORISER,
            conversation=conversation_from_state(state),
            context=build_agent_context(state),
        )
    )


def _dump(obj: object) -> str:
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False)
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


def _run() -> int:
    print("=== non_localised_categoriser Azure smoke ===\n")
    failures = 0

    # --- Case 1: clear SYSTEMIC ---
    print("--- case 1: clear_systemic ---")
    text1 = "fever and body aches, no other symptoms"
    state1 = _state_for(text1)
    print(f"input: {text1!r}")
    try:
        clf1 = _classify(state1)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}\n")
        return 1
    print(_dump(clf1))
    if not clf1.ready:
        print("REJECTED: expected ready=true")
        failures += 1
    elif clf1.category != "SYSTEMIC":
        print(f"REJECTED: expected SYSTEMIC, got {clf1.category!r}")
        failures += 1
    elif (clf1.confidence or 0) < 0.85:
        print(f"REJECTED: confidence {clf1.confidence} < 0.85")
        failures += 1
    else:
        print("case1: OK")
    if clf1.chief_complaint_summary or clf1.localised_anatomy_sites:
        print("WARN: PC-only fields present on NL categoriser result")
    updates = map_classifier_result(
        state1, clf1, prompt_name=_CATEGORISER
    )
    print("apply:", updates)
    if "presentation_category" in updates:
        print("REJECTED: apply wrote presentation_category")
        failures += 1
    elif updates.get("non_localised_category") != clf1.category and clf1.ready:
        print("REJECTED: apply missing non_localised_category")
        failures += 1
    print()

    # --- Case 2: ambiguous → clarify ---
    print("--- case 2: ambiguous_systemic_vs_gi ---")
    text2 = "feel unwell and my stomach hurts a bit"
    state2 = _state_for(text2)
    print(f"input: {text2!r}")
    try:
        clf2 = _classify(state2)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}\n")
        failures += 1
        clf2 = None
    if clf2 is not None:
        print(_dump(clf2))
        if clf2.ready:
            print(
                "WARN: ready=true on ambiguous case — still checking "
                f"category={clf2.category!r}; clarify path may not fire"
            )
            # Soft: don't fail hard if model commits; prefer ready=false
            if clf2.category not in {
                "SYSTEMIC",
                "GASTROINTESTINAL",
            }:
                print(f"REJECTED: unexpected category {clf2.category!r}")
                failures += 1
        else:
            print("ready=false: OK (reason should name candidate buckets)")
            try:
                topics, questions = devise_then_generate(_CLARIFY, state2)
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR devise_then_generate: {exc}")
                failures += 1
            else:
                print("devise topics:")
                print(_dump(topics))
                print("qg questions:")
                print(_dump(questions))
                try:
                    validate_qg_questions(_CLARIFY, questions)
                    print("validate_qg_questions: OK")
                except ValueError as exc:
                    print(f"validate_qg_questions: REJECTED — {exc}")
                    failures += 1
                for q in questions:
                    vals = tuple(o.value for o in (q.options or []))
                    if vals != _NL_VALUES:
                        print(
                            f"REJECTED: {q.id} options {vals} != {_NL_VALUES}"
                        )
                        failures += 1
                    if q.en_prompt is not None or any(
                        o.en_label is not None for o in (q.options or [])
                    ):
                        print(f"REJECTED: en_* set on {q.id} while session=en")
                        failures += 1
                    else:
                        print(f"en_prompt/en_label null on {q.id}: OK")
    print()

    # --- Case 3: trackability note (no live 3-round loop) ---
    print("--- case 3: max-3-rounds force-commit (code hard-stop) ---")
    print(
        "Engine: after non_localised_clarify_rounds >= 3, skip run_classifier "
        "and set non_localised_category from non_localised_category_lean "
        "(best-fit category on ready:false) or SYSTEMIC default. "
        "Covered by tests.test_nl_clarify_rounds — not re-driven live here."
    )
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
