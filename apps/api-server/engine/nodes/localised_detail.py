"""localised_detail — body_diagram SVG tap, then severity / onset questions."""
from __future__ import annotations

from langgraph.types import Command, interrupt

from engine.helpers.apply_answers import apply_answers
from engine.helpers.completed_phases import with_completed
from engine.helpers.next_step import build_body_diagram_next_step, build_next_step
from engine.helpers.state_codecs import as_question_fields, dump_question_fields
from engine.static.body_diagram_catalogue import resolve_prefill_candidates
from engine.static.onset_timing import (
    ONSET_TIMING_OPTIONS,
    onset_timing_default,
)
from schemas.clinical_ai_io import LocalisedAnatomySite
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState

_PHASE = "localised_detail"


def _generate_detail_questions(state: SessionState) -> list[QuestionField]:
    """Round 2 — no region/laterality MCQs (those come from SVG region_id)."""
    onset_default: str | None = None
    if isinstance(state.onset_circumstance, dict):
        text = state.onset_circumstance.get("text")
        if isinstance(text, str):
            onset_default = onset_timing_default(text)

    return [
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
            kind="single_choice",
            prompt="When did this start?",
            personalization_note="deterministic",
            collect_target_id="onset_circumstance",
            options=list(ONSET_TIMING_OPTIONS),
            default_value=onset_default,
        ),
    ]


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
    # Nothing earlier in the graph writes body_structures, so empty vs
    # non-empty cleanly separates "need tap" from "need severity/onset".
    if not state.body_structures:
        if state.awaiting_phase != _PHASE:
            return _arm_body_diagram(state)

        next_step = build_body_diagram_next_step(state)
        answer = interrupt(next_step.model_dump())
        updates = apply_answers(state, answer, [])
        return Command(
            update={
                **updates,
                "pending_diagram_file": None,
                "pending_highlighted_regions": None,
                "awaiting_phase": None,
            },
            goto="localised_detail",
        )

    # --- Round 2: severity / onset QuestionFields ---
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
