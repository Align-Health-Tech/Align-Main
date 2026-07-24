"""Local Azure smoke for priority_questions (Devise + QG). NOT for CI.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_priority_questions/smoke_priority_questions.py

Cases:
  1. Three known targets (onset + character + allergy) — all still asked
     with default_value / default_values (uniform prefill-and-confirm).
  2. Minimal localised complaint — no defaults populated.
  3. Female patient — pregnancy target eligible (registry sex rule).
  4. Wrist injury + Eliquis (apixaban) — base-reasoning ranking.

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
from intelligence.registry import (
    PRIORITY_TARGETS,
    get_eligible_targets,
)
from schemas.clinical_ai_io import ClassifierInput
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_PHASE = "priority_questions"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _state(
    text: str,
    *,
    patient_sex: str | None = "male",
) -> SessionState:
    return SessionState(
        session_id="smoke-priority",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex=patient_sex,
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


_MULTI_PREFILL_TARGETS = ("onset_circumstance", "character", "allergy")


def _questions_for_target(
    questions: list[QuestionField], target_id: str
) -> list[QuestionField]:
    tid = target_id.lower()
    out: list[QuestionField] = []
    for q in questions:
        if (q.collect_target_id or "").lower() == tid or q.id.lower() == tid:
            out.append(q)
            continue
        # Soft prompt match when model omits collect_target_id
        p = q.prompt.lower()
        if tid == "onset_circumstance" and (
            "happen" in p or "how did" in p or "onset" in q.id.lower()
        ):
            out.append(q)
        elif tid == "character" and (
            "feel" in p or "character" in q.id.lower() or "sharp" in p
        ):
            out.append(q)
        elif tid == "allergy" and ("allerg" in p or "allerg" in q.id.lower()):
            out.append(q)
    return out


def _has_prefill(q: QuestionField) -> bool:
    if q.default_value:
        return True
    if q.default_values:
        return True
    return False


def _seed_three_known(state: SessionState) -> SessionState:
    """Ensure onset + character + allergy are known before Devise+QG.

    Classifier may backfill onset from the complaint; character/allergy are
    seeded so the smoke isolates the QG prefill rule across categories.
    """
    updates: dict = {
        "character": [{"text": "Sharp", "source": "option"}],
        "intake_facts": [
            {
                "kind": "ALLERGY",
                "source": "PATIENT_INTAKE",
                "display": {"text": "penicillin", "source": "free_text"},
            }
        ],
    }
    if not state.onset_circumstance:
        updates["onset_circumstance"] = {
            "text": "I twisted it",
            "source": "free_text",
        }
    return state.model_copy(update=updates)


def _comorbid_other_ok(questions: list[QuestionField]) -> bool:
    """If a comorbidities multi_choice appears, require None of these, no Other."""
    for q in questions:
        is_comorbid = (
            q.collect_target_id == "comorbidities"
            or "comorbid" in q.id.lower()
            or "long-term" in q.prompt.lower()
            or "long term" in q.prompt.lower()
        )
        if not is_comorbid or q.kind != "multi_choice":
            continue
        vals = [o.value for o in (q.options or [])]
        if "Other" in vals:
            return False
        if "None of these" not in vals:
            return False
    return True


# Distinctive former bank lines — reject if echoed verbatim.
_LEGACY_EXAMPLE_PROMPTS_STRICT = {
    "Are you taking any medicines for your current symptoms?",
    "Are you currently being treated for any long-term conditions?",
    "Have you had any major surgeries or been in hospital for a serious condition before?",
    "Does anyone in your immediate family have any major ongoing health conditions?",
    "Have you tried anything yourself to manage this before coming in today?",
    "Which of the following currently apply to you?",
}
# Short natural English that matched old bank — warn only (not evidence of echo).
_LEGACY_EXAMPLE_PROMPTS_SOFT = {
    "Do you have any allergies?",
    "How does the pain feel?",
    "How did this happen?",
}


def _check_no_legacy_example_verbatim(
    questions: list[QuestionField],
) -> tuple[list[str], list[str]]:
    """Return (rejects, warns) for prompts matching former registry example_prompt."""
    pregnancy_ep = next(
        (t.example_prompt for t in PRIORITY_TARGETS if t.id == "pregnancy"),
        None,
    )
    rejects: list[str] = []
    warns: list[str] = []
    for q in questions:
        prompt = (q.prompt or "").strip()
        if not prompt:
            continue
        if q.collect_target_id == "pregnancy" and pregnancy_ep and prompt == pregnancy_ep:
            continue
        if prompt in _LEGACY_EXAMPLE_PROMPTS_STRICT:
            rejects.append(
                f"{q.collect_target_id or q.id}: verbatim legacy example_prompt {prompt!r}"
            )
        elif prompt in _LEGACY_EXAMPLE_PROMPTS_SOFT:
            warns.append(
                f"{q.collect_target_id or q.id}: natural phrasing equals old "
                f"example_prompt {prompt!r} (not treated as bank echo)"
            )
    return rejects, warns


def _print_devise_brief(topics: list[TopicCandidate]) -> None:
    print(
        "devise ranking brief:",
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


def _run() -> int:
    print("=== priority_questions Azure smoke ===\n")
    failures = 0

    # --- Case 1: onset + character + allergy all known → all 3 prefill ---
    print("--- case 1: three_known_targets_prefill ---")
    text1 = (
        "twisted my wrist playing tennis yesterday — sharp pain; "
        "I'm allergic to penicillin"
    )
    state1 = _seed_three_known(_classify_and_apply(_state(text1, patient_sex="male")))
    ctx1 = build_agent_context(state1)
    print("known_collect_values:", ctx1["known_collect_values"])
    for tid in _MULTI_PREFILL_TARGETS:
        if tid not in ctx1["known_collect_values"]:
            print(f"REJECTED: seed failed — {tid} missing from known_collect_values")
            failures += 1
    try:
        topics1, questions1 = devise_then_generate(_PHASE, state1)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR devise_then_generate: {exc}")
        failures += 1
        topics1, questions1 = [], []
    else:
        print("devise topics:")
        print(_dump(topics1))
        print("qg questions:")
        print(_dump(questions1))
        prefill_report: list[dict] = []
        for tid in _MULTI_PREFILL_TARGETS:
            qs = _questions_for_target(questions1, tid)
            if not qs:
                print(
                    f"REJECTED: {tid} known but question absent "
                    "(must prefill-and-confirm, not exclude)"
                )
                failures += 1
                continue
            prefills = [q for q in qs if _has_prefill(q)]
            if not prefills:
                print(
                    f"REJECTED: {tid} question present but no "
                    "default_value/default_values (model-following gap)"
                )
                failures += 1
            else:
                prefill_report.append(
                    {
                        "target": tid,
                        "id": prefills[0].id,
                        "default_value": prefills[0].default_value,
                        "default_values": prefills[0].default_values,
                    }
                )
        if len(prefill_report) == len(_MULTI_PREFILL_TARGETS):
            print("case1 all 3 targets prefilled OK:", prefill_report)
        else:
            print(
                f"case1 partial prefill ({len(prefill_report)}/"
                f"{len(_MULTI_PREFILL_TARGETS)}):",
                prefill_report,
            )
        if not _comorbid_other_ok(questions1):
            print(
                "REJECTED: comorbidities multi_choice used Other "
                "or missing None of these"
            )
            failures += 1
        rejects, warns = _check_no_legacy_example_verbatim(questions1)
        for reason in rejects:
            print(f"REJECTED: {reason}")
            failures += 1
        for reason in warns:
            print(f"WARN: {reason}")
        for q in questions1:
            if q.en_prompt is not None or any(
                o.en_label is not None for o in (q.options or [])
            ):
                print(f"REJECTED: en_* set on {q.id} while session=en")
                failures += 1
    print()

    # --- Case 2: minimal detail — no defaults ---
    print("--- case 2: minimal_no_prefill ---")
    text2 = "my wrist hurts"
    state2 = _classify_and_apply(_state(text2, patient_sex="male"))
    ctx2 = build_agent_context(state2)
    print("known_collect_values:", ctx2["known_collect_values"])
    try:
        topics2, questions2 = devise_then_generate(_PHASE, state2)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR devise_then_generate: {exc}")
        failures += 1
    else:
        print("devise topics:")
        print(_dump(topics2))
        print("qg questions:")
        print(_dump(questions2))
        prefills = [q.id for q in questions2 if _has_prefill(q)]
        if prefills and not ctx2["known_collect_values"]:
            print(f"REJECTED: unexpected prefills with empty known values: {prefills}")
            failures += 1
        else:
            print("case2: no spurious prefills OK" if not prefills else "case2: prefills match known only")
        pool_ids = {
            t.id
            for t in get_eligible_targets(
                "priority",
                ctx2.get("patient_sex"),
                ctx2.get("presentation_category"),
            )
        }
        print("eligible pool ids:", sorted(pool_ids))
        if "pregnancy" in pool_ids:
            print("REJECTED: pregnancy in pool for male")
            failures += 1
        if ctx2.get("presentation_category") == "LOCALISED" and "onset_circumstance" not in pool_ids:
            print("REJECTED: onset_circumstance missing from LOCALISED pool")
            failures += 1
        rejects, warns = _check_no_legacy_example_verbatim(questions2)
        for reason in rejects:
            print(f"REJECTED: {reason}")
            failures += 1
        for reason in warns:
            print(f"WARN: {reason}")
    print()

    # --- Case 3: female — pregnancy eligible ---
    print("--- case 3: female_pregnancy_eligible ---")
    text3 = "sore throat and feeling run down"
    state3 = _classify_and_apply(_state(text3, patient_sex="female"))
    ctx3 = build_agent_context(state3)
    pool_f = {
        t.id
        for t in get_eligible_targets(
            "priority",
            "female",
            ctx3.get("presentation_category"),
        )
    }
    print(
        "eligible pool (female,",
        ctx3.get("presentation_category"),
        "):",
        sorted(pool_f),
    )
    if "pregnancy" not in pool_f:
        print("REJECTED: pregnancy missing from female pool")
        failures += 1
    if (
        ctx3.get("presentation_category") == "NOT_LOCALISED"
        and "onset_circumstance" in pool_f
    ):
        print(
            "REJECTED: onset_circumstance in NOT_LOCALISED pool "
            "(locality hard rule)"
        )
        failures += 1
    try:
        topics3, questions3 = devise_then_generate(_PHASE, state3)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR devise_then_generate: {exc}")
        failures += 1
    else:
        print("devise topics:")
        print(_dump(topics3))
        print("qg questions:")
        print(_dump(questions3))
        rejects, warns = _check_no_legacy_example_verbatim(questions3)
        for reason in rejects:
            print(f"REJECTED: {reason}")
            failures += 1
        for reason in warns:
            print(f"WARN: {reason}")
        preg_topics = [t.topic for t in topics3 if t.topic == "pregnancy"]
        preg_qs = [
            q
            for q in questions3
            if q.collect_target_id == "pregnancy" or "pregnant" in q.prompt.lower()
        ]
        print("pregnancy in devise:", bool(preg_topics), "in QG:", bool(preg_qs))
        # Soft: model may defer pregnancy on low relevance; pool eligibility is hard.
        if preg_qs:
            print("case3: pregnancy question present OK")
        else:
            print(
                "WARN: pregnancy eligible but not selected this turn "
                "(acceptable if budget/relevance deferred it)"
            )
        if any(t.topic == "onset_circumstance" for t in topics3):
            print(
                "REJECTED: onset_circumstance devised for NOT_LOCALISED "
                "(should be hard-excluded from pool)"
            )
            failures += 1
    print()

    # --- Case 4: wrist + Eliquis — base-reasoning ranking ---
    print("--- case 4: wrist_eliquis_base_reasoning ---")
    text4 = (
        "Hurt my wrist yesterday after a fall, still swollen and bruised. "
        "I'm on Eliquis (apixaban) for a heart condition."
    )
    state4 = _classify_and_apply(_state(text4, patient_sex="male"))
    print("known_collect_values:", build_agent_context(state4)["known_collect_values"])
    try:
        topics4, questions4 = devise_then_generate(_PHASE, state4)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR devise_then_generate: {exc}")
        failures += 1
        topics4, questions4 = [], []
    else:
        print("devise topics:")
        print(_dump(topics4))
        _print_devise_brief(topics4)
        print("qg questions:")
        print(_dump(questions4))
        rejects, warns = _check_no_legacy_example_verbatim(questions4)
        for reason in rejects:
            print(f"REJECTED: {reason}")
            failures += 1
        for reason in warns:
            print(f"WARN: {reason}")
        med_rank = next(
            (i for i, t in enumerate(topics4) if t.topic == "medication"), None
        )
        comorb_rank = next(
            (i for i, t in enumerate(topics4) if t.topic == "comorbidities"), None
        )
        print(
            "case4 ranking notes:",
            {
                "medication_rank_index": med_rank,
                "comorbidities_rank_index": comorb_rank,
                "sources": sorted({t.source for t in topics4}),
            },
        )
        if any(t.source != "base_reasoning" for t in topics4):
            print("REJECTED: devise emitted a non-base_reasoning source")
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
