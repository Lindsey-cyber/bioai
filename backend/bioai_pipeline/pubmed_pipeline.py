from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bioai_pipeline.config import Settings
from bioai_pipeline.filtering import classify_with_rules
from bioai_pipeline.pipeline import Candidate, RunSummary, _deduplicate
from bioai_pipeline.sources.pubmed import PubmedClient


def run_pubmed_ingest(
    settings: Settings,
    *,
    dry_run: bool,
    trigger: str,
    now: datetime | None = None,
) -> RunSummary:
    started = now or datetime.now(timezone.utc)
    window_start = started - timedelta(hours=settings.lookback_hours)
    fetched = PubmedClient(
        email=settings.ncbi_email,
        api_key=settings.ncbi_api_key,
    ).fetch_recent(
        start_date=window_start.date(),
        end_date=started.date(),
        max_results=settings.pubmed_max_results,
    )
    unique = _deduplicate(fetched)
    candidates = [Candidate(paper, classify_with_rules(paper)) for paper in unique]
    accepted = [candidate for candidate in candidates if candidate.heuristic.accepted]

    if not dry_run:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required unless --dry-run is used")
        from bioai_pipeline.repository import Repository

        config = {
            "lookback_hours": settings.lookback_hours,
            "max_results": settings.pubmed_max_results,
            "endpoint": "ncbi_eutilities",
        }
        with Repository(settings.database_url) as repository:
            run_id = repository.start_run(trigger, config, source="pubmed")
            try:
                repository.save_raw_batch(unique, run_id)
                for candidate in accepted:
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
            "source_id": candidate.paper.arxiv_id,
            "title": candidate.paper.title,
            "published_at": candidate.paper.published_at.isoformat(),
            "journal": candidate.paper.source_metadata.get("journal"),
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
