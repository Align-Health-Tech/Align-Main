"""Convert nested domain models ↔ plain dicts for SessionState / checkpoints.

Why this exists: LangGraph checkpointers (MemorySaver, PostgresSaver) serialize
state with msgpack. Nested Pydantic instances (QuestionField, TopicCandidate,
NarrativeField, …) trigger "unregistered type" warnings and may be blocked
under strict settings. SessionState therefore stores only dict / list[dict].

Use dump_* before writing into SessionState (or Command updates).
Use as_* when engine code needs a typed Pydantic object again.
"""
from __future__ import annotations

from typing import Any

from schemas.question_fields import QuestionField
from schemas.topic_candidates import TopicCandidate


def as_question_fields(raw: list[dict[str, Any]]) -> list[QuestionField]:
    return [QuestionField.model_validate(item) for item in raw]


def dump_question_fields(questions: list[QuestionField]) -> list[dict[str, Any]]:
    return [q.model_dump() for q in questions]


# Re-hydrate TopicCandidate list after Devise writes prioritised_topics as dicts
def as_topic_candidates(raw: list[dict[str, Any]]) -> list[TopicCandidate]:
    return [TopicCandidate.model_validate(item) for item in raw]


def dump_topic_candidates(topics: list[TopicCandidate]) -> list[dict[str, Any]]:
    return [t.model_dump() for t in topics]
