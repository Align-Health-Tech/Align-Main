"""Clinical intelligence — agents, prompts, registry, LLM.

Engine nodes and tests call ``engine.agent_bridge`` (CI patches that module).
Agent implementations live in ``agents``; do not call them from routers.
"""
