"""TopicCandidate — Devise output / SessionState.prioritised_topics row.

``TopicSource`` lives in ``schemas.literals``.
"""

from typing import Optional

from pydantic import BaseModel, Field

from schemas.literals import TopicSource


class TopicCandidate(BaseModel):
    topic: str
    relevance_score: float
    is_red_flag: bool
    source: TopicSource
    rationale: Optional[str] = None
    evidence_urls: list[str] = Field(default_factory=list)
