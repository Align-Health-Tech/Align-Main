"""Build NextStep payloads for interrupt / GET rebuild / router forms."""
from __future__ import annotations

from engine.helpers.state_codecs import as_question_fields
from schemas.literals import Phase, StepType
from schemas.question_fields import NextStep, QuestionField
from schemas.session_states import SessionState


def _step_type_for_phase(phase: Phase) -> StepType:
    if phase == "consent":
        return "consent"
    if phase == "survey":
        return "survey"
    return "question_batch"


def build_next_step_raw(
    turn_number: int,
    questions: list[QuestionField],
    *,
    phase: Phase,
) -> NextStep:
    """Construct NextStep without a SessionState (e.g. pre-graph consent)."""
    return NextStep(
        step_type=_step_type_for_phase(phase),
        phase=phase,
        turn_number=turn_number,
        questions=questions,
    )


def build_next_step(
    state: SessionState,
    questions: list[QuestionField],
    *,
    phase: Phase,
) -> NextStep:
    return build_next_step_raw(state.turn_number, questions, phase=phase)


def build_body_diagram_next_step(state: SessionState) -> NextStep:
    return NextStep(
        step_type="body_diagram",
        phase="localised_detail",
        turn_number=state.turn_number,
        diagram_file=state.pending_diagram_file,
        highlighted_region_ids=state.pending_highlighted_regions,
    )


def next_step_from_state(state: SessionState) -> NextStep | None:
    if state.is_session_complete:
        return NextStep(
            step_type="complete",
            # Last in-graph patient phase; survey (if any) is router-level.
            phase="ice",
            turn_number=state.turn_number,
        )
    # Mid-await body_diagram (no pending_questions — SVG interrupt)
    if (
        state.awaiting_phase == "localised_detail"
        and not state.body_structures
        and state.pending_highlighted_regions is not None
    ):
        return build_body_diagram_next_step(state)
    if state.awaiting_phase is None or not state.pending_questions:
        return None
    return build_next_step(
        state,
        as_question_fields(state.pending_questions),
        phase=state.awaiting_phase,
    )
