"""Patient session HTTP surface — see APISTRUCTURE.md / ROUTER_SPEC.md.

M6: in-memory Encounter/Consent/SurveyResponse stubs (no Postgres / RLS yet).
Auth (QR / session-scoped) deferred — callers pass session_id only.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from schemas.question_fields import NextStep
from services.session_errors import SessionConflictError, SessionNotFoundError
from services.session_lifecycle import lifecycle
from services.session_store import store

router = APIRouter(tags=["sessions"])


class CreateSessionResponse(BaseModel):
    session_id: str
    next_step: NextStep
    # M6: expose status for lifecycle verification (not in original envelope).
    status: str


class RespondRequest(BaseModel):
    answer: dict[str, Any] = Field(
        description="Shape depends on current step_type (consent / batch / diagram / survey)"
    )


class RespondResponse(BaseModel):
    next_step: NextStep
    status: str


class GetSessionResponse(BaseModel):
    next_step: NextStep
    status: str


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(
    session_language: Optional[str] = None,
    patient_sex: Optional[str] = None,
) -> CreateSessionResponse:
    """Create guest encounter at NOT_STARTED; return consent NextStep.

    Optional query params are M6/dev helpers (CLI / tests). Production QR
    binding will set org + language without a body (APISTRUCTURE).
    """
    try:
        session_id, step, status = lifecycle.create_session(
            session_language=session_language or "en",
            patient_sex=patient_sex,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CreateSessionResponse(
        session_id=session_id, next_step=step, status=status
    )


@router.post("/sessions/{session_id}/respond", response_model=RespondResponse)
def respond(session_id: str, body: RespondRequest) -> RespondResponse:
    try:
        step, status = lifecycle.respond(session_id, body.answer)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RespondResponse(next_step=step, status=status)


@router.get("/sessions/{session_id}", response_model=GetSessionResponse)
def get_session(session_id: str) -> GetSessionResponse:
    try:
        step, status = lifecycle.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return GetSessionResponse(next_step=step, status=status)


def reset_in_memory_store() -> None:
    """Test helper — not an HTTP route."""
    store.reset()
