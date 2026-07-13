"""localised_detail — Pattern A deterministic body / onset / severity."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.apply_answers import apply_answers
from engine.completed_phases import with_completed
from engine.next_step import build_next_step
from engine.state_codecs import as_question_fields, dump_question_fields
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState

_PHASE = "localised_detail"


def _generate_localised_questions(_state: SessionState) -> list[QuestionField]:
    regions = ["wrist", "ankle", "knee", "shoulder", "back", "other"]
    return [
        QuestionField(
            id="loc_region",
            kind="single_choice",
            prompt="Which area is most affected?",
            personalization_note="deterministic",
            collect_target_id="body_region",
            options=[QuestionOption(value=r, label=r.title()) for r in regions],
        ),
        QuestionField(
            id="loc_laterality",
            kind="single_choice",
            prompt="Which side?",
            personalization_note="deterministic",
            collect_target_id="laterality",
            options=[
                QuestionOption(value="left", label="Left"),
                QuestionOption(value="right", label="Right"),
                QuestionOption(value="bilateral", label="Both"),
            ],
        ),
        QuestionField(
            id="loc_severity",
            kind="single_choice",
            prompt="How severe is the pain right now? (0 = none, 10 = worst)",
            personalization_note="deterministic",
            collect_target_id="severity_score",
            options=[
                QuestionOption(value=str(i), label=str(i)) for i in range(0, 11)
            ],
        ),
        QuestionField(
            id="loc_onset",
            kind="free_text",
            prompt="How did this start?",
            personalization_note="deterministic",
            collect_target_id="onset_circumstance",
        ),
    ]


def localised_detail(state: SessionState) -> Command:
    if not state.pending_questions:
        return Command(
            update={
                "pending_questions": dump_question_fields(
                    _generate_localised_questions(state)
                ),
                "awaiting_phase": _PHASE,
            },
            goto="localised_detail",
        )

    questions = as_question_fields(state.pending_questions)
    answer = interrupt(
        build_next_step(state, questions, phase=_PHASE).model_dump()
    )
    updates = apply_answers(state, answer, questions)
    return Command(
        update={
            **updates,
            "pending_questions": [],
            "awaiting_phase": None,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="priority_questions",
    )
