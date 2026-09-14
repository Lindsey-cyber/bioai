from __future__ import annotations

import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

from bioai_pipeline.models import ArxivPaper, Author


API_URL = "https://export.arxiv.org/api/query"
RSS_URL = "https://rss.arxiv.org/atom"
USER_AGENT = "bioai-feed/0.1 (personal research reader; https://github.com/Lindsey-cyber/bioai)"
ATOM = "http://www.w3.org/2005/Atom"
ARXIV = "http://arxiv.org/schemas/atom"
OPENSEARCH = "http://a9.com/-/spec/opensearch/1.1/"
DC = "http://purl.org/dc/elements/1.1/"
NS = {"atom": ATOM, "arxiv": ARXIV, "opensearch": OPENSEARCH, "dc": DC}
ARXIV_ID_RE = re.compile(r"/abs/(?P<id>.+?)(?:v(?P<version>\d+))?$")
OAI_ID_RE = re.compile(r"arXiv\.org:(?P<id>.+?)(?:v(?P<version>\d+))?$")


class ArxivError(RuntimeError):
    pass


class ArxivClient:
    def __init__(self, page_size: int = 100, request_delay_seconds: float = 3.0):
        self.page_size = min(max(page_size, 1), 2000)
        self.request_delay_seconds = max(request_delay_seconds, 3.0)
        self._last_request_at: float | None = None

    def fetch_recent(
        self,
        *,
        query_name: str,
        query: str,
        start_at: datetime,
        end_at: datetime,
        max_results: int,
    ) -> list[ArxivPaper]:
        date_clause = (
            f"submittedDate:[{start_at:%Y%m%d%H%M} TO {end_at:%Y%m%d%H%M}]"
        )
        search_query = f"({query}) AND {date_clause}"
        papers: list[ArxivPaper] = []
        offset = 0

        while offset < max_results:
            page_limit = min(self.page_size, max_results - offset)
            params = urllib.parse.urlencode(
                {
                    "search_query": search_query,
                    "start": offset,
                    "max_results": page_limit,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }
            )
            payload = self._get(f"{API_URL}?{params}")
            root = ET.fromstring(payload)
            entries = root.findall("atom:entry", NS)
            papers.extend(self._parse_entry(entry, query_name) for entry in entries)

            total_node = root.find("opensearch:totalResults", NS)
            total = int(total_node.text) if total_node is not None and total_node.text else 0
            offset += len(entries)
            if not entries or offset >= min(total, max_results):
                break
        return papers

    def _get(self, url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/atom+xml"},
        )
        last_error: Exception | None = None
        for attempt in range(4):
            if self._last_request_at is not None:
                remaining = self.request_delay_seconds - (time.monotonic() - self._last_request_at)
                if remaining > 0:
                    time.sleep(remaining)
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    payload = response.read()
                    self._last_request_at = time.monotonic()
                    # arXiv occasionally returns this plain-text body with HTTP 200.
                    if payload.strip().lower().startswith(b"rate exceeded"):
                        last_error = ArxivError("arXiv rate limit response")
                        if attempt < 3:
                            time.sleep(5 * (attempt + 1))
                            continue
                        break
                    return payload
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                self._last_request_at = time.monotonic()
                last_error = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code < 500 and exc.code != 429:
                    break
                if attempt < 3:
                    time.sleep(2**attempt)
        raise ArxivError(f"arXiv request failed after retries: {last_error}")

    @staticmethod
    def _text(entry: ET.Element, path: str) -> str | None:
        node = entry.find(path, NS)
        if node is None or not node.text:
            return None
        return " ".join(node.text.split())

    def _parse_entry(self, entry: ET.Element, query_name: str) -> ArxivPaper:
        entry_id = self._text(entry, "atom:id") or ""
        links = entry.findall("atom:link", NS)
        abstract_url = next(
            (
                link.attrib["href"]
                for link in links
                if link.attrib.get("rel") == "alternate" and "href" in link.attrib
            ),
            entry_id,
        )
        match = ARXIV_ID_RE.search(abstract_url) or OAI_ID_RE.search(entry_id)
        if not match:
            raise ArxivError(f"Unrecognized arXiv entry id: {entry_id}")

        authors = []
        for node in entry.findall("atom:author", NS):
            name = self._text(node, "atom:name") or "Unknown"
            affiliation = self._text(node, "arxiv:affiliation")
            authors.append(Author(name=name, affiliation=affiliation))
        if not authors:
            creator = self._text(entry, "dc:creator")
            if creator:
                authors.extend(Author(name=name.strip()) for name in creator.split(",") if name.strip())

        pdf_url = next(
            (
                link.attrib["href"]
                for link in links
                if link.attrib.get("title") == "pdf" and "href" in link.attrib
            ),
            f"https://arxiv.org/pdf/{match.group('id')}",
        )
        categories = tuple(
            node.attrib["term"]
            for node in entry.findall("atom:category", NS)
            if node.attrib.get("term")
        )
        primary_node = entry.find("arxiv:primary_category", NS)
        summary = self._text(entry, "atom:summary") or ""
        summary = re.sub(r"^arXiv:.*?Abstract:\s*", "", summary, flags=re.IGNORECASE)
        announce_type = self._text(entry, "arxiv:announce_type")

        return ArxivPaper(
            arxiv_id=match.group("id"),
            version=int(match.group("version") or 1),
            title=self._text(entry, "atom:title") or "Untitled",
            abstract=summary,
            authors=tuple(authors),
            categories=categories,
            primary_category=(
                primary_node.attrib.get("term")
                if primary_node is not None
                else (categories[0] if categories else None)
            ),
            published_at=datetime.fromisoformat(self._text(entry, "atom:published") or ""),
            updated_at=datetime.fromisoformat(self._text(entry, "atom:updated") or ""),
            abstract_url=abstract_url,
            pdf_url=pdf_url.replace("http://", "https://"),
            doi=self._text(entry, "arxiv:doi") or self._text(entry, "arxiv:DOI"),
            comment=self._text(entry, "arxiv:comment"),
            query_name=query_name,
            raw_xml=ET.tostring(entry, encoding="unicode"),
            announce_type=announce_type,
        )


class ArxivRssClient(ArxivClient):
    """Daily discovery through arXiv's cache-friendly official Atom feeds."""

    def fetch_daily(self, *, query_name: str, categories: tuple[str, ...]) -> list[ArxivPaper]:
        category_path = "+".join(categories)
        payload = self._get(f"{RSS_URL}/{category_path}")
        root = ET.fromstring(payload)
        papers = [self._parse_entry(entry, query_name) for entry in root.findall("atom:entry", NS)]
        # Replacements are updates to already-announced papers, not new feed stories.
        return [paper for paper in papers if paper.announce_type in {None, "new", "cross"}]
