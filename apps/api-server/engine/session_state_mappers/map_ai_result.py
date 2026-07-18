"""Map AI agent results onto SessionState field updates.

Counterpart to ``map_patient_answers``: nodes call this after an agent
returns (classifier / nurse review). Does not call the LLM — only
"result model → partial state dict".

AI-specific mappers live under ``ai/``.
"""
from __future__ import annotations

from typing import Any

from engine.session_state_mappers.ai.classifier_result import (
    map_classifier_result,
)
from engine.session_state_mappers.ai.nurse_review import map_nurse_review
from schemas.clinical_ai_io import ClassifierResult, ReviewSummaryResult
from schemas.session_states import SessionState


def map_ai_result(
    state: SessionState,
    result: ClassifierResult | ReviewSummaryResult,
    *,
    prompt_name: str = "presenting_complaint",
) -> dict[str, Any]:
    """Dispatch by result type to the matching AI mapper.

    - ``ClassifierResult`` — ``prompt_name`` selects PC vs NL categoriser mapping.
    - ``ReviewSummaryResult`` — writes ``encounter_summary``.
    """
    if isinstance(result, ClassifierResult):
        return map_classifier_result(
            state, result, prompt_name=prompt_name
        )
    if isinstance(result, ReviewSummaryResult):
        return map_nurse_review(state, result)
    raise TypeError(
        f"unsupported AI result type: {type(result)!r}"
    )
