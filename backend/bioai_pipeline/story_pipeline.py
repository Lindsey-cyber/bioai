from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from bioai_pipeline.ai import FastAssessment, FastAssessmentBatch, OpenAIProcessor, StoryExplanation
from bioai_pipeline.config import Settings
from bioai_pipeline.models import PaperRecord
from bioai_pipeline.repository import Repository
from bioai_pipeline.sources.openalex import OpenAlexClient
from bioai_pipeline.sources.pdf import PdfTextClient


@dataclass(frozen=True)
class ProcessingSummary:
    started_at: str
    finished_at: str
    considered_count: int
    geography_eligible_count: int
    geography_ineligible_count: int
    geography_unresolved_count: int
    fast_accepted_count: int
    fast_rejected_count: int
    published_count: int
    error_count: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    published: tuple[dict[str, object], ...]


def _personal_relevance(topics: list[str], affinities: dict[str, float]) -> float:
    if not topics:
        return 0.5
    return round(sum(affinities.get(topic, 0.5) for topic in topics) / len(topics), 4)


def _freshness(published_at: datetime, now: datetime) -> float:
    age_hours = max(0.0, (now - published_at.astimezone(timezone.utc)).total_seconds() / 3600)
    return round(0.5 ** (age_hours / (24 * 7)), 4)


def _final_score(
    settings: Settings,
    *,
    importance: float,
    personal: float,
    freshness: float,
    confidence: float,
) -> float:
    score = (
        settings.rank_global_weight * importance
        + settings.rank_personal_weight * personal
        + settings.rank_freshness_weight * freshness
        + settings.rank_confidence_weight * confidence
    )
    return round(max(0.0, min(1.0, score)), 4)


def run_story_processing(
    settings: Settings,
    *,
    trigger: str,
    max_papers: int = 60,
    max_sol_stories: int | None = None,
    now: datetime | None = None,
) -> ProcessingSummary:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for story processing")
    if not settings.openalex_api_key:
        raise RuntimeError("OPENALEX_API_KEY is required for geography metadata")

    started = now or datetime.now(timezone.utc)
    sol_limit = (
        settings.max_sol_stories_per_day
        if max_sol_stories is None
        else max_sol_stories
    )
    openalex = OpenAlexClient(settings.openalex_api_key, settings.openalex_match_threshold)
    ai = OpenAIProcessor(settings)
    pdf = PdfTextClient()

    eligible_count = 0
    ineligible_count = 0
    unresolved_count = 0
    fast_accepted = 0
    fast_rejected = 0
    published_rows: list[dict[str, object]] = []
    errors: list[str] = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0

    config = {
        "max_papers": max_papers,
        "max_sol_stories": sol_limit,
        "fast_model": settings.fast_model,
        "deep_model": settings.deep_model,
        "prompt_version": settings.prompt_version,
        "allowed_country_codes": sorted(settings.allowed_country_codes),
    }

    with Repository(settings.database_url) as repository:
        run_id = repository.start_run(trigger, config, source="ai_processing")
        candidates = repository.list_processing_candidates(max_papers)
        try:
            for paper in candidates:
                if paper.geography_status == "eligible":
                    eligible_count += 1
                    continue
                if paper.geography_status == "ineligible":
                    ineligible_count += 1
                    continue
                try:
                    metadata = openalex.lookup_by_title(paper.title)
                    status = repository.save_openalex_metadata(
                        paper.id, metadata, settings.allowed_country_codes
                    )
                    if status == "eligible":
                        eligible_count += 1
                    elif status == "ineligible":
                        ineligible_count += 1
                    else:
                        unresolved_count += 1
                except Exception as exc:
                    errors.append(f"{paper.arxiv_id}: metadata: {exc}")
                    repository.mark_processing_error(paper.id, str(exc))

            refreshed = repository.list_processing_candidates(max_papers)
            fast_papers = [
                paper
                for paper in refreshed
                if paper.geography_status == "eligible"
                and paper.processing_status == "metadata_ready"
                and not paper.source_metadata.get("fast_assessment")
            ]
            if fast_papers:
                fast_result = ai.assess_batch(fast_papers)
                batch = fast_result.value
                if not isinstance(batch, FastAssessmentBatch):
                    raise RuntimeError("Unexpected fast assessment result type")
                total_input_tokens += fast_result.input_tokens
                total_output_tokens += fast_result.output_tokens
                total_cost += fast_result.estimated_cost_usd
                by_arxiv_id = {paper.arxiv_id: paper for paper in fast_papers}
                divisor = max(1, len(batch.assessments))
                for assessment in batch.assessments:
                    paper = by_arxiv_id[assessment.arxiv_id]
                    repository.save_fast_assessment(
                        paper.id,
                        assessment,
                        model=fast_result.model,
                        prompt_version=settings.prompt_version,
                        input_tokens=round(fast_result.input_tokens / divisor),
                        output_tokens=round(fast_result.output_tokens / divisor),
                        estimated_cost_usd=round(fast_result.estimated_cost_usd / divisor, 6),
                    )
                    if assessment.is_relevant:
                        fast_accepted += 1
                    else:
                        fast_rejected += 1

            affinities = repository.preference_topic_affinity()
            deep_candidates = repository.list_deep_candidates(sol_limit)
            max_chars = max(8_000, (settings.sol_max_input_tokens - 2_500) * 4)
            for paper in deep_candidates:
                try:
                    assessment = FastAssessment.model_validate(
                        paper.source_metadata["fast_assessment"]
                    )
                    paper_text = pdf.fetch_text(paper.pdf_url, max_chars=max_chars)
                    if len(paper_text) < 1_000:
                        raise RuntimeError("Extracted PDF text was unexpectedly short")
                    repository.save_pdf_text(paper, run_id, paper_text)
                    deep_result = ai.explain(paper, assessment, paper_text)
                    explanation = deep_result.value
                    if not isinstance(explanation, StoryExplanation):
                        raise RuntimeError("Unexpected deep explanation result type")

                    personal = _personal_relevance(list(assessment.topics), affinities)
                    freshness = _freshness(paper.published_at, started)
                    final_score = _final_score(
                        settings,
                        importance=assessment.global_importance,
                        personal=personal,
                        freshness=freshness,
                        confidence=assessment.confidence,
                    )
                    story_id = repository.publish_story(
                        paper,
                        assessment,
                        explanation,
                        model=deep_result.model,
                        prompt_version=settings.prompt_version,
                        input_tokens=deep_result.input_tokens,
                        output_tokens=deep_result.output_tokens,
                        estimated_cost_usd=deep_result.estimated_cost_usd,
                        personal_relevance=personal,
                        freshness=freshness,
                        final_score=final_score,
                    )
                    total_input_tokens += deep_result.input_tokens
                    total_output_tokens += deep_result.output_tokens
                    total_cost += deep_result.estimated_cost_usd
                    published_rows.append(
                        {
                            "story_id": story_id,
                            "arxiv_id": paper.arxiv_id,
                            "title": paper.title,
                            "model": deep_result.model,
                            "final_score": final_score,
                            "cost_usd": deep_result.estimated_cost_usd,
                        }
                    )
                except Exception as exc:
                    errors.append(f"{paper.arxiv_id}: deep: {exc}")
                    repository.mark_processing_error(paper.id, str(exc))

            repository.finish_run(
                run_id,
                status="succeeded",
                fetched_count=len(candidates),
                accepted_count=fast_accepted,
                published_count=len(published_rows),
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                estimated_cost_usd=round(total_cost, 6),
                error="\n".join(errors)[:4000] if errors else None,
            )
        except Exception as exc:
            repository.finish_run(
                run_id,
                status="failed",
                fetched_count=len(candidates),
                accepted_count=fast_accepted,
                published_count=len(published_rows),
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                estimated_cost_usd=round(total_cost, 6),
                error=str(exc)[:4000],
            )
            raise

    finished = datetime.now(timezone.utc)
    return ProcessingSummary(
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        considered_count=len(candidates),
        geography_eligible_count=eligible_count,
        geography_ineligible_count=ineligible_count,
        geography_unresolved_count=unresolved_count,
        fast_accepted_count=fast_accepted,
        fast_rejected_count=fast_rejected,
        published_count=len(published_rows),
        error_count=len(errors),
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        estimated_cost_usd=round(total_cost, 6),
        published=tuple(published_rows),
    )
