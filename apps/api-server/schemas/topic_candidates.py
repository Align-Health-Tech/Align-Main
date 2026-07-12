"""TopicCandidate — Devise output / SessionState.prioritised_topics row."""
from typing import Literal, Optional

from pydantic import BaseModel

TopicSource = Literal["web_search", "base_reasoning"]


class TopicCandidate(BaseModel):
    topic: str
    relevance_score: float
    is_red_flag: bool
    source: TopicSource
    rationale: Optional[str] = None
