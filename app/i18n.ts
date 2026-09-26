export type Language = "zh" | "en";

export const ui = {
  zh: {
    sources: "来源",
    topics: "主题",
    institutions: "机构",
    authors: "作者",
    exploration: "探索",
    warning: "注意",
    readStory: "阅读全文",
    professional: "专业解释",
    originalSource: "Original Source",
    save: "收藏",
    saved: "已收藏",
    expand: "展开专业解释 ↓",
    collapse: "收起专业解释 ↑",
    keyTerms: "关键术语",
    coreAuthors: "核心作者",
    storyCluster: "Story Cluster",
    sourcesCount: "个来源",
    helpful: "这条解释对你有帮助吗？",
    close: "关闭",
    terminology: "专业术语",
    chinese: "中文",
    english: "English",
    understood: "知道了",
    noPhoto: "可靠照片暂缺，显示姓名首字母",
    personSaved: "已收藏人物",
    savePerson: "收藏人物",
    institutionSaved: "已收藏机构",
    saveInstitution: "收藏机构",
    who: "他 / 她是谁",
    career: "教育和职业经历",
    focus: "主要研究方向",
    papers: "代表论文 · 3",
    recentStories: "最近相关 Story",
    whatInstitution: "是什么机构",
    direction: "AI × Bio 主要方向",
    whyKnow: "为什么值得认识",
    researchers: "核心研究者",
    noSaved: "还没有收藏",
    noSavedHint: "在 Feed 里点星标，内容就会出现在这里。",
    explanationDepth: "解释深度",
    depthDescription: "控制默认中文解释的技术深度。",
    exampleAmount: "例子数量",
    exampleDescription: "决定解释中使用多少具体例子。",
    topicDescription: "影响 For You 的排序，不会从 Latest 删除内容。",
    sourceDescription: "第一版优先使用论文与权威索引。",
    geography: "地区",
    geographyDescription: "当前只收录美国和欧洲。",
    geographyLocked: "已锁定 · 后续可通过配置修改",
    locked: "已锁定",
    depthSaved: "解释深度已保存",
    examplesSaved: "例子偏好已保存",
    removed: "已从收藏移除",
    added: "已收藏",
    localFeedback: "本地已记录；云端偏好暂时未更新",
  },
  en: {
    sources: "Sources",
    topics: "Topics",
    institutions: "Institutions",
    authors: "Authors",
    exploration: "Explore",
    warning: "Caution",
    readStory: "Read full story",
    professional: "Professional explanation",
    originalSource: "Original Source",
    save: "Save",
    saved: "Saved",
    expand: "Expand professional explanation ↓",
    collapse: "Collapse professional explanation ↑",
    keyTerms: "Key terms",
    coreAuthors: "Core authors",
    storyCluster: "Story cluster",
    sourcesCount: "sources",
    helpful: "Was this explanation useful?",
    close: "close",
    terminology: "Terminology",
    chinese: "Chinese",
    english: "English",
    understood: "Got it",
    noPhoto: "Verified photo unavailable; showing initials",
    personSaved: "Person saved",
    savePerson: "Save person",
    institutionSaved: "Institution saved",
    saveInstitution: "Save institution",
    who: "Who they are",
    career: "Education and career",
    focus: "Research focus",
    papers: "Representative papers · 3",
    recentStories: "Recent related stories",
    whatInstitution: "About the institution",
    direction: "AI × Bio focus",
    whyKnow: "Why it matters",
    researchers: "Key researchers",
    noSaved: "Nothing saved yet",
    noSavedHint: "Select a star in the Feed to keep it here.",
    explanationDepth: "Explanation depth",
    depthDescription: "Controls the technical depth of default explanations.",
    exampleAmount: "Example amount",
    exampleDescription: "Controls how many concrete examples explanations use.",
    topicDescription: "Affects For You ranking without removing items from Latest.",
    sourceDescription: "The first version prioritizes papers and authoritative indexes.",
    geography: "Geography",
    geographyDescription: "The feed currently covers the United States and Europe.",
    geographyLocked: "Locked · configurable later",
    locked: "LOCKED",
    depthSaved: "Explanation depth saved",
    examplesSaved: "Example preference saved",
    removed: "Removed from saved: ",
    added: "Saved: ",
    localFeedback: "Saved locally; cloud preferences are temporarily unavailable",
  },
} as const;

export const feedbackLabels = {
  "太复杂": { zh: "太复杂", en: "Too complex" },
  "太简单": { zh: "太简单", en: "Too simple" },
  "多来这种": { zh: "多来这种", en: "More like this" },
  "少来这种": { zh: "少来这种", en: "Less like this" },
  "多举例子": { zh: "多举例子", en: "More examples" },
} as const;

export const feedbackMessages = {
  "太复杂": { zh: "已记住：解释会更浅显，主题偏好不变", en: "Got it: explanations will be simpler; topic preferences stay unchanged" },
  "太简单": { zh: "已记住：解释会更专业，主题偏好不变", en: "Got it: explanations will be more technical; topic preferences stay unchanged" },
  "多来这种": { zh: "已提高相关主题、作者和机构偏好", en: "Raised affinity for related topics, authors, and institutions" },
  "少来这种": { zh: "已降低相关主题、作者和机构偏好", en: "Lowered affinity for related topics, authors, and institutions" },
  "多举例子": { zh: "已记住：后续解释会增加例子", en: "Got it: future explanations will use more examples" },
} as const;

export const sectionTitles = {
  zh: ["发生了什么？", "他们想解决什么？", "怎么做的？", "结果怎么样？", "为什么值得我知道？"],
  en: ["What happened?", "What problem are they solving?", "How did they do it?", "What were the results?", "Why should I know about it?"],
} as const;

export const topicTranslations: Record<string, string> = {
  "AI 方法": "AI methods",
  "基础模型": "Foundation models",
  "生成式模型": "Generative models",
  "生成式 AI": "Generative AI",
  "多模态学习": "Multimodal learning",
  "多模态": "Multimodal AI",
  "科学机器学习": "Scientific machine learning",
  "实验自动化": "Lab automation",
  "分子与细胞": "Molecules and cells",
  "蛋白质设计": "Protein design",
  "酶工程": "Enzyme engineering",
  "药物发现": "Drug discovery",
  "基因组学": "Genomics",
  "单细胞": "Single-cell biology",
  "空间组学": "Spatial omics",
  "合成生物学": "Synthetic biology",
  "神经科学": "Neuroscience",
  "计算神经科学": "Computational neuroscience",
  "脑机接口": "Brain–computer interfaces",
  "神经影像": "Neuroimaging",
  "神经退行性疾病": "Neurodegenerative disease",
  "神经精神疾病": "Neuropsychiatric disease",
  "疾病与转化": "Disease and translation",
  "疾病模型": "Disease models",
  "转化 AI": "Translational AI",
  "肿瘤": "Oncology",
  "免疫学": "Immunology",
  "临床 AI": "Clinical AI",
  "生物标志物": "Biomarkers",
  "长寿与衰老": "Longevity and aging",
  "评估标准": "Evaluation standards",
  "开放科学": "Open science",
  "实验验证": "Experimental validation",
};

type StoryEnglish = {
  sections: Array<{ simple: string; professional: string }>;
  limitation?: string;
};

export const storyEnglish: Record<string, StoryEnglish> = {
  "001": {
    sections: [
      { simple: "The team used AI to design new enzymes for a target reaction and selected promising candidates for experiments.", professional: "The team trained a generative model conditioned on protein sequences and three-dimensional backbone geometry. It first proposed sequences likely to fold stably, then filtered them using catalytic-site geometry and substrate-binding constraints." },
      { simple: "Traditional enzyme engineering usually starts from natural proteins, which narrows the search space and requires many experiments.", professional: "Directed evolution needs an existing activity as a starting point. For reactions without a suitable natural template, researchers want to explore a much wider sequence space while preserving plausible catalytic-residue geometry." },
      { simple: "The model generated many sequences, then narrowed them down with structure prediction and energy calculations.", professional: "Candidates were filtered for structural consistency, active-site RMSD, pocket accessibility, and computational energy. Only a small set of high-scoring designs advanced to synthesis and purification." },
      { simple: "Some candidates performed well in computational tests, but the experimental evidence is still limited.", professional: "Several candidates passed computational benchmarks and a smaller subset underwent initial biochemical testing. The results support feasibility, but do not yet show that the method can consistently produce highly active, manufacturable enzymes." },
      { simple: "If broader experiments confirm the method, designing enzymes for new reactions could become much faster.", professional: "This work moves protein generation from making sequences that merely resemble natural proteins toward satisfying explicit functional constraints. It could matter for green chemistry, drug synthesis, and industrial catalysis." },
    ],
    limitation: "Most evidence still comes from computational benchmarks. Only a small number of candidates received wet-lab validation, so broad applicability has not been established.",
  },
  "002": {
    sections: [
      { simple: "Researchers trained a cell model to predict how a cell responds when a gene is perturbed.", professional: "The model was pretrained on multiple scRNA-seq perturbation datasets and generated post-intervention expression profiles conditioned on cell state, perturbation identity, and dose." },
      { simple: "Experiments cannot exhaustively test every combination of gene, cell type, dose, and time point.", professional: "The combination space grows rapidly across genes, cellular backgrounds, time points, and doses. The model aims to transfer learned patterns and reduce the number of experiments that must be prioritized." },
      { simple: "It placed data from different labs in a shared representation space and learned changes before and after intervention.", professional: "Training combined batch correction, masked-expression modeling, and conditional generation, while holding out data from independent laboratories for stricter external evaluation." },
      { simple: "Predictions were stronger for familiar cells and perturbations, but performance dropped in genuinely novel biological settings.", professional: "The model beat baselines on held-out perturbations and cross-dataset tests, but gains were limited for rare cell states, strongly nonlinear responses, and combinatorial perturbations." },
      { simple: "It shows how AI could help decide which experiment is most valuable to run next.", professional: "The main value is not simply generating expression matrices, but using uncertainty and expected information gain to prioritize experiments—potentially serving as a decision layer for automated laboratories." },
    ],
    limitation: "Cross-laboratory generalization remains unstable, and model predictions cannot replace real perturbation experiments.",
  },
  "003": {
    sections: [
      { simple: "A new model jointly learns from tissue images, gene expression, and medical text.", professional: "The system uses modality-specific encoders and a shared latent space to align pathology slides, transcriptomic vectors, and curated textual descriptions." },
      { simple: "Each biological data type reveals only part of a disease, and combining them is often difficult.", professional: "Missing-data patterns differ across cohorts. Directly concatenating features reduces usable sample size and can amplify batch effects." },
      { simple: "The model first processes each data type separately, then maps them into a common space.", professional: "Its objectives combine cross-modal contrastive learning, missing-modality reconstruction, and disease-label supervision to improve transfer with incomplete samples." },
      { simple: "It improved results on several public datasets, but has not shown that it improves real clinical decisions.", professional: "The model outperformed unimodal baselines for survival stratification and subtype classification, but gains varied between cohorts and all analyses were retrospective." },
      { simple: "It helps show whether multimodal foundation models are getting closer to practical use.", professional: "The key signals are external validation, robustness to missing modalities, and prospective utility—not just the average score on one benchmark." },
    ],
    limitation: "All results are retrospective. There is no prospective clinical validation, and fairness across populations was not fully evaluated.",
  },
  "004": {
    sections: [
      { simple: "A group of researchers proposed a reporting checklist for evaluating AI models in biology.", professional: "The article separates evaluation into six levels: data provenance, split strategy, independent replication, wet-lab validation, failure cases, and resource cost." },
      { simple: "Many papers report strong scores but make it hard to tell whether the model will work in a new experiment.", professional: "Random splits can leak homologous samples, single-lab data may let models exploit batch signatures, and missing negative results can inflate apparent success rates." },
      { simple: "The authors compared existing benchmarks and proposed a common disclosure template.", professional: "They reviewed dependencies in widely used benchmarks and proposed minimum isolation standards across time, laboratories, and sequence similarity." },
      { simple: "This is a perspective, not a standard that the entire field has already adopted.", professional: "The checklist can expose common weaknesses, but journals, conferences, and data platforms do not yet share an enforcement mechanism." },
      { simple: "Understanding evaluation design helps you distinguish genuine progress from an attractive benchmark result.", professional: "For industry judgment and interviews, asking about leakage, external validation, and prospective evidence is more valuable than merely repeating a model architecture." },
    ],
  },
};

export const personEnglish: Record<string, { bio: string; career: string; paperNotes: string[] }> = {
  "maya-chen": { bio: "She studies how generative AI can design experimentally testable proteins under explicit chemical constraints.", career: "PhD in biological engineering from MIT, former postdoctoral researcher at EMBL, and now an assistant professor of bioengineering at Stanford.", paperNotes: ["Most relevant to this story", "Represents current research direction", "Established the methodological foundation"] },
  "leo-martin": { bio: "He develops machine-learning methods that connect protein sequence, three-dimensional structure, and experimental function measurements.", career: "PhD in computer science from ETH Zürich; now a research scientist at EMBL working with multiple wet labs.", paperNotes: ["Most relevant to this story", "Represents current research direction", "Widely used field benchmark"] },
  "elena-rossi": { bio: "She uses single-cell and perturbation experiments to study how immune cells respond to disease and treatment.", career: "PhD in genetics from the University of Cambridge, former Broad Institute postdoctoral researcher, and now leads a computational genomics group at Sanger.", paperNotes: ["Representative resource", "Most relevant to this story", "Established the research direction"] },
  "noah-williams": { bio: "He leads the use of multimodal foundation models for target discovery and early drug-program decisions.", career: "PhD in machine learning from Carnegie Mellon University, formerly in computational drug discovery at a pharmaceutical company, and now VP of machine learning at Aster Therapeutics.", paperNotes: ["Current team focus", "Represents current research direction", "Emphasizes prospective validation"] },
};

export const institutionEnglish: Record<string, { description: string; direction: string; why: string }> = {
  stanford: { description: "A leading US research university with close links between computer science, bioengineering, medicine, and entrepreneurship.", direction: "Protein design, foundation models, genomics, medical AI, and translational research.", why: "Many AI × Bio methods move from algorithm development to clinical collaboration and company formation here, making it worth following closely." },
  embl: { description: "A major European life-science organization with sites across member countries and a strong emphasis on open resources and interdisciplinary research.", direction: "Structural biology, computational biology, imaging, genomics, and bioinformatics infrastructure.", why: "EMBL connects the European research network and produces widely reused data, tools, and methods." },
  sanger: { description: "A nonprofit research institute known for large-scale genomics, data resources, and studies of human disease.", direction: "Single-cell atlases, cancer genomics, pathogen surveillance, and computational genomics.", why: "Its datasets often become important foundations for training and independently evaluating AI × Bio models." },
  aster: { description: "A fictional biotechnology company used in the Phase 1 prototype to represent teams applying multimodal AI to early drug discovery.", direction: "Target discovery, multimodal biological data, virtual screening, and translational validation.", why: "It demonstrates a company profile and how research findings may enter real R&D decisions." },
};

export function topicLabel(value: string, language: Language) {
  return language === "en" ? topicTranslations[value] || value : value;
}

export function ageLabel(value: string, language: Language) {
  if (language === "zh") return value;
  if (value === "刚刚") return "just now";
  if (value === "昨天") return "yesterday";
  const hours = value.match(/^(\d+)\s*小时前$/);
  if (hours) return `${hours[1]}h ago`;
  const days = value.match(/^(\d+)\s*天前$/);
  if (days) return `${days[1]}d ago`;
  return value;
}
