from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, time as datetime_time, timezone
from typing import Any

from bioai_pipeline.models import ArxivPaper, Author
from bioai_pipeline.sources.arxiv import USER_AGENT


API_URL = "https://api.biorxiv.org/details/biorxiv"


class BiorxivError(RuntimeError):
    pass


class BiorxivClient:
    page_size = 30

    def fetch_recent(
        self,
        *,
        start_date: date,
        end_date: date,
        max_results: int,
    ) -> list[ArxivPaper]:
        first = self._page(start_date, end_date, 0)
        total = self._total(first)
        cursor = max(0, total - max_results)
        payload = first if cursor == 0 else self._page(start_date, end_date, cursor)
        papers: list[ArxivPaper] = []

        while cursor < total and len(papers) < max_results:
            collection = payload.get("collection") or []
            if not collection:
                break
            papers.extend(self._parse_item(item) for item in collection)
            cursor += len(collection)
            if cursor < total and len(papers) < max_results:
                time.sleep(0.4)
                payload = self._page(start_date, end_date, cursor)
        return papers[-max_results:]

    def _page(self, start_date: date, end_date: date, cursor: int) -> dict[str, Any]:
        url = f"{API_URL}/{start_date.isoformat()}/{end_date.isoformat()}/{cursor}/json"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    payload = json.load(response)
                messages = payload.get("messages") or []
                if messages and messages[0].get("status") != "ok":
                    raise BiorxivError(str(messages[0].get("status")))
                return payload
            except BiorxivError:
                raise
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code < 500 and exc.code != 429:
                    break
                if attempt < 3:
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
