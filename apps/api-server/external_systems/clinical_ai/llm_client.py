"""Azure chat helpers — load prompt, call LLM, return a Pydantic model."""
from __future__ import annotations

import json
import os
from typing import Any, Sequence, TypeVar

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from external_systems.clinical_ai.prompt_loader import load_prompt

load_dotenv()

T = TypeVar("T", bound=BaseModel)


def get_model(*, temperature: float = 0) -> AzureChatOpenAI:
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

    api_version = (os.getenv("AZURE_OPENAI_API_VERSION") or "2025-04-01-preview").strip()

    return AzureChatOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_version=api_version,
        temperature=temperature,
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
    result = model.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
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
) -> T:
    """Tool loop (e.g. web_search), then structured output for the final answer."""
    base = get_model(temperature=temperature)
    tool_map = {t.name: t for t in tools}
    bound = base.bind_tools(list(tools))

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
    )
