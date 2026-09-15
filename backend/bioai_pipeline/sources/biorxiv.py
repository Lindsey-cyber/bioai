from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time as datetime_time, timezone
from typing import Any

from bioai_pipeline.models import ArxivPaper, Author
from bioai_pipeline.sources.arxiv import USER_AGENT


API_URL = "https://api.biorxiv.org/details/biorxiv"
CROSSREF_URL = "https://api.crossref.org/works"


class BiorxivError(RuntimeError):
    pass


class BiorxivClient:
    page_size = 30

    def __init__(self, request_timeout: int = 20, max_attempts: int = 2):
        self.request_timeout = request_timeout
        self.max_attempts = max(1, max_attempts)

    def fetch_recent(
        self,
        *,
        start_date: date,
        end_date: date,
        max_results: int,
    ) -> list[ArxivPaper]:
        try:
            first = self._page(start_date, end_date, 0)
        except BiorxivError:
            # The public bioRxiv endpoint intermittently times out from hosted
            # CI runners. Crossref is the DOI metadata registry used by
            # bioRxiv and gives us a safe abstract-level fallback.
            return CrossrefBiorxivClient(
                request_timeout=max(30, self.request_timeout),
                max_attempts=max(2, self.max_attempts),
            ).fetch_recent(
                start_date=start_date,
                end_date=end_date,
                max_results=max_results,
            )
        total = self._total(first)
        cursor = max(0, total - max_results)
        payload = first if cursor == 0 else self._page(start_date, end_date, cursor)
        papers: list[ArxivPaper] = []

        while cursor < total and len(papers) < max_results:
            collection = payload.get("collection") or []
            if not collection:
                break
            for item in collection:
                try:
                    papers.append(self._parse_item(item))
                except (BiorxivError, TypeError, ValueError):
                    # Withdrawn or incomplete records occasionally appear in
                    # the collection without a DOI/date. They have no stable
                    # identity and cannot safely become feed items.
                    continue
            cursor += len(collection)
            if cursor < total and len(papers) < max_results:
                time.sleep(0.4)
                try:
                    payload = self._page(start_date, end_date, cursor)
                except BiorxivError:
                    # A later page timing out should not discard earlier pages.
                    # The overlapping daily window will fill the gap next run.
                    break
        return papers[-max_results:]

    def _page(self, start_date: date, end_date: date, cursor: int) -> dict[str, Any]:
        url = f"{API_URL}/{start_date.isoformat()}/{end_date.isoformat()}/{cursor}/json"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.request_timeout,
                ) as response:
                    payload = json.load(response)
                messages = payload.get("messages") or []
                if messages and messages[0].get("status") != "ok":
                    raise BiorxivError(str(messages[0].get("status")))
                return payload
            except BiorxivError:
                raise
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if (
                    isinstance(exc, urllib.error.HTTPError)
                    and exc.code < 500
                    and exc.code != 429
                ):
                    break
                if attempt < self.max_attempts - 1:
                    time.sleep(2**attempt)
        raise BiorxivError(f"bioRxiv API request failed after retries: {last_error}")

    @staticmethod
    def _total(payload: dict[str, Any]) -> int:
        messages = payload.get("messages") or []
        if not messages:
            return 0
        return int(messages[0].get("total") or 0)

    @staticmethod
    def _parse_item(item: dict[str, Any]) -> ArxivPaper:
        doi = str(item.get("doi") or "").strip()
        if not doi:
            raise BiorxivError("bioRxiv item is missing a DOI")
        version = int(item.get("version") or 1)
        posted_date = date.fromisoformat(str(item.get("date")))
        timestamp = datetime.combine(posted_date, datetime_time.min, tzinfo=timezone.utc)
        authors = tuple(
            Author(name=name.strip())
            for name in str(item.get("authors") or "").split(";")
            if name.strip()
        )
        category = str(item.get("category") or "biology").strip().lower()
        abstract_url = f"https://www.biorxiv.org/content/{doi}v{version}"
        return ArxivPaper(
            arxiv_id=f"biorxiv:{doi}",
            version=version,
            title=" ".join(str(item.get("title") or "Untitled").split()),
            abstract=" ".join(str(item.get("abstract") or "").split()),
            authors=authors,
            categories=(f"biorxiv:{category}",),
            primary_category=f"biorxiv:{category}",
            published_at=timestamp,
            updated_at=timestamp,
            abstract_url=abstract_url,
            pdf_url=f"{abstract_url}.full.pdf",
            doi=doi,
            comment=str(item.get("type") or "") or None,
            query_name="biorxiv",
            raw_xml=json.dumps(item, ensure_ascii=False),
            source="biorxiv",
            source_metadata={
                "source_external_id": doi,
                "corresponding_author": item.get("author_corresponding") or None,
                "corresponding_institution": item.get("author_corresponding_institution") or None,
                "jatsxml": item.get("jatsxml") or None,
                "license": item.get("license") or None,
            },
        )


class CrossrefBiorxivClient:
    """Abstract-level bioRxiv fallback backed by Crossref metadata."""

    # bioRxiv moved new deposits from 10.1101 to 10.64898. Query both so the
    # adapter also works across the transition and filter out medRxiv records.
    doi_prefixes = ("10.64898", "10.1101")

    def __init__(self, request_timeout: int = 30, max_attempts: int = 2):
        self.request_timeout = request_timeout
        self.max_attempts = max(1, max_attempts)

    def fetch_recent(
        self,
        *,
        start_date: date,
        end_date: date,
        max_results: int,
    ) -> list[ArxivPaper]:
        papers: list[ArxivPaper] = []
        errors: list[str] = []
        for prefix in self.doi_prefixes:
            try:
                for item in self._items(start_date, end_date, prefix, max_results):
                    if not self._is_biorxiv(item):
                        continue
                    try:
                        papers.append(self._parse_item(item))
                    except (BiorxivError, TypeError, ValueError):
                        continue
            except BiorxivError as exc:
                errors.append(str(exc))

        if not papers and errors:
            raise BiorxivError("; ".join(errors))

        unique = {paper.arxiv_id: paper for paper in papers}
        ordered = sorted(unique.values(), key=lambda paper: paper.published_at)
        return ordered[-max_results:]

    def _items(
        self,
        start_date: date,
        end_date: date,
        prefix: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode(
            {
                "filter": (
                    f"from-pub-date:{start_date.isoformat()},"
                    f"until-pub-date:{end_date.isoformat()},"
                    f"prefix:{prefix},type:posted-content"
                ),
                "rows": min(1000, max(100, max_results * 2)),
                "sort": "published",
                "order": "desc",
            }
        )
        request = urllib.request.Request(
            f"{CROSSREF_URL}?{query}",
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                    payload = json.load(response)
                return list(payload.get("message", {}).get("items") or [])
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code < 500 and exc.code != 429:
                    break
                if attempt < self.max_attempts - 1:
                    time.sleep(2**attempt)
        raise BiorxivError(
            f"Crossref bioRxiv fallback failed after retries: {last_error}"
        )

    @staticmethod
    def _is_biorxiv(item: dict[str, Any]) -> bool:
        names = {
            str(institution.get("name") or "").strip().lower()
            for institution in item.get("institution") or []
        }
        primary_url = str(
            (item.get("resource") or {}).get("primary", {}).get("URL") or ""
        ).lower()
        return "biorxiv" in names or "biorxiv.org" in primary_url

    @staticmethod
    def _parse_item(item: dict[str, Any]) -> ArxivPaper:
        doi = str(item.get("DOI") or "").strip()
        if not doi:
            raise BiorxivError("Crossref item is missing a DOI")
        title_values = item.get("title") or []
        title = str(title_values[0] if title_values else "Untitled")
        published = (
            item.get("published")
            or item.get("posted")
            or item.get("issued")
            or {}
        )
        date_parts = published.get("date-parts") or []
        if not date_parts or not date_parts[0]:
            raise BiorxivError("Crossref item is missing a publication date")
        parts = list(date_parts[0]) + [1, 1]
        posted_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
        timestamp = datetime.combine(
            posted_date,
            datetime_time.min,
            tzinfo=timezone.utc,
        )

        authors: list[Author] = []
        for author in item.get("author") or []:
            name = " ".join(
                value
                for value in (
                    str(author.get("given") or "").strip(),
                    str(author.get("family") or "").strip(),
                )
                if value
            )
            affiliation = next(
                (
                    str(value.get("name") or "").strip()
                    for value in author.get("affiliation") or []
                    if str(value.get("name") or "").strip()
                ),
                None,
            )
            if name:
                authors.append(Author(name=name, affiliation=affiliation))

        abstract = html.unescape(
            re.sub(r"<[^>]+>", " ", str(item.get("abstract") or ""))
        )
        abstract = " ".join(abstract.split())
        category = str(item.get("group-title") or "biology").strip().lower()
        corresponding_institution = next(
            (author.affiliation for author in reversed(authors) if author.affiliation),
            None,
        )
        original_url = f"https://doi.org/{doi}"
        return ArxivPaper(
            arxiv_id=f"biorxiv:{doi}",
            version=1,
            title=" ".join(title.split()),
            abstract=abstract,
            authors=tuple(authors),
            categories=(f"biorxiv:{category}",),
            primary_category=f"biorxiv:{category}",
            published_at=timestamp,
            updated_at=timestamp,
            abstract_url=original_url,
            pdf_url=original_url,
            doi=doi,
            comment=str(item.get("subtype") or "preprint"),
            query_name="biorxiv-crossref-fallback",
            raw_xml=json.dumps(item, ensure_ascii=False),
            source="biorxiv",
            source_metadata={
                "source_external_id": doi,
                "metadata_provider": "crossref_fallback",
                "corresponding_institution": corresponding_institution,
                "license": next(
                    (
                        license_item.get("URL")
                        for license_item in item.get("license") or []
                        if license_item.get("URL")
                    ),
                    None,
                ),
            },
        )
