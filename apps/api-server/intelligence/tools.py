"""DuckDuckGo web_search tool used by Devise."""
from langchain.tools import tool

try:
    from duckduckgo_search import DDGS
except ImportError:  # pragma: no cover
    DDGS = None  # type: ignore[misc, assignment]


@tool
def web_search(query: str) -> str:
    """Search the public web for clinical context relevant to the query.
    Use for brief evidence / differential hints — not for inventing patient questions.
    """
    if DDGS is None:
        return "Web search unavailable (duckduckgo-search not installed)."
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=5))
        if not hits:
            return "No web search results."
        lines: list[str] = []
        for h in hits:
            title = h.get("title") or ""
            body = h.get("body") or h.get("snippet") or ""
            href = h.get("href") or h.get("link") or ""
            lines.append(f"- {title}: {body} ({href})")
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001 — degrade gracefully for Devise
        return f"Web search failed: {exc}"
