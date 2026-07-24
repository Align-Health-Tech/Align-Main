"""Single tool-call tracing used for evidence attribution."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from intelligence.llm_client import (
    _chat_with_tools_then_structured,
    _get_last_tool_trace,
)
from langchain.tools import tool
from langchain_core.messages import AIMessage
from pydantic import BaseModel


class _Result(BaseModel):
    value: str


class _BoundModel:
    def invoke(self, messages):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "test_search",
                    "args": {"query": "first"},
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        )


class _StructuredModel:
    def invoke(self, messages):
        return _Result(value="done")


class _BaseModel:
    def __init__(self, bound_model=None) -> None:
        self.bind_kwargs = {}
        self.bound_model = bound_model or _BoundModel()

    def bind_tools(self, tools, **kwargs):
        self.bind_kwargs = kwargs
        return self.bound_model

    def with_structured_output(self, schema):
        return _StructuredModel()


class TestToolTrace(unittest.TestCase):
    def test_one_invocation_is_traced_with_its_result(self) -> None:
        invocations: list[str] = []

        @tool
        def test_search(query: str) -> str:
            """Test-only search."""
            invocations.append(query)
            return '{"successful_sources": []}'

        base = _BaseModel()
        trace: list[dict] = []
        with patch("intelligence.llm_client._get_model", return_value=base):
            result = _chat_with_tools_then_structured(
                _Result,
                "system",
                "user",
                [test_search],
                tool_choice="test_search",
                tool_trace=trace,
            )

        self.assertEqual(result.value, "done")
        self.assertEqual(invocations, ["first"])
        self.assertEqual(trace[0]["args"], {"query": "first"})
        self.assertEqual(trace[0]["result"], '{"successful_sources": []}')
        self.assertEqual(len(_get_last_tool_trace()["tool_calls"]), 1)
        self.assertFalse(base.bind_kwargs["parallel_tool_calls"])

    def test_blank_required_arg_uses_configured_default(self) -> None:
        class EmptyQueryModel:
            def invoke(self, messages):
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "test_search",
                            "args": {"query": ""},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                )

        invocations: list[str] = []

        @tool
        def test_search(query: str) -> str:
            """Test-only search."""
            invocations.append(query)
            return "ok"

        base = _BaseModel(EmptyQueryModel())
        with patch("intelligence.llm_client._get_model", return_value=base):
            _chat_with_tools_then_structured(
                _Result,
                "system",
                "user",
                [test_search],
                tool_choice="required",
                tool_default_args={"test_search": {"query": "fallback clinical query"}},
            )

        self.assertEqual(invocations, ["fallback clinical query"])
        self.assertEqual(
            _get_last_tool_trace()["tool_calls"][0]["args"]["query"],
            "fallback clinical query",
        )

    def test_multiple_tool_calls_are_rejected(self) -> None:
        class MultipleCallModel:
            def invoke(self, messages):
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "test_search",
                            "args": {"query": "first"},
                            "id": "call-1",
                            "type": "tool_call",
                        },
                        {
                            "name": "test_search",
                            "args": {"query": "second"},
                            "id": "call-2",
                            "type": "tool_call",
                        },
                    ],
                )

        @tool
        def test_search(query: str) -> str:
            """Test-only search."""
            return query

        base = _BaseModel(MultipleCallModel())
        with (
            patch("intelligence.llm_client._get_model", return_value=base),
            self.assertRaisesRegex(RuntimeError, "at most one tool call"),
        ):
            _chat_with_tools_then_structured(
                _Result,
                "system",
                "user",
                [test_search],
                tool_choice="required",
            )


if __name__ == "__main__":
    unittest.main()
