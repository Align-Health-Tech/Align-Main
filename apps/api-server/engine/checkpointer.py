"""Memory checkpointer for local / M0; Postgres later."""
from langgraph.checkpoint.memory import MemorySaver


def build_checkpointer() -> MemorySaver:
    return MemorySaver()
