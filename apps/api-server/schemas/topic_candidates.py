"""
TopicCandidate — the output shape of ClinicalReasoningProvider.get_topics()
(external_systems/clinical_reasoning/). Shared contract: our fallback
implementation and David/Kevin's engine both need to satisfy this exact
shape, since SessionState.prioritised_topics is typed against it regardless
of which provider produced it.

Red flag handling is deliberately simple for the demo — `is_red_flag` is a
flat boolean, not a confidence-scored sub-question chain with synthesis
logic. Revisit if the demo needs the more elaborate pattern later.

`is_red_flag` is set exactly once, here, during devise_and_prioritise's
initial pass (right after presenting complaint / body diagram — before any
priority questions are asked). The later `redflag_screening` phase doesn't
independently detect anything; it just pulls whatever candidates already
have `is_red_flag=True` and asks about those specifically as their own
batch, then writes `Flag` rows once confirmed. One detection point, one
later consumer — not two separate red-flag mechanisms.
"""
from typing import Literal, Optional

from pydantic import BaseModel

# "pathway" removed — not using health-pathway lookup for now. Fallback
# provider only uses web search + base LLM reasoning.
TopicSource = Literal["web_search", "base_reasoning"]


class TopicCandidate(BaseModel):
    topic: str
    relevance_score: float
    is_red_flag: bool
    source: TopicSource
    rationale: Optional[str] = None