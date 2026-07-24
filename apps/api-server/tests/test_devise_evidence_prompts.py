"""Copyright and evidence instructions for evidence-enabled Devise phases."""

from __future__ import annotations

import unittest

from intelligence.prompt_loader import load_prompt


class TestDeviseEvidencePrompts(unittest.TestCase):
    def test_priority_and_redflag_have_required_copyright_rules(self) -> None:
        for phase in ("priority_questions", "redflag_screening"):
            with self.subTest(phase=phase):
                prompt = load_prompt("devise_and_prioritise", phase).casefold()
                self.assertIn("prefer original paraphrasing and synthesis", prompt)
                self.assertIn("at most 14 words", prompt)
                self.assertIn(
                    "at most one direct quote from each referenced source",
                    prompt,
                )
                self.assertIn(
                    "do not use quotation marks around paraphrased material",
                    prompt,
                )
                self.assertIn("invoke `web_search` exactly once", prompt)


if __name__ == "__main__":
    unittest.main()
