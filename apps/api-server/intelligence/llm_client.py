"""Azure chat helpers — load prompt, call LLM, return a Pydantic model."""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Sequence, TypeVar

from dotenv import load_dotenv
from intelligence.prompt_loader import load_prompt
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

load_dotenv()

T = TypeVar("T", bound=BaseModel)

# Last tool-loop telemetry (smoke / local probes). Not a production API contract.
_last_tool_loop: dict[str, Any] = {
    "tool_choice": None,
    "tool_calls": [],  # [{name, args}, ...]
}


def get_last_tool_loop() -> dict[str, Any]:
    """Snapshot of the most recent ``chat_with_tools_then_structured`` loop."""
    return {
        "tool_choice": _last_tool_loop.get("tool_choice"),
        "tool_calls": list(_last_tool_loop.get("tool_calls") or []),
    }


def reset_last_tool_loop() -> None:
    _last_tool_loop["tool_choice"] = None
    _last_tool_loop["tool_calls"] = []


def get_model(*, temperature: float = 0) -> ChatOpenAI:
    """Build AzureChatOpenAI from env.

    Required: AZURE_OPENAI_API_KEY, AZURE_MODEL_NAME, AZURE_OPENAI_ENDPOINT
    Optional: AZURE_OPENAI_API_VERSION (default 2025-04-01-preview)
    """
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY is not set")

    deployment = os.getenv("AZURE_MODEL_NAME")
    if not deployment:
        raise RuntimeError("Set AZURE_MODEL_NAME for the Azure deployment")

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        raise RuntimeError("Set AZURE_OPENAI_ENDPOINT")

    return ChatOpenAI(
        api_key=api_key,
        base_url=endpoint,
        model=deployment,
        temperature=temperature,
        reasoning_effort="low",
        timeout=60,
        max_retries=0,
    )


def chat_structured(
    schema: type[T],
    system: str,
    user: str,
    *,
    temperature: float = 0,
) -> T:
    """Invoke Azure chat with with_structured_output(schema)."""
    model = get_model(temperature=temperature).with_structured_output(schema)
    result = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    if not isinstance(result, schema):
        return schema.model_validate(result)
    return result


def chat_with_tools_then_structured(
    schema: type[T],
    system: str,
    user: str,
    tools: Sequence[BaseTool],
    *,
    max_tool_rounds: int = 3,
    temperature: float = 0,
    tool_choice: Optional[str | dict[str, Any] | bool] = None,
) -> T:
    """Tool loop (e.g. web_search), then structured output for the final answer.

    ``tool_choice`` defaults to model auto (None). Pass a tool name (e.g.
    ``\"web_search\"``) only for rare plumbing checks — not habitual smokes.
    """
    reset_last_tool_loop()
    _last_tool_loop["tool_choice"] = "auto" if tool_choice is None else tool_choice

    base = get_model(temperature=temperature)
    tool_map = {t.name: t for t in tools}
    bind_kwargs: dict[str, Any] = {}
    if tool_choice is not None:
        bind_kwargs["tool_choice"] = tool_choice
    bound = base.bind_tools(list(tools), **bind_kwargs)

    messages: list[BaseMessage] = [
        SystemMessage(content=system),
        HumanMessage(content=user),
    ]

    for _ in range(max_tool_rounds):
        ai = bound.invoke(messages)
        messages.append(ai)
        tool_calls = getattr(ai, "tool_calls", None) or []
        if not tool_calls:
            break
        for call in tool_calls:
            name = call["name"]
            args = call.get("args") or {}
            _last_tool_loop["tool_calls"].append({"name": name, "args": args})
            tool = tool_map.get(name)
            if tool is None:
                observation = f"Unknown tool: {name}"
            else:
                try:
                    observation = tool.invoke(args)
                except Exception as exc:  # noqa: BLE001
                    observation = f"Tool {name} failed: {exc}"
            messages.append(
                ToolMessage(content=str(observation), tool_call_id=call["id"])
            )

    structured = base.with_structured_output(schema)
    messages.append(
        HumanMessage(
            content=(
                "Using the conversation and any tool results above, "
                "return the final structured response now."
            )
        )
    )
    result = structured.invoke(messages)
    if isinstance(result, AIMessage):
        raise RuntimeError("Expected structured output, got AIMessage")
    if not isinstance(result, schema):
        return schema.model_validate(result)
    return result


def run_agent(
    category: str,
    phase: str,
    payload: dict[str, Any],
    output_type: type[T],
    *,
    temperature: float = 0,
) -> T:
    """Load prompt → structured LLM call → validated Pydantic model."""
    system = load_prompt(category, phase)
    user = json.dumps(payload, default=str)
    return chat_structured(output_type, system, user, temperature=temperature)


def run_agent_with_tools(
    category: str,
    phase: str,
    payload: dict[str, Any],
    output_type: type[T],
    tools: Sequence[BaseTool],
    *,
    temperature: float = 0,
    tool_choice: Optional[str | dict[str, Any] | bool] = None,
) -> T:
    """Same as run_agent, but allows tool calls (Devise + web_search)."""
    system = load_prompt(category, phase)
    user = json.dumps(payload, default=str)
    return chat_with_tools_then_structured(
        output_type,
        system,
        user,
        tools=tools,
        temperature=temperature,
        tool_choice=tool_choice,
    )
