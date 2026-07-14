"""Compile intake graph (clinical nodes only; consent/survey = router)."""
from __future__ import annotations

import os

# Allow Pydantic models in MemorySaver checkpoints (LangGraph msgpack).
os.environ.setdefault(
    "LANGGRAPH_ALLOWED_MSGPACK_MODULES",
    "schemas.question_fields,schemas.topic_candidates,schemas.session_states,schemas.jsonb_fields",
)

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from engine.checkpointer import build_checkpointer
from engine.topology import wire_topology
from schemas.session_states import SessionState


def build_graph(segment_type: str) -> CompiledStateGraph:
    builder: StateGraph = StateGraph(SessionState)
    wire_topology(builder, segment_type)
    return builder.compile(checkpointer=build_checkpointer())
