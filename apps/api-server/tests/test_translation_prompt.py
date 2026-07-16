"""translation/to_english prompt load + TranslationResult shape."""
from __future__ import annotations

import unittest

from external_systems.clinical_ai.prompt_loader import load_prompt
from schemas.clinical_ai_io import TranslationResult


class TestTranslationPrompt(unittest.TestCase):
    def test_prompt_is_ported_not_stub(self) -> None:
        text = load_prompt("translation", "to_english")
        self.assertNotIn("TODO", text)
        self.assertIn("en_text", text)
        self.assertIn("exactly", text.casefold())

    def test_result_schema(self) -> None:
        parsed = TranslationResult.model_validate(
            {"en_text": "lower back ache", "detected_lang": "ko"}
        )
        self.assertEqual(parsed.en_text, "lower back ache")
        self.assertEqual(parsed.detected_lang, "ko")


if __name__ == "__main__":
    unittest.main()
