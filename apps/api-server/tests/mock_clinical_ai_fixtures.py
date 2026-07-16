"""Stable TopicCandidate / QuestionField fixtures for ClinicalAiMock (CI)."""
from __future__ import annotations

from schemas.question_fields import QuestionField
from schemas.topic_candidates import TopicCandidate

TOPICS_BY_PHASE: dict[str, list[TopicCandidate]] = {
    "presenting_complaint_clarify": [
        TopicCandidate(
            topic="location_or_nature",
            relevance_score=0.85,
            is_red_flag=False,
            source="base_reasoning",
            rationale="mock clarify",
        )
    ],
    "non_localised_clarify": [
        TopicCandidate(
            topic="systemic_nature",
            relevance_score=0.8,
            is_red_flag=False,
            source="base_reasoning",
        )
    ],
    "priority_questions": [
        TopicCandidate(
            topic="medication",
            relevance_score=0.9,
            is_red_flag=False,
            source="base_reasoning",
        )
    ],
    "redflag_screening": [
        TopicCandidate(
            topic="chest_pain",
            relevance_score=0.95,
            is_red_flag=True,
            source="base_reasoning",
        ),
        TopicCandidate(
            topic="neurological_deficit",
            relevance_score=0.7,
            is_red_flag=True,
            source="base_reasoning",
        ),
    ],
    "optional_questions": [
        TopicCandidate(
            topic="self_management",
            relevance_score=0.5,
            is_red_flag=False,
            source="base_reasoning",
        )
    ],
}

QUESTIONS_BY_PHASE: dict[str, list[QuestionField]] = {
    "priority_questions": [
        QuestionField(
            id="meds_q1",
            kind="yes_no",
            prompt="Are you taking any medicines for your symptoms?",
            personalization_note="mock priority",
            collect_target_id="medication",
        )
    ],
    "redflag_screening": [
        QuestionField(
            id="rf_chest_pain",
            kind="yes_no",
            prompt="Do you have chest pain or pressure?",
            personalization_note="mock redflag",
            collect_target_id="chest_pain",
        ),
        QuestionField(
            id="rf_neuro",
            kind="yes_no",
            prompt="Any sudden weakness, numbness, or vision loss?",
            personalization_note="mock redflag",
            collect_target_id="neurological_deficit",
        ),
    ],
    "optional_questions": [
        QuestionField(
            id="opt_sleep",
            kind="yes_no",
            prompt="Have you tried anything yourself for this?",
            personalization_note="mock optional",
            collect_target_id="self_management",
            required=False,
        )
    ],
    "ice": [
        QuestionField(
            id="ice_idea",
            kind="free_text",
            prompt="What do you think is going on?",
            personalization_note="mock ice",
            collect_target_id="ice_idea",
        ),
        QuestionField(
            id="ice_concern",
            kind="free_text",
            prompt="What worries you most about this?",
            personalization_note="mock ice",
            collect_target_id="ice_concern",
        ),
        QuestionField(
            id="ice_expectation",
            kind="free_text",
            prompt="What are you hoping we can do today?",
            personalization_note="mock ice",
            collect_target_id="ice_expectation",
        ),
    ],
}
