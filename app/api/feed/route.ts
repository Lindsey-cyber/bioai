import { NextRequest, NextResponse } from "next/server";
import { getDatabase } from "@/lib/server-database";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type JsonObject = Record<string, unknown>;

type FeedRow = {
  id: string;
  slug: string;
  global_importance: number;
  personal_relevance: number;
  final_score: number;
  is_exploration: boolean;
  published_at: string;
  arxiv_id: string;
  title: string;
  authors: JsonObject[];
  affiliations: JsonObject[];
  topics: string[];
  abstract_url: string;
  source_comment: string | null;
  content: {
    title_zh?: string;
    sections?: Record<string, { simple?: string; professional?: string; simple_en?: string; professional_en?: string }>;
    limitations_en?: string[];
  };
  limitations: string[];
  terminology: Array<{
    chinese_name?: string;
    english_term?: string;
    abbreviation?: string;
    chinese_explanation?: string;
    english_explanation?: string;
  }>;
  sources: Array<{ label: string; url: string; is_original: boolean }>;
};

const sectionMap = [
  ["what_happened", "发生了什么？"],
  ["problem", "他们想解决什么？"],
  ["approach", "怎么做的？"],
  ["results", "结果怎么样？"],
  ["why_it_matters", "为什么值得我知道？"],
] as const;

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "?";
}

function safeId(prefix: string, value: string) {
  const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  let hash = 0;
  for (const character of value) hash = ((hash << 5) - hash + character.charCodeAt(0)) | 0;
  return `${prefix}-${slug || "entity"}-${Math.abs(hash).toString(36)}`;
}

function selectCoreAuthors(authors: JsonObject[]) {
  if (authors.length <= 3 || !authors.some((author) => author.position || author.is_corresponding)) {
    return authors.slice(0, 3);
  }
  const selected: JsonObject[] = [];
  for (const author of authors) {
    if (author.position === "first" || author.position === "last" || author.is_corresponding) {
      if (!selected.includes(author)) selected.push(author);
    }
  }
  for (const author of authors) {
    if (selected.length >= 3) break;
    if (!selected.includes(author)) selected.push(author);
  }
  return selected.slice(0, 3);
}

function formatAge(value: string) {
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const hours = Math.floor(elapsed / 3_600_000);
  if (hours < 1) return "刚刚";
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "昨天" : `${days} 天前`;
}

const modelMetaMarkers = [
  /\bneed\s+(?:to\s+)?(?:be\s+)?chinese\b/i,
  /\blet(?:'|’)s\s+(?:revise|rewrite|fix|continue)\b/i,
  /\bwait,?\s+(?:already|before|need|the)\b/i,
  /\b(?:valid|correct)\s+json\b/i,
  /\bfinal\s+generation\b/i,
  /\bcurrent\s+string\b/i,
];

function sanitizeGeneratedText(value: string) {
  let cutoff = value.length;
  for (const marker of modelMetaMarkers) {
    const match = marker.exec(value);
    if (match?.index !== undefined) cutoff = Math.min(cutoff, match.index);
  }
  return value.slice(0, cutoff).trim().replace(/[，,;；:\s]+$/, "");
}

function transformRow(row: FeedRow) {
  const terms = (row.terminology || []).map((term) => ({
    zh: String(term.chinese_name || ""),
    en: String(term.english_term || ""),
    abbr: String(term.abbreviation || "") || undefined,
    zhExplanation: String(term.chinese_explanation || ""),
    enExplanation: String(term.english_explanation || ""),
  }));

  const people = selectCoreAuthors(row.authors || []).map((author) => {
    const name = String(author.name || "Unknown author");
    const currentInstitutions = Array.isArray(author.last_known_institutions) ? author.last_known_institutions as JsonObject[] : [];
    const paperInstitutions = Array.isArray(author.institutions) ? author.institutions as JsonObject[] : [];
    const authorInstitutions = currentInstitutions.length ? currentInstitutions : paperInstitutions;
    const affiliation = String(
      authorInstitutions[0]?.name || author.affiliation || "机构信息待核实",
    );
    const researchTopics = Array.isArray(author.research_topics)
      ? author.research_topics.map(String).filter(Boolean).slice(0, 5)
      : [];
    const worksCount = Number(author.works_count || 0);
    const citedByCount = Number(author.cited_by_count || 0);
    const representativeWorks = Array.isArray(author.representative_works)
      ? author.representative_works as JsonObject[]
      : [];
    const noteByReason: Record<string, { zh: string; en: string }> = {
      highly_cited: { zh: "按引用与学术影响选取", en: "Selected for scholarly impact" },
      current_direction: { zh: "代表近期研究方向", en: "Represents recent research direction" },
      related_to_story: { zh: "与当前 Story 最相关", en: "Most relevant to this story" },
      representative: { zh: "代表性研究", en: "Representative work" },
    };
    const role = author.position === "first" && author.is_corresponding
      ? "First & corresponding author"
      : author.position === "first"
        ? "First author"
        : author.is_corresponding
          ? "Corresponding author"
          : author.position === "last"
            ? "Senior / last author"
            : "Author";
    return {
      id: safeId("author", String(author.id || name)),
      initials: initials(name),
      name,
      role,
      institution: affiliation,
      focus: researchTopics.length ? researchTopics : row.topics || [],
      bio: author.profile_verified
        ? `OpenAlex 已用稳定作者 ID 核实该作者；目前收录约 ${worksCount} 篇作品、${citedByCount} 次引用。`
        : "作者身份尚未完成可靠核实；因此暂不展示照片或推测性履历。",
      bioEn: author.profile_verified
        ? `Verified by a stable OpenAlex author ID, with approximately ${worksCount} indexed works and ${citedByCount} citations.`
        : "This identity has not yet been reliably verified, so no photo or inferred biography is shown.",
      career: author.profile_verified
        ? `当前机构来自 OpenAlex 的 last-known institution。教育经历尚无可靠来源，暂不补写。`
        : "可靠的教育和职业经历尚未补全。",
      careerEn: author.profile_verified
        ? "The current affiliation is OpenAlex's last-known institution. Verified education history is not yet available."
        : "Verified education and career history is not yet available.",
      profileUrl: String(author.openalex_url || "") || undefined,
      orcid: String(author.orcid || "") || undefined,
      papers: representativeWorks.map((work) => {
        const reason = noteByReason[String(work.selection_reason || "representative")] || noteByReason.representative;
        return {
          title: String(work.title || "Untitled work"),
          year: Number(work.year || new Date().getFullYear()),
          note: reason.zh,
          noteEn: reason.en,
          url: String(work.url || work.id || "") || undefined,
        };
      }).slice(0, 3),
    };
  });

  const affiliations = [...(row.affiliations || [])];
  for (const author of row.authors || []) {
    if (Array.isArray(author.institutions)) affiliations.push(...author.institutions as JsonObject[]);
  }
  const seenInstitutions = new Set<string>();
  const institutions = affiliations.flatMap((institution) => {
    const name = String(institution.name || "");
    const institutionKey = String(institution.id || name);
    if (!name || seenInstitutions.has(institutionKey)) return [];
    seenInstitutions.add(institutionKey);
    const countryCode = String(institution.country_code || "");
    const location = institution.location && typeof institution.location === "object" ? institution.location as JsonObject : {};
    const locationText = [location.city, location.region, location.country].map(String).filter((value) => value && value !== "undefined").join(", ") || countryCode || "地点待核实";
    const researchTopics = Array.isArray(institution.research_topics)
      ? institution.research_topics.map(String).filter(Boolean).slice(0, 5)
      : row.topics || [];
    const kind = String(institution.type || "Research institution");
    const verified = Boolean(institution.profile_verified);
    return [{
      id: safeId("institution", String(institution.id || name)),
      name,
      short: name.split(/\s+/).slice(0, 3).map((part) => part[0]).join("").toUpperCase(),
      location: locationText,
      kind,
      description: verified ? `OpenAlex 已核实这是一个 ${kind} 类型机构，地点为 ${locationText}。` : "机构资料正在核实中。",
      descriptionEn: verified ? `OpenAlex identifies this as a ${kind} institution located in ${locationText}.` : "Verified institution information is being prepared.",
      direction: researchTopics.join("、"),
      directionEn: researchTopics.join(" · "),
      why: "该机构参与了这项最新研究。",
      whyEn: "This institution is linked to the authorship record for the featured research.",
      profileUrl: String(institution.homepage_url || institution.openalex_url || "") || undefined,
      researchers: people.filter((person) => person.institution === name).map((person) => person.id),
    }];
  }).slice(0, 3);

  const sections = sectionMap.map(([key, title], index) => {
    const value = row.content?.sections?.[key] || {};
    return {
      title,
      simple: String(value.simple || "解释正在生成。"),
      professional: String(value.professional || "专业解释正在生成。"),
      titleEn: ["What happened?", "What problem are they solving?", "How did they do it?", "What were the results?", "Why should I know about it?"][index],
      simpleEn: String(value.simple_en || "English overview is being prepared."),
      professionalEn: String(value.professional_en || "A complete English translation of the Chinese professional explanation is being prepared."),
      terms: index === 2 ? terms : undefined,
    };
  });
  const sources = row.sources?.length
    ? row.sources
    : [{ label: "arXiv", url: row.abstract_url, is_original: true }];
  const originalSource = sources.find((source) => source.is_original) || sources[0];

  return {
    id: row.id,
    source: originalSource?.label || "Original source",
    sourceType: originalSource?.label === "bioRxiv"
      ? "preprint"
      : originalSource?.label === "PubMed"
        ? String(row.source_comment || "journal article")
        : "paper",
    age: formatAge(row.published_at),
    date: new Date(row.published_at).toISOString().slice(0, 10),
    title: row.title,
    titleZh: String(row.content?.title_zh || row.title),
    topics: row.topics || [],
    importance: Number(row.global_importance || 0),
    relevance: Number(row.personal_relevance || 0),
    finalScore: Number(row.final_score || 0),
    sections,
    limitation: (row.limitations || [])
      .map((item) => sanitizeGeneratedText(String(item)))
      .filter(Boolean)
      .join("；") || undefined,
    limitationEn: (row.content?.limitations_en || [])
      .map((item) => sanitizeGeneratedText(String(item)))
      .filter(Boolean)
      .join("; ") || undefined,
    authors: people.map((person) => person.id),
    institutions: institutions.map((institution) => institution.id),
    people,
    institutionDetails: institutions,
    sources: sources.map((source) => source.label),
    sourceLinks: sources,
    originalUrl: originalSource?.url || row.abstract_url,
    exploration: Boolean(row.is_exploration),
  };
}

export async function GET(request: NextRequest) {
  const sql = getDatabase();
  if (!sql) {
    return NextResponse.json({ stories: [], configured: false });
  }

  try {
    const mode = request.nextUrl.searchParams.get("mode") === "latest" ? "latest" : "for-you";
    const rows = await sql<FeedRow[]>`
      select
        stories.id::text,
        stories.slug,
        stories.global_importance::float8,
        stories.personal_relevance::float8,
        stories.final_score::float8,
        stories.is_exploration,
        stories.published_at,
        papers.arxiv_id,
        papers.title,
        papers.authors,
        papers.affiliations,
        papers.topics,
        papers.abstract_url,
        papers.source_comment,
        explanation.content,
        explanation.limitations,
        explanation.terminology,
        coalesce(sources.items, '[]'::json) as sources
      from stories
      join papers on papers.id = stories.paper_id
      join lateral (
        select content, limitations, terminology
        from explanations
        where explanations.story_id = stories.id
        order by explanations.created_at desc
        limit 1
      ) explanation on true
      left join lateral (
        select json_agg(
          json_build_object(
            'label', story_sources.label,
            'url', story_sources.url,
            'is_original', story_sources.is_original
          ) order by story_sources.is_original desc, story_sources.created_at
        ) as items
        from story_sources
        where story_sources.story_id = stories.id
      ) sources on true
      where stories.status = 'published'
      order by
        case when ${mode} = 'latest' then stories.published_at end desc,
        case when ${mode} = 'for-you' then stories.final_score end desc,
        stories.published_at desc
      limit 40
    `;
    return NextResponse.json(
      { stories: rows.map(transformRow), configured: true },
      { headers: { "Cache-Control": "private, no-store" } },
    );
  } catch (error) {
    console.error("Feed query failed", error);
    return NextResponse.json({ stories: [], configured: true, error: "feed_unavailable" }, { status: 503 });
  }
}
