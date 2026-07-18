"""optional_questions answers → SessionState / intake_facts."""
from __future__ import annotations

from typing import Any

from engine.session_state_mappers.selections import (
    intake_fact_additions,
    join_narrative,
    merge_intake_facts,
    narrative_dumps,
    selections_for_target,
)
from schemas.literals import IntakeFactKind
from schemas.question_fields import QuestionField
from schemas.session_states import SessionState

# collect_target_id → intake_fact kind
_INTAKE_FACT_TARGETS: dict[str, IntakeFactKind] = {
    "past_history": "PAST_HISTORY",
    "family_history": "FAMILY_HISTORY",
    "social_history": "SOCIAL_HISTORY",
}


def map_optional_questions(
    state: SessionState,
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    """Map optional collect targets onto SessionState."""
    updates: dict[str, Any] = {}

    fact_additions = intake_fact_additions(
        state, questions, by_id, _INTAKE_FACT_TARGETS
    )
    if fact_additions:
        updates["intake_facts"] = merge_intake_facts(state, fact_additions)

    self_mgmt = selections_for_target(questions, by_id, "self_management")
    if self_mgmt is not None:
        updates["self_management"] = join_narrative(state, self_mgmt)

    weight = selections_for_target(questions, by_id, "weight_change")
    if weight is not None:
        updates["weight_change"] = (
            "; ".join(text for text, _ in weight) if weight else None
        )

    exacerbating = selections_for_target(questions, by_id, "exacerbating_factors")
    if exacerbating is not None:
        updates["exacerbating_factors"] = narrative_dumps(state, exacerbating)

    mitigating = selections_for_target(questions, by_id, "mitigating_factors")
    if mitigating is not None:
        updates["mitigating_factors"] = narrative_dumps(state, mitigating)

    return updates
