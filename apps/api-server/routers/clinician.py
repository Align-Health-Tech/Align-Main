"""Clinician dashboard routes — M6: mark-complete only.

Auth (Medtech / Entra) and RLS deferred to M7. List/detail/comments out of scope.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.session_errors import SessionConflictError, SessionNotFoundError
from services.session_lifecycle import lifecycle

router = APIRouter(prefix="/clinician", tags=["clinician"])


class CompleteResponse(BaseModel):
    session_id: str
    status: str


@router.post("/sessions/{session_id}/complete", response_model=CompleteResponse)
def mark_complete(session_id: str) -> CompleteResponse:
    """AWAITING_REVIEW → COMPLETED. 409 otherwise."""
    try:
        sid, status = lifecycle.clinician_complete(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CompleteResponse(session_id=sid, status=status)
