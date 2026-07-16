"""Local Azure smoke for nurse_review summary (single agent). NOT for CI.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_nurse_review/smoke_nurse_review.py

Cases:
  1. Full localised wrist — no raised flags; expect clinician shorthand.
  2. Same base + raised red flag — flag must be prominent in summary.
  3. NOT_LOCALISED systemic — empty body_structures; no awkward filler.

Also confirms review node stays silent (goto complete, no interrupt) via
static import check — Azure path is the agent call only.

Results under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt``.
"""
from __future__ import annotations

import inspect
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
    run_nurse_review_summary_agent,
)
from engine.nodes import review as review_mod
from schemas.session_states import SessionState

_RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _base_localised_wrist(**overrides) -> SessionState:
    data = dict(
        session_id="smoke-nurse-review",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="male",
        chief_complaint={
            "text": "Twisted my right wrist playing tennis yesterday",
            "source": "free_text",
        },
        presentation_category="LOCALISED",
        body_structures=[
            {
                "structure_type": "PRIMARY",
                "coding": {
                    "system": "http://snomed.info/sct",
                    "code": "8205005",
                    "display": "Wrist region structure",
                },
                "laterality": "RIGHT",
                "severity_score": 5,
            }
        ],
        onset_circumstance={
            "text": "Twisted playing tennis yesterday",
            "source": "free_text",
        },
        character=[{"text": "Sharp", "source": "option"}],
        severity_score=5,
        functional_impact_score=4,
        encounter_medication=[
            {"text": "ibuprofen PRN", "source": "free_text"}
        ],
        intake_facts=[
            {
                "kind": "ALLERGY",
                "display_name": "penicillin",
                "source": "patient",
            }
        ],
        raised_flag_topics=[],
        ice_idea={"text": "maybe a sprain", "source": "free_text"},
        ice_concern={"text": "worried about a fracture", "source": "free_text"},
        ice_expectation={
            "text": "want an x-ray and advice",
            "source": "free_text",
        },
        completed_phases=[
            "presenting_complaint",
            "localised_detail",
            "priority_questions",
            "redflag_screening",
            "optional_questions",
            "ice",
        ],
    )
    data.update(overrides)
    return SessionState(**data)


def _case_not_localised() -> SessionState:
    return SessionState(
        session_id="smoke-nurse-review-nl",
        patient_id="p",
        organization_id="o",
        session_language="en",
        patient_sex="female",
        chief_complaint={
            "text": "Fever, fatigue and body aches for three days",
            "source": "free_text",
        },
        presentation_category="NOT_LOCALISED",
        non_localised_category="SYSTEMIC",
        body_structures=[],
        duration={"text": "3 days", "source": "option"},
        severity_score=6,
        functional_impact_score=7,
        raised_flag_topics=[],
        intake_facts=[
            {
                "kind": "PAST_HISTORY",
                "display_name": "asthma",
                "source": "patient",
            }
        ],
        ice_idea={"text": "viral illness", "source": "free_text"},
        ice_concern={"text": "worried it is something worse", "source": "free_text"},
        ice_expectation={"text": "check and advice", "source": "free_text"},
        completed_phases=[
            "presenting_complaint",
            "non_localised_detail",
            "priority_questions",
            "redflag_screening",
            "optional_questions",
            "ice",
        ],
    )


def _assert_silent_review_node() -> str:
    src = inspect.getsource(review_mod.review)
    checks = []
    if "interrupt" in src:
        checks.append("FAIL: review() still references interrupt")
    else:
        checks.append("OK: review() has no interrupt")
    if 'goto="complete"' in src or "goto='complete'" in src:
        checks.append('OK: review() goto="complete"')
    else:
        checks.append("FAIL: review() does not goto complete")
    if "build_next_step" in src:
        checks.append("FAIL: review() builds a NextStep (patient-facing)")
    else:
        checks.append("OK: review() does not build NextStep")
    return "\n".join(checks)


def _run_case(label: str, state: SessionState) -> dict:
    ctx = build_agent_context(state)
    result = run_nurse_review_summary_agent(ctx)
    return {
        "label": label,
        "context_keys": sorted(ctx.keys()),
        "raised_flag_topics": ctx.get("raised_flag_topics"),
        "body_structures_len": len(ctx.get("body_structures") or []),
        "presentation_category": ctx.get("presentation_category"),
        "raw": result.model_dump(by_alias=True),
        "summary": result.summary,
    }


def main() -> int:
    buf = StringIO()
    with redirect_stdout(buf):
        print("=== silent review node (static) ===")
        print(_assert_silent_review_node())
        print()

        cases = [
            (
                "1. Full localised wrist (no red flags)",
                _base_localised_wrist(),
            ),
            (
                "2. Localised wrist + raised red flag",
                _base_localised_wrist(
                    raised_flag_topics=["Chest pain at rest"],
                ),
            ),
            (
                "3. NOT_LOCALISED systemic (empty body_structures)",
                _case_not_localised(),
            ),
        ]

        outputs = []
        for label, state in cases:
            print(f"=== {label} ===")
            try:
                out = _run_case(label, state)
                outputs.append(out)
                print(json.dumps(out, indent=2, default=str))
            except Exception as exc:  # noqa: BLE001 — smoke report
                print(f"ERROR: {exc!r}")
                outputs.append({"label": label, "error": repr(exc)})
            print()

        print("=== tone / flag checks (human) ===")
        for out in outputs:
            if "error" in out:
                print(f"- {out['label']}: ERROR")
                continue
            s = out["summary"] or ""
            patientish = any(
                p in s.lower()
                for p in (
                    "don't worry",
                    "do not worry",
                    "you'll be",
                    "you will be",
                    "please rest assured",
                    "we understand",
                )
            )
            print(f"- {out['label']}")
            print(f"  summary: {s}")
            print(f"  patient-facing reassurance phrases: {'YES' if patientish else 'no'}")
            if out.get("raised_flag_topics"):
                flag = out["raised_flag_topics"][0]
                print(
                    f"  raised flag reflected: "
                    f"{'likely' if flag.lower() in s.lower() or 'chest' in s.lower() else 'CHECK MANUALLY'} "
                    f"(topic={flag!r})"
                )
            if out.get("presentation_category") == "NOT_LOCALISED":
                awkward = "body structures" in s.lower() and (
                    "none" in s.lower() or "empty" in s.lower()
                )
                print(f"  awkward body_structures filler: {'YES' if awkward else 'no'}")

    text = buf.getvalue()
    path = next_result_path(_RESULTS_DIR, prefix="results")
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
