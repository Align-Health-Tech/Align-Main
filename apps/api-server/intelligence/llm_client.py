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
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

load_dotenv()

T = TypeVar("T", bound=BaseModel)

# Last tool-call telemetry (smoke / local probes). Not a production API contract.
_last_tool_trace: dict[str, Any] = {
    "tool_choice": None,
    "tool_calls": [],  # [{name, args}, ...]
    "tool_results": [],  # [{name, args, result}, ...]
}


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
    return _chat_structured(output_type, system, user, temperature=temperature)


def run_agent_with_tools(
    category: str,
    phase: str,
    payload: dict[str, Any],
    output_type: type[T],
    tools: Sequence[BaseTool],
    *,
    temperature: float = 0,
    tool_choice: Optional[str | dict[str, Any] | bool] = None,
    tool_trace: Optional[list[dict[str, Any]]] = None,
    tool_default_args: Optional[dict[str, dict[str, Any]]] = None,
) -> T:
    """Same as run_agent, with exactly one tool-selection round and invocation."""
    system = load_prompt(category, phase)
    user = json.dumps(payload, default=str)
    return _chat_with_tools_then_structured(
        output_type,
        system,
        user,
        tools=tools,
        temperature=temperature,
        tool_choice=tool_choice,
        tool_trace=tool_trace,
        tool_default_args=tool_default_args,
    )


def validate_model_configuration() -> None:
    """Fail fast when the Azure model environment is incomplete."""
    _get_model()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_last_tool_trace() -> dict[str, Any]:
    """Snapshot of the most recent one-round tool call."""
    return {
        "tool_choice": _last_tool_trace.get("tool_choice"),
        "tool_calls": list(_last_tool_trace.get("tool_calls") or []),
        "tool_results": list(_last_tool_trace.get("tool_results") or []),
    }


def _reset_last_tool_trace() -> None:
    _last_tool_trace["tool_choice"] = None
    _last_tool_trace["tool_calls"] = []
    _last_tool_trace["tool_results"] = []


def _get_model(*, temperature: float = 0) -> AzureChatOpenAI:
    """Build an Azure Responses API chat model from env.

    Required: AZURE_OPENAI_API_KEY, AZURE_MODEL_NAME, AZURE_OPENAI_ENDPOINT
    Optional: AZURE_OPENAI_API_VERSION (default 2025-04-01-preview)
    """
    if temperature != 0:
        raise ValueError("Azure GPT-5.4 Responses does not support temperature")

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY is not set")

    deployment = os.getenv("AZURE_MODEL_NAME")
    if not deployment:
        raise RuntimeError("Set AZURE_MODEL_NAME for the Azure deployment")

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        raise RuntimeError("Set AZURE_OPENAI_ENDPOINT")

    api_version = (
        os.getenv("AZURE_OPENAI_API_VERSION") or "2025-04-01-preview"
    ).strip()

    return AzureChatOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_version=api_version,
        reasoning_effort="low",
        use_responses_api=True,
        timeout=60,
        max_retries=0,
    )


def _chat_structured(
    schema: type[T],
    system: str,
    user: str,
    *,
    temperature: float = 0,
) -> T:
    """Invoke Azure chat with with_structured_output(schema)."""
    model = _get_model(temperature=temperature).with_structured_output(schema)
    result = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    if not isinstance(result, schema):
        return schema.model_validate(result)
    return result


def _chat_with_tools_then_structured(
    schema: type[T],
    system: str,
    user: str,
    tools: Sequence[BaseTool],
    *,
    temperature: float = 0,
    tool_choice: Optional[str | dict[str, Any] | bool] = None,
    tool_trace: Optional[list[dict[str, Any]]] = None,
    tool_default_args: Optional[dict[str, dict[str, Any]]] = None,
) -> T:
    """Run one tool-selection call, one tool, then return structured output.

    ``tool_choice`` defaults to model auto (None). Production Devise passes
    ``"required"`` with only ``web_search`` bound.
    """
    _reset_last_tool_trace()
    _last_tool_trace["tool_choice"] = "auto" if tool_choice is None else tool_choice

    base = _get_model(temperature=temperature)
    tool_map = {t.name: t for t in tools}
    bind_kwargs: dict[str, Any] = {"parallel_tool_calls": False}
    if tool_choice is not None:
        bind_kwargs["tool_choice"] = tool_choice
    bound = base.bind_tools(list(tools), **bind_kwargs)

    messages: list[BaseMessage] = [
        SystemMessage(content=system),
        HumanMessage(content=user),
    ]

    ai = bound.invoke(messages)
    messages.append(ai)
    tool_calls = getattr(ai, "tool_calls", None) or []
    if len(tool_calls) > 1:
        raise RuntimeError("Expected at most one tool call")
    if tool_calls:
        call = tool_calls[0]
        name = call["name"]
        args = dict(call.get("args") or {})
        for key, value in (tool_default_args or {}).get(name, {}).items():
            if not args.get(key):
                args[key] = value
        _last_tool_trace["tool_calls"].append({"name": name, "args": args})
        tool = tool_map.get(name)
        if tool is None:
            observation = f"Unknown tool: {name}"
        else:
            try:
                observation = tool.invoke(args)
            except Exception as exc:  # noqa: BLE001
                observation = f"Tool {name} failed: {exc}"
        traced_result = {
            "name": name,
            "args": args,
            "result": observation,
        }
        _last_tool_trace["tool_results"].append(traced_result)
        if tool_trace is not None:
            tool_trace.append(traced_result)
        messages.append(ToolMessage(content=str(observation), tool_call_id=call["id"]))

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
