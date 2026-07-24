"""Azure Responses API model construction."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from intelligence.llm_client import _get_model


class TestLlmModelConfiguration(unittest.TestCase):
    def test_builds_azure_chat_model_with_responses_api(self) -> None:
        env = {
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.cognitiveservices.azure.com/",
            "AZURE_MODEL_NAME": "gpt-5.4-mini-deployment",
            "AZURE_OPENAI_API_VERSION": "preview",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch("intelligence.llm_client.AzureChatOpenAI") as azure_chat,
        ):
            model = _get_model()

        self.assertIs(model, azure_chat.return_value)
        azure_chat.assert_called_once_with(
            api_key="test-key",
            azure_endpoint="https://example.cognitiveservices.azure.com/",
            azure_deployment="gpt-5.4-mini-deployment",
            api_version="preview",
            reasoning_effort="low",
            use_responses_api=True,
            timeout=60,
            max_retries=0,
        )

    def test_uses_default_api_version(self) -> None:
        env = {
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.cognitiveservices.azure.com/",
            "AZURE_MODEL_NAME": "gpt-5.4-mini-deployment",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch("intelligence.llm_client.AzureChatOpenAI") as azure_chat,
        ):
            _get_model()

        self.assertEqual(
            azure_chat.call_args.kwargs["api_version"],
            "2025-04-01-preview",
        )

    def test_rejects_unsupported_temperature(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not support temperature"):
            _get_model(temperature=0.4)


if __name__ == "__main__":
    unittest.main()
