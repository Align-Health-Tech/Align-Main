"""Intake graph topology — clinical nodes only (consent/survey are router-level).

9 nodes: presenting_complaint → … → review (silent) → complete.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from engine.nodes.complete import complete
from engine.nodes.ice import ice
from engine.nodes.localised_detail import localised_detail
from engine.nodes.non_localised_detail import non_localised_detail
from engine.nodes.optional_questions import optional_questions
from engine.nodes.presenting_complaint import presenting_complaint
from engine.nodes.priority_questions import priority_questions
from engine.nodes.redflag_screening import redflag_screening
from engine.nodes.review import review


def wire_topology(builder: StateGraph) -> None:
    builder.add_node("presenting_complaint", presenting_complaint)
    builder.add_node("localised_detail", localised_detail)
    builder.add_node("non_localised_detail", non_localised_detail)
    builder.add_node("priority_questions", priority_questions)
    builder.add_node("redflag_screening", redflag_screening)
    builder.add_node("optional_questions", optional_questions)
    builder.add_node("ice", ice)
    builder.add_node("review", review)
    builder.add_node("complete", complete)

    builder.add_edge(START, "presenting_complaint")
    builder.add_edge("complete", END)
