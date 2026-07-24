"""localised_detail — body_diagram SVG tap, then severity + adaptive duration."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine import agent_bridge
from engine.session_state_mappers import map_patient_answers
from engine.helpers.completed_phases import with_completed
from engine.helpers.next_step import build_body_diagram_next_step, build_next_step
from engine.helpers.state_codecs import as_question_fields, dump_question_fields
from catalogues.body_diagram import resolve_prefill_candidates
from schemas.clinical_ai_io import LocalisedAnatomySite
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState

_PHASE = "localised_detail"
_DURATION_PHASE = "duration"


def _severity_question() -> QuestionField:
    return QuestionField(
        id="loc_severity",
        kind="single_choice",
        prompt="How severe is the pain right now? (0 = none, 10 = worst)",
        personalization_note="deterministic",
        collect_target_id="severity_score",
        options=[
            QuestionOption(value=str(i), label=str(i)) for i in range(0, 11)
        ],
    )


def _generate_detail_questions(state: SessionState) -> list[QuestionField]:
    """Round 2 — severity (deterministic) + duration (QG, adaptive chips)."""
    _topics, duration_qs = agent_bridge.devise_then_generate(
        _DURATION_PHASE, state, devise=False
    )
    return [_severity_question(), *duration_qs]


def _arm_body_diagram(state: SessionState) -> Command:
    raw_sites = (state.presenting_complaint_hint or {}).get(
        "localisedAnatomySites"
    ) or []
    sites: list[LocalisedAnatomySite] = []
    if isinstance(raw_sites, list):
        for item in raw_sites:
            if isinstance(item, dict):
                sites.append(LocalisedAnatomySite.model_validate(item))
    prefill = resolve_prefill_candidates(sites, state.patient_sex)
    return Command(
        update={
            "pending_diagram_file": prefill.diagram_file if prefill else None,
            "pending_highlighted_regions": (
                list(prefill.highlighted_region_ids) if prefill else []
            ),
            "awaiting_phase": _PHASE,
        },
        goto="localised_detail",
    )


def localised_detail(state: SessionState) -> Command:
    # --- Round 1: SVG body diagram (gate = empty body_structures) ---
    if not state.body_structures:
        if state.awaiting_phase != _PHASE:
            return _arm_body_diagram(state)

        next_step = build_body_diagram_next_step(state)
        answer = interrupt(next_step.model_dump())
        updates = map_patient_answers(state, answer, [])
        return Command(
            update={
                **updates,
                "pending_diagram_file": None,
                "pending_highlighted_regions": None,
                "awaiting_phase": None,
            },
            goto="localised_detail",
        )

    # --- Round 2: severity + adaptive duration ---
    if not state.pending_questions:
        return Command(
            update={
                "pending_questions": dump_question_fields(
                    _generate_detail_questions(state)
                ),
                "awaiting_phase": _PHASE,
            },
            goto="localised_detail",
        )

    questions = as_question_fields(state.pending_questions)
    answer = interrupt(
        build_next_step(state, questions, phase=_PHASE).model_dump()
    )
    updates = map_patient_answers(state, answer, questions)
    return Command(
        update={
            **updates,
            "pending_questions": [],
            "awaiting_phase": None,
            "completed_phases": with_completed(state, _PHASE),
        },
        goto="priority_questions",
    )
