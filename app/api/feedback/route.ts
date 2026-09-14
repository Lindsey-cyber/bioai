import { NextRequest, NextResponse } from "next/server";
import { getDatabase } from "@/lib/server-database";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const eventTypes = [
  "too_complex",
  "too_simple",
  "more_like_this",
  "less_like_this",
  "more_examples",
] as const;

type EventType = (typeof eventTypes)[number];
type Affinity = Record<string, number>;
type JsonObject = Record<string, unknown>;

type FeedbackBody = {
  eventId?: string;
  storyId?: string;
  eventType?: EventType;
  active?: boolean;
};

type StoryContext = {
  topics: string[];
  authors: JsonObject[];
  affiliations: JsonObject[];
  source: string;
};

type ProfileRow = {
  topic_affinity: Affinity;
  author_affinity: Affinity;
  institution_affinity: Affinity;
  source_affinity: Affinity;
  technical_depth: number;
  example_preference: number;
};

type RankingRow = StoryContext & {
  story_id: string;
  global_importance: number;
  freshness: number;
  confidence: number;
};

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function numberSetting(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) ? value : fallback;
}

function clamp(value: number, minimum = 0, maximum = 1) {
  return Math.min(maximum, Math.max(minimum, value));
}

function bump(affinity: Affinity, keys: string[], delta: number) {
  for (const key of new Set(keys.filter(Boolean))) {
    affinity[key] = Number(clamp(Number(affinity[key] ?? 0.5) + delta).toFixed(4));
  }
}

function authorKeys(authors: JsonObject[]) {
  return authors.map((author) => String(author.id || author.name || "")).filter(Boolean);
}

function institutionKeys(context: StoryContext) {
  const institutions = [...(context.affiliations || [])];
  for (const author of context.authors || []) {
    if (Array.isArray(author.institutions)) institutions.push(...author.institutions as JsonObject[]);
  }
  return institutions.map((institution) => String(institution.id || institution.name || "")).filter(Boolean);
}

function affinityScore(affinity: Affinity, keys: string[]) {
  const unique = [...new Set(keys.filter(Boolean))];
  if (!unique.length) return null;
  return unique.reduce((total, key) => total + Number(affinity[key] ?? 0.5), 0) / unique.length;
}

function personalRelevance(profile: ProfileRow, story: RankingRow) {
  const signals = [
    [numberSetting("PERSONAL_TOPIC_WEIGHT", 0.5), affinityScore(profile.topic_affinity, story.topics || [])],
    [numberSetting("PERSONAL_AUTHOR_WEIGHT", 0.2), affinityScore(profile.author_affinity, authorKeys(story.authors || []))],
    [numberSetting("PERSONAL_INSTITUTION_WEIGHT", 0.2), affinityScore(profile.institution_affinity, institutionKeys(story))],
    [numberSetting("PERSONAL_SOURCE_WEIGHT", 0.1), affinityScore(profile.source_affinity, [story.source || "arxiv"])],
  ] as const;
  const available = signals.filter((signal): signal is readonly [number, number] => signal[1] !== null);
  const totalWeight = available.reduce((total, [weight]) => total + weight, 0);
  if (!totalWeight) return 0.5;
  return clamp(available.reduce((total, [weight, value]) => total + weight * value, 0) / totalWeight);
}

export async function POST(request: NextRequest) {
  const sql = getDatabase();
  if (!sql) return NextResponse.json({ error: "database_not_configured" }, { status: 503 });

  let body: FeedbackBody;
  try {
    body = await request.json() as FeedbackBody;
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }
  if (!body.eventId || !uuidPattern.test(body.eventId) || !body.storyId || !uuidPattern.test(body.storyId)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  if (!body.eventType || !eventTypes.includes(body.eventType)) {
    return NextResponse.json({ error: "invalid_event_type" }, { status: 400 });
  }
  const eventId = body.eventId;
  const storyId = body.storyId;
  const eventType = body.eventType;

  try {
    const result = await sql.begin(async (transaction) => {
      // postgres-js transactions are callable at runtime; its published
      // TransactionSql type loses the tagged-template signature through Omit.
      const tx = transaction as unknown as typeof sql;
      const contexts = await tx`
        select papers.topics, papers.authors, papers.affiliations,
               coalesce(papers.source_metadata->>'source', 'arxiv') as source
        from stories
        join papers on papers.id = stories.paper_id
        where stories.id = ${storyId}
        limit 1
      `;
      if (!contexts.length) return { error: "story_not_found" as const };

      const inserted = await tx`
        insert into feedback_events (id, story_id, event_type, metadata)
        values (
          ${eventId},
          ${storyId},
          ${eventType},
          ${tx.json({ active: body.active !== false })}
        )
        on conflict (id) do nothing
        returning id::text
      `;
      if (!inserted.length) return { duplicate: true as const };

      const rows = await tx`
        select topic_affinity, author_affinity, institution_affinity,
               source_affinity, technical_depth::float8, example_preference::float8
        from preference_profile
        where id = 'owner'
        for update
      `;
      if (!rows.length) throw new Error("Owner preference profile is missing");

      const storedProfile = rows[0] as unknown as ProfileRow;
      const profile: ProfileRow = {
        ...storedProfile,
        topic_affinity: { ...(storedProfile.topic_affinity || {}) },
        author_affinity: { ...(storedProfile.author_affinity || {}) },
        institution_affinity: { ...(storedProfile.institution_affinity || {}) },
        source_affinity: { ...(storedProfile.source_affinity || {}) },
      };
      const direction = body.active === false ? -1 : 1;
      const explanationDelta = numberSetting("FEEDBACK_EXPLANATION_WEIGHT", 0.08) * direction;
      const contentDelta = numberSetting("FEEDBACK_CONTENT_WEIGHT", 0.12) * direction;
      const context = contexts[0] as unknown as StoryContext;

      if (eventType === "too_complex") profile.technical_depth = clamp(Number(profile.technical_depth) - explanationDelta);
      if (eventType === "too_simple") profile.technical_depth = clamp(Number(profile.technical_depth) + explanationDelta);
      if (eventType === "more_examples") profile.example_preference = clamp(Number(profile.example_preference) + explanationDelta);
      if (eventType === "more_like_this" || eventType === "less_like_this") {
        const preferenceDirection = eventType === "more_like_this" ? 1 : -1;
        const delta = contentDelta * preferenceDirection;
        bump(profile.topic_affinity, context.topics || [], delta);
        bump(profile.author_affinity, authorKeys(context.authors || []), delta);
        bump(profile.institution_affinity, institutionKeys(context), delta);
        bump(profile.source_affinity, [context.source || "arxiv"], delta);
      }

      await tx`
        update preference_profile
        set topic_affinity = ${tx.json(profile.topic_affinity)},
            author_affinity = ${tx.json(profile.author_affinity)},
            institution_affinity = ${tx.json(profile.institution_affinity)},
            source_affinity = ${tx.json(profile.source_affinity)},
            technical_depth = ${profile.technical_depth},
            example_preference = ${profile.example_preference},
            updated_at = now()
        where id = 'owner'
      `;

      const rankingRows = await tx`
        select stories.id::text as story_id,
               stories.global_importance::float8,
               stories.freshness::float8,
               stories.confidence::float8,
               papers.topics, papers.authors, papers.affiliations,
               coalesce(papers.source_metadata->>'source', 'arxiv') as source
        from stories
        join papers on papers.id = stories.paper_id
        where stories.status = 'published'
      `;
      const globalWeight = numberSetting("RANK_GLOBAL_WEIGHT", 0.55);
      const personalWeight = numberSetting("RANK_PERSONAL_WEIGHT", 0.30);
      const freshnessWeight = numberSetting("RANK_FRESHNESS_WEIGHT", 0.10);
      const confidenceWeight = numberSetting("RANK_CONFIDENCE_WEIGHT", 0.05);
      for (const rawStory of rankingRows) {
        const story = rawStory as unknown as RankingRow;
        const relevance = personalRelevance(profile, story);
        const finalScore = clamp(
          story.global_importance * globalWeight +
          relevance * personalWeight +
          story.freshness * freshnessWeight +
          story.confidence * confidenceWeight,
        );
        await tx`
          update stories
          set personal_relevance = ${relevance},
              final_score = ${finalScore},
              updated_at = now()
          where id = ${story.story_id}
        `;
      }

      return {
        updated: true as const,
        preference: {
          technicalDepth: profile.technical_depth,
          examplePreference: profile.example_preference,
          topicAffinity: profile.topic_affinity,
        },
      };
    });

    if ("error" in result) return NextResponse.json(result, { status: 404 });
    return NextResponse.json(result);
  } catch (error) {
    console.error("Feedback update failed", error);
    return NextResponse.json({ error: "feedback_unavailable" }, { status: 503 });
  }
}
