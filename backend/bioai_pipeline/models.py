from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Author:
    name: str
    affiliation: str | None = None


@dataclass(frozen=True)
class ArxivPaper:
    arxiv_id: str
    version: int
    title: str
    abstract: str
    authors: tuple[Author, ...]
    categories: tuple[str, ...]
    primary_category: str | None
    published_at: datetime
    updated_at: datetime
    abstract_url: str
    pdf_url: str
    doi: str | None
    comment: str | None
    query_name: str
    raw_xml: str
    announce_type: str | None = None

    def raw_payload(self) -> dict[str, Any]:
        value = asdict(self)
        value["published_at"] = self.published_at.isoformat()
        value["updated_at"] = self.updated_at.isoformat()
        return value


@dataclass(frozen=True)
class HeuristicResult:
    accepted: bool
    relevance: float
    topics: tuple[str, ...]
    matched_ai_terms: tuple[str, ...]
    matched_bio_terms: tuple[str, ...]


@dataclass(frozen=True)
class PaperRecord:
    id: str
    arxiv_id: str
    latest_version: int
    title: str
    abstract: str
    authors: tuple[dict[str, Any], ...]
    categories: tuple[str, ...]
    published_at: datetime
    abstract_url: str
    pdf_url: str
    geography_status: str
    country_codes: tuple[str, ...]
    processing_status: str
    source_metadata: dict[str, Any]


@dataclass(frozen=True)
class OpenAlexMetadata:
    openalex_id: str
    title: str
    title_similarity: float
    authors: tuple[dict[str, Any], ...]
    institutions: tuple[dict[str, Any], ...]
    country_codes: tuple[str, ...]
    primary_location: dict[str, Any] | None
    doi: str | None
    raw: dict[str, Any]
