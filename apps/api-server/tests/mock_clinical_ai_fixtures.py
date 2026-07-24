"""Stable TopicCandidate / QuestionField fixtures for ClinicalAiMock (CI)."""
from __future__ import annotations

from schemas.question_fields import QuestionField, QuestionOption
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
    "duration": [
        QuestionField(
            id="duration",
            kind="single_choice",
            prompt="How long have you had this?",
            personalization_note="mock duration",
            collect_target_id="duration",
            options=[
                QuestionOption(value="Last 24 hours", label="Last 24 hours"),
                QuestionOption(value="Within a week", label="Within a week"),
                QuestionOption(value="More than a week", label="More than a week"),
                QuestionOption(value="Other", label="Other"),
            ],
        )
    ],
    "ice": [
        QuestionField(
            id="ice_idea",
            kind="multi_choice",
            prompt="What do you think is going on?",
            personalization_note="mock ice",
            collect_target_id="ice_idea",
            options=[
                QuestionOption(value="Maybe a sprain", label="Maybe a sprain"),
                QuestionOption(value="I'm not sure", label="I'm not sure"),
                QuestionOption(value="Other", label="Other"),
            ],
        ),
        QuestionField(
            id="ice_concern",
            kind="multi_choice",
            prompt="What worries you most about this?",
            personalization_note="mock ice",
            collect_target_id="ice_concern",
            options=[
                QuestionOption(
                    value="Worried about a fracture",
                    label="Worried about a fracture",
                ),
                QuestionOption(value="I'm not sure", label="I'm not sure"),
                QuestionOption(value="Other", label="Other"),
            ],
        ),
        QuestionField(
            id="ice_expectation",
            kind="multi_choice",
            prompt="What are you hoping we can do today?",
            personalization_note="mock ice",
            collect_target_id="ice_expectation",
            options=[
                QuestionOption(value="Want an X-ray", label="Want an X-ray"),
                QuestionOption(value="Advice only", label="Advice only"),
                QuestionOption(value="Other", label="Other"),
            ],
        ),
    ],
}
