"""Curated evidence catalogue ranking and parallel fetch behavior."""

from __future__ import annotations

import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx

from intelligence.tools import (
    CatalogueEntry,
    FailedSource,
    RankedCatalogueEntry,
    SuccessfulSource,
    _fetch_ranked_sources,
    _load_catalogue,
    _rank_catalogue,
    web_search,
)
from pydantic import ValidationError


def _entry(title: str, url: str, row_order: int) -> CatalogueEntry:
    tokens = tuple(title.casefold().split())
    return CatalogueEntry(
        title=title,
        url=url,
        row_order=row_order,
        tokens=tokens,
        normalized_title=" ".join(tokens),
        normalized_slug=" ".join(tokens),
    )


def _ranked(index: int) -> RankedCatalogueEntry:
    return RankedCatalogueEntry(
        entry=_entry(
            f"Source {index}",
            f"https://healthify.nz/health-a-z/source-{index}",
            index,
        ),
        score=float(10 - index),
    )


class TestCatalogueRanking(unittest.TestCase):
    def test_bom_csv_formats_and_unsafe_rows(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            healthify = root / "healthify.csv"
            health_nz = root / "health-nz.csv"
            healthify.write_text(
                "\ufefftitle,url,letter\n"
                "First,https://healthify.nz/health-a-z/first,F\n"
                "Insecure,http://healthify.nz/health-a-z/insecure,I\n"
                "Foreign,https://example.com/foreign,F\n",
                encoding="utf-8",
            )
            health_nz.write_text(
                "\ufefftitle,url,path,parent_path,depth\n"
                "Second,https://www.healthnz.govt.nz/health-topics/second,"
                "/health-topics/second,/health-topics,1\n"
                'Placeholder,"https://www.healthnz.govt.nz/health-topics/'
                '%5Bsitetree_link,id=1%5D",/bad,/health-topics,1\n'
                "Malformed,not a url,/bad,/health-topics,1\n",
                encoding="utf-8",
            )

            entries = _load_catalogue((healthify, health_nz))

        self.assertEqual([entry.title for entry in entries], ["First", "Second"])
        self.assertEqual([entry.row_order for entry in entries], [0, 3])

    def test_bm25_exact_phrase_stable_ties_and_top_three(self) -> None:
        entries = (
            _entry(
                "Chest pain",
                "https://healthify.nz/health-a-z/chest-pain",
                0,
            ),
            _entry(
                "Chest pain",
                "https://www.healthnz.govt.nz/health-topics/chest-pain",
                1,
            ),
            _entry(
                "Pain in the chest",
                "https://healthify.nz/health-a-z/pain-in-the-chest",
                2,
            ),
            _entry(
                "Chest infection",
                "https://healthify.nz/health-a-z/chest-infection",
                3,
            ),
        )

        ranked = _rank_catalogue("chest pain", entries)

        self.assertEqual(len(ranked), 3)
        self.assertEqual(
            [item.entry.row_order for item in ranked[:2]],
            [0, 1],
        )
        self.assertGreater(ranked[0].score, ranked[2].score)

    def test_zero_to_two_positive_results_are_not_padded(self) -> None:
        entries = (
            _entry(
                "Migraine",
                "https://healthify.nz/health-a-z/migraine",
                0,
            ),
            _entry(
                "Head injury",
                "https://www.healthnz.govt.nz/health-topics/head-injury",
                1,
            ),
        )
        self.assertEqual(_rank_catalogue("unmatched phrase", entries), [])
        self.assertEqual(len(_rank_catalogue("migraine", entries)), 1)
        self.assertEqual(len(_rank_catalogue("migraine head", entries)), 2)

    def test_tool_rejects_empty_query(self) -> None:
        with self.assertRaises(ValidationError):
            web_search.invoke({"query": ""})


class TestParallelFetching(unittest.TestCase):
    def test_concurrent_completion_does_not_change_rank_order(self) -> None:
        ranked = [_ranked(index) for index in range(3)]
        barrier = threading.Barrier(3)
        condition = threading.Condition()
        completion_order = [2, 0, 1]
        next_completion = 0
        observed_completion: list[int] = []

        def fetcher(item: RankedCatalogueEntry) -> SuccessfulSource:
            nonlocal next_completion
            index = item.entry.row_order
            barrier.wait(timeout=2)
            with condition:
                condition.wait_for(
                    lambda: completion_order[next_completion] == index,
                    timeout=2,
                )
                observed_completion.append(index)
                next_completion += 1
                condition.notify_all()
            return SuccessfulSource(
                title=item.entry.title,
                url=item.entry.url,
                bm25_score=item.score,
                latency_ms=index,
                content=f"content {index}",
            )

        successful, failed, _ = _fetch_ranked_sources(ranked, fetcher=fetcher)

        self.assertEqual(observed_completion, completion_order)
        self.assertEqual(
            [source.url for source in successful],
            [item.entry.url for item in ranked],
        )
        self.assertEqual(failed, [])

    def test_partial_exception_and_complete_failure(self) -> None:
        ranked = [_ranked(index) for index in range(3)]

        def partial_fetcher(
            item: RankedCatalogueEntry,
        ) -> SuccessfulSource | FailedSource:
            if item.entry.row_order == 1:
                raise RuntimeError("unsafe detail must not escape")
            return SuccessfulSource(
                title=item.entry.title,
                url=item.entry.url,
                bm25_score=item.score,
                latency_ms=1,
                content="ok",
            )

        successful, failed, _ = _fetch_ranked_sources(
            ranked,
            fetcher=partial_fetcher,
        )
        self.assertEqual(
            [source.url for source in successful],
            [ranked[0].entry.url, ranked[2].entry.url],
        )
        self.assertEqual([source.error_code for source in failed], ["fetch_error"])

        def failed_fetcher(item: RankedCatalogueEntry) -> FailedSource:
            return FailedSource(
                title=item.entry.title,
                url=item.entry.url,
                bm25_score=item.score,
                latency_ms=8_000,
                error_code="timeout",
            )

        successful, failed, _ = _fetch_ranked_sources(
            ranked,
            fetcher=failed_fetcher,
        )
        self.assertEqual(successful, [])
        self.assertEqual(len(failed), 3)


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        content_type: str = "text/html",
        body: bytes = b"<main>Useful content</main>",
        headers: dict[str, str] | None = None,
        chunks: list[bytes] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = {"content-type": content_type, **(headers or {})}
        self._chunks = chunks if chunks is not None else [body]

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def iter_bytes(self):
        yield from self._chunks


class _FakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def stream(self, *args: object, **kwargs: object):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class TestFetchSafety(unittest.TestCase):
    def _fetch_with(self, responses: list[object]) -> SuccessfulSource | FailedSource:
        with patch(
            "intelligence.tools.httpx.Client",
            return_value=_FakeClient(responses),
        ):
            successful, failed, _ = _fetch_ranked_sources([_ranked(0)])
        return successful[0] if successful else failed[0]

    def test_html_is_cleaned_and_limited(self) -> None:
        body = (
            b"<html><header>Header</header><main><script>bad()</script>"
            b"<nav>Links</nav><h1>Title</h1><p>Readable text</p></main></html>"
        )
        result = self._fetch_with([_FakeResponse(body=body)])
        self.assertIsInstance(result, SuccessfulSource)
        assert isinstance(result, SuccessfulSource)
        self.assertEqual(result.content, "Title Readable text")

        limited = self._fetch_with(
            [_FakeResponse(body=b"<main>" + b"x" * 12_100 + b"</main>")]
        )
        self.assertIsInstance(limited, SuccessfulSource)
        assert isinstance(limited, SuccessfulSource)
        self.assertEqual(len(limited.content), 12_000)

    def test_non_html_oversized_unsafe_redirect_and_empty_content(self) -> None:
        cases = (
            (
                [_FakeResponse(content_type="application/pdf")],
                "non_html",
            ),
            (
                [
                    _FakeResponse(
                        headers={"content-length": "1048577"},
                    )
                ],
                "too_large",
            ),
            (
                [
                    _FakeResponse(
                        status_code=302,
                        headers={"location": "https://example.com/steal"},
                    )
                ],
                "unsafe_redirect",
            ),
            (
                [_FakeResponse(body=b"<html><main><script>x</script></main></html>")],
                "empty_content",
            ),
        )
        for responses, expected_code in cases:
            with self.subTest(error_code=expected_code):
                result = self._fetch_with(responses)
                self.assertIsInstance(result, FailedSource)
                assert isinstance(result, FailedSource)
                self.assertEqual(result.error_code, expected_code)

    def test_timeout_is_safe_failure(self) -> None:
        result = self._fetch_with(
            [
                httpx.ReadTimeout(
                    "timed out", request=httpx.Request("GET", "https://healthify.nz")
                )
            ]
        )
        self.assertIsInstance(result, FailedSource)
        assert isinstance(result, FailedSource)
        self.assertEqual(result.error_code, "timeout")

    def test_more_than_two_redirects_is_rejected(self) -> None:
        result = self._fetch_with(
            [
                _FakeResponse(status_code=302, headers={"location": "/one"}),
                _FakeResponse(status_code=302, headers={"location": "/two"}),
                _FakeResponse(status_code=302, headers={"location": "/three"}),
            ]
        )
        self.assertIsInstance(result, FailedSource)
        assert isinstance(result, FailedSource)
        self.assertEqual(result.error_code, "too_many_redirects")


if __name__ == "__main__":
    unittest.main()
