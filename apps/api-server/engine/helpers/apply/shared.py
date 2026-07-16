"""Shared constants/helpers for apply_* modules."""
from __future__ import annotations

from typing import Any

from schemas.question_fields import QuestionField

_YES = frozenset({True, "yes", "true", "accepted", "Yes", "True"})


def values_by_target(
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for q in questions:
        if q.collect_target_id is None:
            continue
        if q.id not in by_id:
            continue
        out[q.collect_target_id] = by_id[q.id]
    return out


def messages_from_answers(
    questions: list[QuestionField],
    by_id: dict[str, Any],
) -> dict[str, Any]:
    new_msgs: list[dict[str, str]] = []
    for q in questions:
        val = by_id.get(q.id)
        if val is None or val == "":
            continue
        text = val if isinstance(val, str) else str(val)
        new_msgs.append({"role": "user", "content": f"{q.prompt} {text}"})
    if not new_msgs:
        return {}
    return {"messages": new_msgs}
