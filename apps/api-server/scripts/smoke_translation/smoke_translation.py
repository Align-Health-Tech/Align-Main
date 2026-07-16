"""Local Azure smoke for Pattern E translation (to_english). NOT for CI.

Usage (from apps/api-server, with Azure env set):

  ./venv/bin/python scripts/smoke_translation/smoke_translation.py

Verifies real ``translate_to_english`` (not the ``[en] …`` fake) across the
same apply paths prior M5 slices only exercised with mocks:

  1. Direct agent calls (Korean clinical phrases + already-English + empty)
  2. presenting_complaint free-text chief complaint (session_language=ko)
  3. priority allergy Other free text
  4. optional past_history Other + self_management free text
  5. ice idea / concern / expectation free text
  6. Control: English session must not set en_text / must not need Azure
     for option chips

Results under ``./results/vNNN_results_YYYY-MM-DD_HHMMSS.txt``.
"""
from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _smoke_results import next_result_path
from engine.helpers.agent_bridge import translate_to_english
from engine.helpers.apply import apply_answers
from engine.helpers.translate import narrative_dump_free_text, narrative_dump_option
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState

_RESULTS_DIR = Path(__file__).resolve().parent / "results"
_LANG = "ko"


def _state(**overrides) -> SessionState:
    data = dict(
        session_id="smoke-translation",
        patient_id="p",
        organization_id="o",
        session_language=_LANG,
        patient_sex="male",
        presentation_category="LOCALISED",
        turn_number=2,
    )
    data.update(overrides)
    return SessionState(**data)


def _q(
    qid: str,
    *,
    kind: str = "free_text",
    collect_target_id: str,
    options: list[QuestionOption] | None = None,
) -> QuestionField:
    return QuestionField(
        id=qid,
        kind=kind,  # type: ignore[arg-type]
        prompt=f"smoke {qid}",
        personalization_note="smoke",
        collect_target_id=collect_target_id,
        required=False,
        options=options,
    )


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def _dump(label: str, obj) -> None:
    print(f"\n-- {label} --")
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _direct_cases() -> list[dict]:
    cases = [
        ("wrist injury", "어제 테니스 치다가 오른쪽 손목을 삐었어요. 아파요."),
        ("lower back", "허리가 쑤시고 다리가 찌릿해요."),
        ("already english", "NHI verified, ACC claim"),
        ("empty", ""),
    ]
    out = []
    for label, text in cases:
        result = translate_to_english(text, _LANG)
        out.append(
            {
                "label": label,
                "source_text": text,
                "raw": result.model_dump(),
            }
        )
    return out


def _phase_presenting_complaint() -> dict:
    state = _state(awaiting_phase="presenting_complaint", chief_complaint=None)
    questions = [
        _q("chief_complaint", collect_target_id="chief_complaint"),
    ]
    text = "어제 테니스 치다가 손목을 삐었어요"
    updates = apply_answers(
        state,
        {"answers": [{"question_id": "chief_complaint", "value": text}]},
        questions,
    )
    return {"phase": "presenting_complaint", "input": text, "updates": updates}


def _phase_priority_allergy() -> dict:
    state = _state(awaiting_phase="priority_questions")
    questions = [
        _q(
            "allergy",
            kind="multi_choice",
            collect_target_id="allergy",
            options=[
                QuestionOption(label="Penicillin", value="Penicillin"),
                QuestionOption(label="Other", value="Other"),
            ],
        )
    ]
    text = "땅콩 알레르기"
    updates = apply_answers(
        state,
        {
            "answers": [
                {"question_id": "allergy", "value": [f"Other:{text}"]}
            ]
        },
        questions,
    )
    return {"phase": "priority_questions/allergy", "input": text, "updates": updates}


def _phase_optional() -> dict:
    state = _state(awaiting_phase="optional_questions")
    questions = [
        _q(
            "past_history",
            kind="multi_choice",
            collect_target_id="past_history",
            options=[
                QuestionOption(label="Asthma", value="Asthma"),
                QuestionOption(label="Other", value="Other"),
            ],
        ),
        _q("self_management", collect_target_id="self_management"),
    ]
    past = "예전에 손목 골절 수술"
    self_mgmt = "이부프로펜 먹었어요"
    updates = apply_answers(
        state,
        {
            "answers": [
                {
                    "question_id": "past_history",
                    "value": [f"Other:{past}"],
                },
                {
                    "question_id": "self_management",
                    "value": self_mgmt,
                },
            ]
        },
        questions,
    )
    return {
        "phase": "optional_questions",
        "input": {"past_history": past, "self_management": self_mgmt},
        "updates": updates,
    }


def _phase_ice() -> dict:
    state = _state(awaiting_phase="ice")
    questions = [
        _q("ice_idea", collect_target_id="ice_idea"),
        _q("ice_concern", collect_target_id="ice_concern"),
        _q("ice_expectation", collect_target_id="ice_expectation"),
    ]
    answers = {
        "ice_idea": "염좌인 것 같아요",
        "ice_concern": "골절이 걱정돼요",
        "ice_expectation": "엑스레이 찍고 싶어요",
    }
    updates = apply_answers(
        state,
        {
            "answers": [
                {"question_id": k, "value": v} for k, v in answers.items()
            ]
        },
        questions,
    )
    return {"phase": "ice", "input": answers, "updates": updates}


def _english_control() -> dict:
    """English free text must not call Azure; option chips never translate."""
    calls = {"n": 0}

    def _blocked(*_a, **_k):
        calls["n"] += 1
        raise AssertionError("translate_to_english must not run for en session")

    with patch(
        "engine.helpers.translate.agent_bridge.translate_to_english",
        side_effect=_blocked,
    ):
        free = narrative_dump_free_text(
            "twisted my wrist", session_language="en"
        )
        option = narrative_dump_option("Sharp")
    return {
        "free_text_dump": free,
        "option_dump": option,
        "translate_calls": calls["n"],
        "ok": calls["n"] == 0 and free.get("en_text") is None,
    }


def main() -> int:
    buf = StringIO()
    with redirect_stdout(buf):
        _section("1. Direct translate_to_english (Korean)")
        for row in _direct_cases():
            _dump(row["label"], row)

        _section("2. Pattern E via apply — presenting_complaint")
        _dump("result", _phase_presenting_complaint())

        _section("3. Pattern E via apply — priority allergy Other")
        _dump("result", _phase_priority_allergy())

        _section("4. Pattern E via apply — optional past_history + self_management")
        _dump("result", _phase_optional())

        _section("5. Pattern E via apply — ice (3 fields)")
        _dump("result", _phase_ice())

        _section("6. English control (no Azure)")
        _dump("result", _english_control())

        print("\n=== human checks ===")
        print("- Korean sources must keep original text; en_text must be English")
        print("- No [en] fake prefix")
        print("- 허리 → lower back (not waist) preferred")
        print("- English session: en_text absent, zero translate calls")

    text = buf.getvalue()
    path = next_result_path(_RESULTS_DIR, prefix="results")
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
