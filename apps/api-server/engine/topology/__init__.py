"""Segment → topology wiring registry.

Only URGENT_CARE is registered today. Physio/GP are additive: add a module
and register its ``wire_topology`` here — no change to dispatch logic.
``engine/nodes/`` stay flat/shared until a segment needs a different node.
"""
from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import StateGraph

from . import urgent_care

_TOPOLOGY_BUILDERS: dict[str, Callable[[StateGraph], None]] = {
    "URGENT_CARE": urgent_care.wire_topology,
}


def wire_topology(builder: StateGraph, segment_type: str) -> None:
    if segment_type not in _TOPOLOGY_BUILDERS:
        raise ValueError(
            f"No topology registered for segment_type={segment_type!r}"
        )
    _TOPOLOGY_BUILDERS[segment_type](builder)
