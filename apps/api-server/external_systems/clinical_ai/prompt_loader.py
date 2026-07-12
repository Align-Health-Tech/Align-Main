"""Load prompts/{category}/{phase}.md as a system prompt string."""
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(category: str, phase: str) -> str:
    """category: classifier | devise_and_prioritise | question_generation |
    nurse_review | translation

    Raises FileNotFoundError if the prompt file is missing.
    """
    path = PROMPTS_DIR / category / f"{phase}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"No prompt at {path} — add prompts/{category}/{phase}.md"
        )
    return path.read_text(encoding="utf-8")
