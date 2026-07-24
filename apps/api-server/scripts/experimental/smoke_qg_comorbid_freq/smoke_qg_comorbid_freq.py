"""Comorbidities option-frequency probe (stripped hints) — repetition, not self-report.

NOT for CI. Asks QG 5× per context to observe run-to-run variation.
Does NOT ask the model to explain itself.

Usage (from apps/api-server, Azure env set):

  ./venv/bin/python scripts/smoke_qg_comorbid_freq/smoke_qg_comorbid_freq.py

Conditions:
  A. wrist + Eliquis/heart (5 runs)
  B. same wrist injury, Eliquis/heart stripped from context (5 runs)
  C. unrelated sore throat, no heart (5 runs)

All QG calls: eligible_targets stripped of clinical_hint / example_prompt /
suggested_options. Devise topics fixed so comorbidities is always asked.

Results under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt``.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
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
)
from engine.session_state_mappers.ai import map_classifier_result
from intelligence.llm_client import run_agent
from intelligence.registry import get_eligible_targets
from schemas.clinical_ai_io import ClassifierInput, QuestionGenerationResult
from schemas.collect_targets import CollectTarget
from schemas.session_states import SessionState
from schemas.topic_candidates import TopicCandidate

_RESULTS_DIR = Path(__file__).resolve().parent / "results"
_PHASE = "priority_questions"
_RUNS = 5
_STRIPPED_KEEP = {"id", "category", "phase", "free_text_policy"}

_REGISTRY_COMORBID = {
    "Diabetes",
    "High blood pressure",
    "Asthma",
    "Heart conditions",
    "None of these",
}

# Fixed Devise list — comorbidities always present so option lists are comparable.
_FIXED_TOPICS = [
    TopicCandidate(
        topic="medication",
        relevance_score=0.9,
        is_red_flag=False,
        source="base_reasoning",
        rationale="fixed for probe",
    ),
    TopicCandidate(
        topic="comorbidities",
        relevance_score=0.85,
        is_red_flag=False,
        source="base_reasoning",
        rationale="fixed for probe",
    ),
    TopicCandidate(
        topic="onset_circumstance",
        relevance_score=0.7,
        is_red_flag=False,
        source="base_reasoning",
        rationale="fixed for probe",
    ),
]


def _state(text: str) -> SessionState:
    return SessionState(
        session_id="smoke-comorbid-freq",
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
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _classify(text: str) -> SessionState:
    state = _state(text)
    clf = run_classifier(
        ClassifierInput(
            prompt_name="presenting_complaint",
            conversation=conversation_from_state(state),
            context=build_agent_context(state),
        )
    )
    print(f"classifier ready={clf.ready} category={clf.category}")
    print("chiefComplaintSummary:", clf.chief_complaint_summary)
    print("supplement comorbidities:", None if not clf.encounter_intake_supplement else clf.encounter_intake_supplement.comorbidities)
    return state.model_copy(update=map_classifier_result(state, clf))


def _strip_heart_from_state(state: SessionState) -> SessionState:
    """Remove heart/Eliquis signals so known_collect_values has no heart comorbidity."""
    cc = state.chief_complaint
    if isinstance(cc, dict) and cc.get("text"):
        text = str(cc["text"])
        for frag in (
            "Eliquis",
            "eliquis",
            "apixaban",
            "heart condition",
            "Heart condition",
            "heart disease",
        ):
            text = text.replace(frag, "")
        text = re.sub(r"\s+", " ", text).strip(" .;")
        cc = {**cc, "text": text}
    return state.model_copy(
        update={
            "chief_complaint": cc,
            "comorbidities": None,
            "intake_facts": [
                f
                for f in (state.intake_facts or [])
                if "heart" not in str(f).lower() and "eliquis" not in str(f).lower()
            ],
        }
    )


def _strip_targets(targets: list[CollectTarget]) -> list[CollectTarget]:
    out: list[CollectTarget] = []
    for t in targets:
        data = t.model_dump(include=_STRIPPED_KEEP)
        data["clinical_hint"] = None
        data["example_prompt"] = None
        data["suggested_options"] = None
        out.append(CollectTarget.model_validate(data))
    return out


def _comorbid_options(result: QuestionGenerationResult) -> list[str] | None:
    for q in result.questions:
        if (q.collect_target_id or q.id) == "comorbidities":
            return [o.value for o in (q.options or [])]
        if "long-term" in q.prompt.lower() or "long term" in q.prompt.lower():
            return [o.value for o in (q.options or [])]
    return None


def _run_qg(context: dict, eligible: list[CollectTarget]) -> list[str] | None:
    result = run_agent(
        "question_generation",
        _PHASE,
        {
            "prioritised_topics": [t.model_dump() for t in _FIXED_TOPICS],
            "eligible_targets": [t.model_dump() for t in eligible],
            "max_questions": None,
            "context": context,
        },
        QuestionGenerationResult,
    )
    return _comorbid_options(result)


def _freq_table(runs: list[list[str]]) -> dict:
    flat = Counter()
    kidney_hits = 0
    heart_hits = 0
    novel_hits = Counter()
    for opts in runs:
        flat.update(opts)
        joined = " | ".join(opts).lower()
        if "kidney" in joined:
            kidney_hits += 1
        if "heart" in joined:
            heart_hits += 1
        for o in opts:
            if o not in _REGISTRY_COMORBID and o != "None of these":
                # "None of these" is registry; also allow exact registry set
                if o not in _REGISTRY_COMORBID:
                    novel_hits[o] += 1
    n = len(runs)
    return {
        "n_runs": n,
        "option_frequency": {
            k: {"count": v, "rate": round(v / n, 2)} for k, v in flat.most_common()
        },
        "kidney_in_list_rate": round(kidney_hits / n, 2) if n else None,
        "heart_in_list_rate": round(heart_hits / n, 2) if n else None,
        "novel_options_frequency": dict(novel_hits.most_common()),
        "per_run_options": runs,
    }


def _condition(label: str, state: SessionState, eligible: list[CollectTarget]) -> dict:
    print(f"\n===== {label} =====")
    context = build_agent_context(state)
    print("known_collect_values:", context.get("known_collect_values"))
    print("chief_complaint:", context.get("chief_complaint"))
    runs: list[list[str]] = []
    for i in range(1, _RUNS + 1):
        print(f"--- {label} run {i}/{_RUNS} ---")
        try:
            opts = _run_qg(context, eligible)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {exc}")
            opts = None
        if opts is None:
            print("WARN: no comorbidities question")
            runs.append([])
        else:
            print("comorbidities options:", opts)
            runs.append(opts)
    table = _freq_table(runs)
    print(f"{label} frequency:", _dump(table))
    return table


def _run() -> int:
    print("=== comorbidities stripped-hints frequency probe ===\n")
    print(f"QG model-default sampling runs_per_condition={_RUNS}")
    print("stripped: clinical_hint, example_prompt, suggested_options\n")

    eligible = _strip_targets(get_eligible_targets("priority", "male"))

    # A: wrist + Eliquis / heart
    text_a = (
        "Hurt my wrist yesterday after a fall, still swollen and bruised. "
        "I'm on Eliquis (apixaban) for a heart condition."
    )
    state_a = _classify(text_a)
    table_a = _condition("A_wrist_eliquis_heart", state_a, eligible)

    # B: same injury story, strip heart/Eliquis from complaint + known values
    text_b = "Hurt my wrist yesterday after a fall, still swollen and bruised."
    state_b = _strip_heart_from_state(_classify(text_b))
    table_b = _condition("B_wrist_no_heart", state_b, eligible)

    # C: unrelated, no heart
    text_c = "sore throat and feeling run down for a few days"
    state_c = _strip_heart_from_state(_classify(text_c))
    table_c = _condition("C_sore_throat_no_heart", state_c, eligible)

    print("\n===== SUMMARY (raw rates, no model self-explanation) =====")
    summary = {
        "A_wrist_eliquis_heart": {
            "kidney_rate": table_a["kidney_in_list_rate"],
            "heart_rate": table_a["heart_in_list_rate"],
            "novel": table_a["novel_options_frequency"],
            "top_options": list(table_a["option_frequency"].items())[:8],
        },
        "B_wrist_no_heart": {
            "kidney_rate": table_b["kidney_in_list_rate"],
            "heart_rate": table_b["heart_in_list_rate"],
            "novel": table_b["novel_options_frequency"],
            "top_options": list(table_b["option_frequency"].items())[:8],
        },
        "C_sore_throat_no_heart": {
            "kidney_rate": table_c["kidney_in_list_rate"],
            "heart_rate": table_c["heart_in_list_rate"],
            "novel": table_c["novel_options_frequency"],
            "top_options": list(table_c["option_frequency"].items())[:8],
        },
    }
    print(_dump(summary))

    # Gate check without asking the model
    kidney_a = table_a["kidney_in_list_rate"] or 0
    kidney_b = table_b["kidney_in_list_rate"] or 0
    kidney_c = table_c["kidney_in_list_rate"] or 0
    print(
        "\nInterpretation cues (automatic):",
        {
            "kidney_appears_when_heart_context": kidney_a,
            "kidney_when_wrist_no_heart": kidney_b,
            "kidney_when_sore_throat": kidney_c,
            "context_gated_kidney": kidney_a > 0
            and kidney_a > kidney_b
            and kidney_a > kidney_c,
            "kidney_regardless_of_context": kidney_a > 0
            and kidney_b > 0
            and kidney_c > 0,
        },
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
