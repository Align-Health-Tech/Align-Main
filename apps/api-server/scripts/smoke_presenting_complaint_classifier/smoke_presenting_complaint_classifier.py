"""Local Azure smoke for classifier/presenting_complaint (NOT for CI).

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_presenting_complaint_classifier/smoke_presenting_complaint_classifier.py

Requires: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_MODEL_NAME

Builds the same ClassifierInput shape as ``presenting_complaint`` node:
``conversation_from_state`` + ``build_agent_context``.

Results are appended under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt``
(never overwrites prior runs).
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
from engine.helpers.agent_bridge import (
    build_agent_context,
    conversation_from_state,
    run_classifier,
)
from engine.static.body_diagram_catalogue import resolve_prefill_candidates
from schemas.clinical_ai_io import ClassifierInput, ClassifierResult
from schemas.session_states import SessionState

CASES: list[tuple[str, str]] = [
    ("localised_wrist", "sharp pain in my right wrist"),
    ("systemic_fever", "fever and feeling generally unwell"),
    ("vague_hurts", "something hurts"),
]

_RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _state_for(text: str) -> SessionState:
    """Mirror post–Stage-1 state: chief_complaint set, messages seeded."""
    return SessionState(
        session_id="smoke-pc-classifier",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="female",
        chief_complaint={"text": text, "source": "free_text"},
        messages=[{"role": "user", "content": text}],
    )


def _run_one(text: str) -> ClassifierResult:
    state = _state_for(text)
    return run_classifier(
        ClassifierInput(
            prompt_name="presenting_complaint",
            conversation=conversation_from_state(state),
            context=build_agent_context(state),
        )
    )


def _run() -> int:
    print("=== presenting_complaint classifier Azure smoke ===\n")
    failures = 0
    for label, text in CASES:
        print(f"--- case: {label} ---")
        print(f"input: {text!r}")
        ctx = build_agent_context(_state_for(text))
        print(
            "context keys:",
            sorted(ctx.keys()),
            "| chief_complaint:",
            ctx.get("chief_complaint"),
        )
        try:
            result = _run_one(text)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {exc}")
            print()
            failures += 1
            continue

        raw = result.model_dump(mode="json", by_alias=True)
        print("raw ClassifierResult:")
        print(json.dumps(raw, indent=2, ensure_ascii=False))

        if "clarifyingQuestions" in raw or "assistantMessage" in raw:
            print("WARN: legacy clarify fields present on dump")
        if "extra" in raw and raw["extra"]:
            print("WARN: unexpected extra field populated")

        if result.ready:
            if not result.chief_complaint_summary:
                print("WARN: ready=true but chiefComplaintSummary missing")
                failures += 1
            else:
                print(
                    "chiefComplaintSummary:",
                    result.chief_complaint_summary,
                )

        if result.ready and result.category == "LOCALISED":
            sites = result.localised_anatomy_sites or []
            prefill = resolve_prefill_candidates(sites, patient_sex="female")
            print(
                "prefill:",
                None
                if prefill is None
                else {
                    "diagram_file": prefill.diagram_file,
                    "highlighted_region_ids": prefill.highlighted_region_ids,
                },
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
