from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from bioai_pipeline.config import ARXIV_QUERIES, ARXIV_RSS_FEEDS, Settings
from bioai_pipeline.filtering import classify_with_rules
from bioai_pipeline.models import ArxivPaper, HeuristicResult
from bioai_pipeline.sources.arxiv import ArxivClient, ArxivRssClient


@dataclass(frozen=True)
class Candidate:
    paper: ArxivPaper
    heuristic: HeuristicResult


@dataclass(frozen=True)
class RunSummary:
    started_at: str
    finished_at: str
    fetched_count: int
    unique_count: int
    accepted_count: int
    rejected_count: int
    sample: tuple[dict[str, object], ...]


def _deduplicate(papers: Iterable[ArxivPaper]) -> list[ArxivPaper]:
    by_id: dict[str, ArxivPaper] = {}
    for paper in papers:
        existing = by_id.get(paper.arxiv_id)
        if existing is None or paper.version > existing.version:
            by_id[paper.arxiv_id] = paper
    return sorted(by_id.values(), key=lambda paper: paper.published_at, reverse=True)


def run_arxiv_ingest(
    settings: Settings,
    *,
    dry_run: bool,
    trigger: str,
    now: datetime | None = None,
) -> RunSummary:
    started = now or datetime.now(timezone.utc)
    window_start = started - timedelta(hours=settings.lookback_hours)
    fetched: list[ArxivPaper] = []

    if settings.arxiv_discovery_mode == "rss":
        client = ArxivRssClient()
        for name, categories in ARXIV_RSS_FEEDS.items():
            fetched.extend(client.fetch_daily(query_name=name, categories=categories))
    elif settings.arxiv_discovery_mode == "api":
        client = ArxivClient()
        for name, query in ARXIV_QUERIES.items():
            fetched.extend(
                client.fetch_recent(
                    query_name=name,
                    query=query,
                    start_at=window_start,
                    end_at=started,
                    max_results=settings.max_results_per_query,
                )
            )
    else:
        raise ValueError("ARXIV_DISCOVERY_MODE must be 'rss' or 'api'")

    unique = _deduplicate(fetched)
    candidates = [Candidate(paper, classify_with_rules(paper)) for paper in unique]
    accepted: list[Candidate] = []
    accepted_by_feed: dict[str, int] = {}
    for candidate in candidates:
        if not candidate.heuristic.accepted:
            continue
        feed_count = accepted_by_feed.get(candidate.paper.query_name, 0)
        if feed_count >= settings.max_results_per_query:
            continue
        accepted.append(candidate)
        accepted_by_feed[candidate.paper.query_name] = feed_count + 1

    if not dry_run:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required unless --dry-run is used")
        # Keep dry-runs dependency-light; psycopg is only needed for a real ingest.
        from bioai_pipeline.repository import Repository

        config = {
            "lookback_hours": settings.lookback_hours,
            "max_results_per_query": settings.max_results_per_query,
            "discovery_mode": settings.arxiv_discovery_mode,
            "query_names": list(ARXIV_RSS_FEEDS),
        }
        with Repository(settings.database_url) as repository:
            run_id = repository.start_run(trigger, config)
            try:
                for candidate in accepted:
                    repository.save_raw(candidate.paper, run_id)
                    repository.upsert_paper(candidate.paper, candidate.heuristic)
                repository.finish_run(
                    run_id,
                    status="succeeded",
                    fetched_count=len(unique),
                    accepted_count=len(accepted),
                )
            except Exception as exc:
                repository.finish_run(
                    run_id,
                    status="failed",
                    fetched_count=len(unique),
                    accepted_count=0,
                    error=str(exc)[:4000],
                )
                raise

    finished = datetime.now(timezone.utc)
    sample = tuple(
        {
            "arxiv_id": candidate.paper.arxiv_id,
            "title": candidate.paper.title,
            "published_at": candidate.paper.published_at.isoformat(),
            "categories": candidate.paper.categories,
            "topics": candidate.heuristic.topics,
            "rule_relevance": candidate.heuristic.relevance,
        }
        for candidate in accepted[:10]
    )
    return RunSummary(
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        fetched_count=len(fetched),
        unique_count=len(unique),
        accepted_count=len(accepted),
        rejected_count=len(unique) - len(accepted),
        sample=sample,
    )
