import { NextResponse } from "next/server";
import { getDatabase } from "@/lib/server-database";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const sql = getDatabase();
  if (!sql) {
    return NextResponse.json({ configured: false }, { status: 503 });
  }

  try {
    const [runs, stories, failures, preferences, feedback] = await Promise.all([
      sql`
        select id::text, source, trigger, status, config, fetched_count,
               accepted_count, published_count, input_tokens, output_tokens,
               estimated_cost_usd::float8, error, started_at, finished_at
        from pipeline_runs
        order by started_at desc
        limit 12
      `,
      sql`
        select stories.id::text, papers.arxiv_id, papers.title, papers.topics,
               papers.authors, papers.affiliations,
               stories.global_importance::float8,
               stories.personal_relevance::float8,
               stories.freshness::float8, stories.confidence::float8,
               stories.final_score::float8, stories.is_exploration,
               stories.why_recommended, stories.published_at,
               explanation.model, explanation.prompt_version,
               explanation.input_tokens, explanation.output_tokens,
               explanation.estimated_cost_usd::float8
        from stories
        join papers on papers.id = stories.paper_id
        left join lateral (
          select model, prompt_version, input_tokens, output_tokens, estimated_cost_usd
          from explanations
          where explanations.story_id = stories.id
          order by explanations.created_at desc
          limit 1
        ) explanation on true
        order by stories.final_score desc
        limit 40
      `,
      sql`
        select arxiv_id, title, processing_status, processing_error, updated_at
        from papers
        where processing_error is not null
        order by updated_at desc
        limit 30
      `,
      sql`
        select topic_affinity, author_affinity, institution_affinity,
               source_affinity, technical_depth::float8,
               example_preference::float8, term_familiarity, updated_at
        from preference_profile
        where id = 'owner'
      `,
      sql`
        select feedback_events.id::text, feedback_events.event_type,
               feedback_events.entity_type, feedback_events.entity_id,
               feedback_events.metadata, feedback_events.created_at,
               papers.arxiv_id, papers.title
        from feedback_events
        left join stories on stories.id = feedback_events.story_id
        left join papers on papers.id = stories.paper_id
        order by feedback_events.created_at desc
        limit 80
      `,
    ]);

    return NextResponse.json(
      {
        configured: true,
        generatedAt: new Date().toISOString(),
        runs,
        stories,
        failures,
        preference: preferences[0] || null,
        feedback,
      },
      { headers: { "Cache-Control": "private, no-store" } },
    );
  } catch (error) {
    console.error("Debug query failed", error);
    return NextResponse.json({ configured: true, error: "debug_unavailable" }, { status: 503 });
  }
}
