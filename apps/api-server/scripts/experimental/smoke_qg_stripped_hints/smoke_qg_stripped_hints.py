"""Exploratory: QG with registry ids kept, phrasing hints stripped.

NOT for CI. Production unchanged.

Question: if we still pass collect-target ids (avoid topic drift) but omit
``clinical_hint`` / ``example_prompt`` / ``suggested_options``, does QG invent
better patient-facing options than when those registry suggestions are present?

Devise already never sees example_prompt / suggested_options — only
``{id, category, clinical_hint}``. This probe is about **Question Generation**.

Usage (from apps/api-server, Azure env set):

  ./venv/bin/python scripts/smoke_qg_stripped_hints/smoke_qg_stripped_hints.py

A. Devise (normal) → QG with **full** eligible_targets (control)
B. Same Devise topics → QG with eligible_targets reduced to
   ``{id, category, phase, free_text_policy}`` only

Context: wrist fall + Eliquis (priority case 4).

Results under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt``.
"""
from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

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
    run_question_generation,
)
from engine.session_state_mappers.ai import map_classifier_result
from intelligence.registry import get_eligible_targets
from schemas.clinical_ai_io import ClassifierInput, QuestionGenerationInput
from schemas.collect_targets import CollectTarget
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_PHASE = "priority_questions"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"

_ELIQUIS_TEXT = (
    "Hurt my wrist yesterday after a fall, still swollen and bruised. "
    "I'm on Eliquis (apixaban) for a heart condition."
)

# Keep identity + free_text_policy (comorbidities None-of-these rule); strip
# the three phrasing/suggestion fields the user called out.
_STRIPPED_KEEP = {"id", "category", "phase", "free_text_policy"}


def _state(text: str) -> SessionState:
    return SessionState(
        session_id="smoke-qg-stripped",
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
    updates = map_classifier_result(state, clf)
    print("apply keys:", sorted(updates.keys()))
    return state.model_copy(update=updates)


def _strip_targets(targets: list[CollectTarget]) -> list[CollectTarget]:
    out: list[CollectTarget] = []
    for t in targets:
        data = t.model_dump(include=_STRIPPED_KEEP)
        # Explicitly null the suggestion fields so dumps are unambiguous.
        data["clinical_hint"] = None
        data["example_prompt"] = None
        data["suggested_options"] = None
        out.append(CollectTarget.model_validate(data))
    return out


def _options_brief(questions: list[QuestionField]) -> list[dict]:
    return [
        {
            "id": q.id,
            "collect_target_id": q.collect_target_id,
            "kind": q.kind,
            "prompt": q.prompt,
            "option_values": [o.value for o in (q.options or [])],
            "default_value": q.default_value,
            "default_values": q.default_values,
        }
        for q in questions
    ]


def _run_qg(
    label: str,
    topics: list[TopicCandidate],
    eligible: list[CollectTarget],
    context: dict,
) -> list[QuestionField]:
    print(f"--- {label} ---")
    print(
        "eligible_targets fields present:",
        sorted(
            {
                k
                for t in eligible
                for k, v in t.model_dump().items()
                if v is not None and k not in ("id", "category", "phase")
            }
        ),
    )
    print(
        "sample eligible[0]:",
        eligible[0].model_dump() if eligible else None,
    )
    try:
        result = run_question_generation(
            QuestionGenerationInput(
                prompt_name=_PHASE,
                prioritised_topics=topics,
                eligible_targets=eligible,
                context=context,
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR QG: {exc}")
        return []

    print("qg reason:", result.reason)
    print("qg questions:")
    print(_dump(result.questions))
    print(f"{label} options brief:", _options_brief(result.questions))
    print()
    return result.questions


def _run() -> int:
    print("=== QG stripped-hints exploratory probe ===\n")
    print(
        "Registry topic ids still passed. Stripped from B only: "
        "clinical_hint, example_prompt, suggested_options.\n"
        "Note: Devise already excludes example_prompt/suggested_options; "
        "this probe targets QG option invention.\n"
    )

    state = _classify_and_apply(_state(_ELIQUIS_TEXT))
    context = build_agent_context(state)
    print("known_collect_values:", context.get("known_collect_values"))
    print()

    topics = run_devise_and_prioritise(_PHASE, context)
    print("devise topics (shared input to both QG runs):")
    print(_dump(topics))
    print()

    full = get_eligible_targets("priority", context.get("patient_sex"))
    stripped = _strip_targets(full)

    q_full = _run_qg("A_qg_full_registry_hints", topics, full, context)
    q_stripped = _run_qg("B_qg_ids_only_no_suggestions", topics, stripped, context)

    print("--- comparison notes (human) ---")
    by_full = {q.collect_target_id or q.id: q for q in q_full}
    by_strip = {q.collect_target_id or q.id: q for q in q_stripped}
    shared = sorted(set(by_full) & set(by_strip))
    diffs = []
    for tid in shared:
        a = [o.value for o in (by_full[tid].options or [])]
        b = [o.value for o in (by_strip[tid].options or [])]
        diffs.append(
            {
                "target": tid,
                "full_options": a,
                "stripped_options": b,
                "options_identical": a == b,
                "full_prompt": by_full[tid].prompt,
                "stripped_prompt": by_strip[tid].prompt,
                "prompt_identical": by_full[tid].prompt == by_strip[tid].prompt,
            }
        )
    print(_dump(diffs))
    print(
        "Interpretation: does stripping suggested_options/example_prompt "
        "yield more tailored options (e.g. anticoagulant-aware meds), or "
        "does the model still converge on the same Panadol/Ibuprofen-style "
        "lists from prior knowledge / prompt examples?"
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
