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

