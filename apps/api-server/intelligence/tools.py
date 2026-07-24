"""Curated clinical evidence lookup used by Devise.

``web_search`` retains its LangChain tool name, but it only ranks committed
Healthify / Health NZ catalogue rows and fetches the best three HTML pages.
"""

from __future__ import annotations

import csv
import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import unquote, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from langchain.tools import tool
from pydantic import BaseModel, Field

API_SERVER_ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_PATHS = (
    API_SERVER_ROOT / "urls" / "healthify_health_az_urls.csv",
    API_SERVER_ROOT / "urls" / "healthnz_health_topics_urls.csv",
)
ALLOWED_HOSTS = frozenset({"healthify.nz", "www.healthnz.govt.nz"})
MAX_RESULTS = 3
MAX_REDIRECTS = 2
MAX_RESPONSE_BYTES = 1_048_576
MAX_CONTENT_CHARS = 12_000
SOURCE_DEADLINE_SECONDS = 8.0
EXACT_PHRASE_BOOST = 2.0

_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_HTML_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_REMOVED_ELEMENTS = (
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "noscript",
    "svg",
)


@dataclass(frozen=True)
class CatalogueEntry:
    title: str
    url: str
    row_order: int
    tokens: tuple[str, ...]
    normalized_title: str
    normalized_slug: str


@dataclass(frozen=True)
class RankedCatalogueEntry:
    entry: CatalogueEntry
    score: float


class SuccessfulSource(BaseModel):
    title: str
    url: str
    bm25_score: float
    latency_ms: int = Field(ge=0)
    content: str


class FailedSource(BaseModel):
    title: str
    url: str
    bm25_score: float
    latency_ms: int = Field(ge=0)
    error_code: str


class EvidenceSearchResult(BaseModel):
    query: str
    successful_sources: list[SuccessfulSource] = Field(default_factory=list)
    failed_sources: list[FailedSource] = Field(default_factory=list)
    batch_latency_ms: int = Field(ge=0)


class WebSearchInput(BaseModel):
    query: str = Field(
        min_length=3,
        max_length=200,
        description="A non-empty, concise clinical search query.",
    )


@tool(args_schema=WebSearchInput)
def web_search(query: str) -> str:
    """Fetch clinical context from the curated Healthify and Health NZ catalogue.

    Supply one concise clinical query describing the presentation or safety
    concern. The result contains up to three ranked HTML sources.
    """
    result = _search_curated_evidence(query)
    return json.dumps(result.model_dump(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_catalogue(
    paths: Sequence[Path] | None = None,
) -> tuple[CatalogueEntry, ...]:
    """Load valid catalogue rows in explicit file and row order.

    The default catalogues are cached for the process lifetime. Passing paths
    is primarily useful for deterministic tests of alternate CSV formats.
    """
    selected = CATALOGUE_PATHS if paths is None else tuple(paths)
    return _load_catalogue_cached(tuple(str(path.resolve()) for path in selected))


def _rank_catalogue(
    query: str,
    entries: Sequence[CatalogueEntry] | None = None,
    *,
    limit: int = MAX_RESULTS,
) -> list[RankedCatalogueEntry]:
    """Return positive-scoring BM25 matches with stable row-order ties."""
    catalogue = tuple(entries) if entries is not None else _load_catalogue()
    query_tokens = _normalize_tokens(query)
    if not query_tokens or not catalogue or limit <= 0:
        return []

    document_frequencies: dict[str, int] = {}
    for term in set(query_tokens):
        document_frequencies[term] = sum(
            1 for entry in catalogue if term in entry.tokens
        )

    average_length = sum(len(entry.tokens) for entry in catalogue) / len(catalogue)
    normalized_phrase = " ".join(query_tokens)
    ranked: list[RankedCatalogueEntry] = []
    for entry in catalogue:
        score = _bm25_score(
            query_tokens,
            entry.tokens,
            document_frequencies,
            len(catalogue),
            average_length,
        )
        if len(query_tokens) > 1 and (
            normalized_phrase in entry.normalized_title
            or normalized_phrase in entry.normalized_slug
        ):
            score += EXACT_PHRASE_BOOST
        if score > 0:
            ranked.append(RankedCatalogueEntry(entry=entry, score=score))

    ranked.sort(key=lambda item: (-item.score, item.entry.row_order))
    return ranked[:limit]


def _fetch_ranked_sources(
    ranked: Sequence[RankedCatalogueEntry],
    *,
    fetcher: Callable[[RankedCatalogueEntry], SuccessfulSource | FailedSource]
    | None = None,
) -> tuple[list[SuccessfulSource], list[FailedSource], int]:
    """Fetch selected sources concurrently and restore BM25 rank order."""
    selected = list(ranked[:MAX_RESULTS])
    if not selected:
        return [], [], 0

    started = time.monotonic()
    worker = fetcher or _fetch_source
    by_index: dict[int, SuccessfulSource | FailedSource] = {}
    with ThreadPoolExecutor(max_workers=MAX_RESULTS) as executor:
        futures = {
            executor.submit(worker, ranked_entry): index
            for index, ranked_entry in enumerate(selected)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                by_index[index] = future.result()
            except Exception:  # noqa: BLE001 - isolate every source worker
                item = selected[index]
                by_index[index] = _failed_source(
                    item,
                    latency_ms=0,
                    error_code="fetch_error",
                )

    successful: list[SuccessfulSource] = []
    failed: list[FailedSource] = []
    for index in range(len(selected)):
        result = by_index[index]
        if isinstance(result, SuccessfulSource):
            successful.append(result)
        else:
            failed.append(result)
    batch_latency_ms = round((time.monotonic() - started) * 1000)
    return successful, failed, batch_latency_ms


def _search_curated_evidence(query: str) -> EvidenceSearchResult:
    """Rank the committed catalogue and fetch up to three matching sources."""
    ranked = _rank_catalogue(query)
    successful, failed, batch_latency_ms = _fetch_ranked_sources(ranked)
    return EvidenceSearchResult(
        query=query,
        successful_sources=successful,
        failed_sources=failed,
        batch_latency_ms=batch_latency_ms,
    )


@lru_cache(maxsize=8)
def _load_catalogue_cached(paths: tuple[str, ...]) -> tuple[CatalogueEntry, ...]:
    entries: list[CatalogueEntry] = []
    row_order = 0
    for raw_path in paths:
        with Path(raw_path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                title = (row.get("title") or "").strip()
                url = (row.get("url") or "").strip()
                if title and _is_safe_catalogue_url(url):
                    title_tokens = _normalize_tokens(title)
                    slug_text = _url_slug_text(url)
                    slug_tokens = _normalize_tokens(slug_text)
                    entries.append(
                        CatalogueEntry(
                            title=title,
                            url=url,
                            row_order=row_order,
                            tokens=tuple(title_tokens + slug_tokens),
                            normalized_title=" ".join(title_tokens),
                            normalized_slug=" ".join(slug_tokens),
                        )
                    )
                row_order += 1
    return tuple(entries)


def _normalize_tokens(value: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN_PATTERN.finditer(value)]


def _url_slug_text(url: str) -> str:
    return unquote(urlsplit(url).path).replace("-", " ").replace("/", " ")


def _is_safe_catalogue_url(url: str) -> bool:
    if any(character.isspace() or ord(character) < 32 for character in url):
        return False
    if "\\" in url:
        return False
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    decoded = unquote(unquote(url)).casefold()
    return (
        parsed.scheme == "https"
        and parsed.hostname in ALLOWED_HOSTS
        and parsed.username is None
        and parsed.password is None
        and port is None
        and parsed.path.startswith("/")
        and not parsed.fragment
        and "sitetree_link" not in decoded
        and not any(character in decoded for character in ("[", "]", "{", "}"))
    )


def _bm25_score(
    query_tokens: Sequence[str],
    document_tokens: Sequence[str],
    document_frequencies: dict[str, int],
    document_count: int,
    average_length: float,
) -> float:
    k1 = 1.5
    b = 0.75
    frequencies: dict[str, int] = {}
    for token in document_tokens:
        frequencies[token] = frequencies.get(token, 0) + 1

    score = 0.0
    document_length = len(document_tokens)
    for term in query_tokens:
        frequency = frequencies.get(term, 0)
        if frequency == 0:
            continue
        document_frequency = document_frequencies[term]
        inverse_document_frequency = math.log(
            1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        denominator = frequency + k1 * (1 - b + b * document_length / average_length)
        score += inverse_document_frequency * (frequency * (k1 + 1) / denominator)
    return score


def _fetch_source(
    ranked_entry: RankedCatalogueEntry,
) -> SuccessfulSource | FailedSource:
    started = time.monotonic()
    initial_url = ranked_entry.entry.url
    initial_host = urlsplit(initial_url).hostname
    current_url = initial_url

    try:
        with httpx.Client(
            follow_redirects=False,
            timeout=SOURCE_DEADLINE_SECONDS,
            headers={"User-Agent": "AlignEvidenceFetcher/1.0"},
        ) as client:
            for redirect_count in range(MAX_REDIRECTS + 1):
                remaining = SOURCE_DEADLINE_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    raise httpx.TimeoutException("source deadline exceeded")

                with client.stream("GET", current_url, timeout=remaining) as response:
                    if response.status_code in _REDIRECT_STATUSES:
                        if redirect_count >= MAX_REDIRECTS:
                            return _failed_source(
                                ranked_entry,
                                _elapsed_ms(started),
                                "too_many_redirects",
                            )
                        location = response.headers.get("location")
                        redirect_url = urljoin(current_url, location or "")
                        if not location or not _is_safe_redirect(
                            redirect_url, initial_host
                        ):
                            return _failed_source(
                                ranked_entry,
                                _elapsed_ms(started),
                                "unsafe_redirect",
                            )
                        current_url = redirect_url
                        continue

                    if response.status_code >= 400:
                        return _failed_source(
                            ranked_entry,
                            _elapsed_ms(started),
                            "http_error",
                        )

                    content_type = (
                        response.headers.get("content-type", "")
                        .split(";", 1)[0]
                        .strip()
                        .casefold()
                    )
                    if content_type not in _HTML_CONTENT_TYPES:
                        return _failed_source(
                            ranked_entry,
                            _elapsed_ms(started),
                            "non_html",
                        )

                    body = _read_limited_body(response, started)
                    content = _extract_readable_content(body)
                    if not content:
                        return _failed_source(
                            ranked_entry,
                            _elapsed_ms(started),
                            "empty_content",
                        )
                    return SuccessfulSource(
                        title=ranked_entry.entry.title,
                        url=ranked_entry.entry.url,
                        bm25_score=round(ranked_entry.score, 6),
                        latency_ms=_elapsed_ms(started),
                        content=content,
                    )
    except httpx.TimeoutException:
        return _failed_source(ranked_entry, _elapsed_ms(started), "timeout")
    except httpx.RequestError:
        return _failed_source(ranked_entry, _elapsed_ms(started), "network_error")
    except _ResponseTooLarge:
        return _failed_source(ranked_entry, _elapsed_ms(started), "too_large")
    except _SourceDeadlineExceeded:
        return _failed_source(ranked_entry, _elapsed_ms(started), "timeout")
    except Exception:  # noqa: BLE001 - tool output must expose safe codes only
        return _failed_source(ranked_entry, _elapsed_ms(started), "fetch_error")

    return _failed_source(ranked_entry, _elapsed_ms(started), "fetch_error")


def _read_limited_body(response: httpx.Response, started: float) -> bytes:
    declared_length = response.headers.get("content-length")
    if declared_length:
        try:
            if int(declared_length) > MAX_RESPONSE_BYTES:
                raise _ResponseTooLarge
        except ValueError:
            pass

    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        if time.monotonic() - started >= SOURCE_DEADLINE_SECONDS:
            raise _SourceDeadlineExceeded
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise _ResponseTooLarge
        chunks.append(chunk)
    return b"".join(chunks)


def _extract_readable_content(body: bytes) -> str:
    soup = BeautifulSoup(body, "html.parser")
    for element in soup.find_all(_REMOVED_ELEMENTS):
        element.decompose()
    root = soup.find("main") or soup.find("article") or soup.body
    if root is None:
        return ""
    content = " ".join(root.stripped_strings)
    return content[:MAX_CONTENT_CHARS]


def _is_safe_redirect(url: str, initial_host: str | None) -> bool:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == initial_host
        and parsed.hostname in ALLOWED_HOSTS
        and parsed.username is None
        and parsed.password is None
        and port is None
    )


def _failed_source(
    ranked_entry: RankedCatalogueEntry,
    latency_ms: int,
    error_code: str,
) -> FailedSource:
    return FailedSource(
        title=ranked_entry.entry.title,
        url=ranked_entry.entry.url,
        bm25_score=round(ranked_entry.score, 6),
        latency_ms=latency_ms,
        error_code=error_code,
    )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


class _ResponseTooLarge(Exception):
    pass


class _SourceDeadlineExceeded(Exception):
    pass
