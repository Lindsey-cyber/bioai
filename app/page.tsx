"use client";

import { useEffect, useMemo, useState } from "react";

type View = "feed" | "saved" | "settings";
type FeedMode = "for-you" | "latest";
type Feedback = "太复杂" | "太简单" | "多来这种" | "少来这种" | "多举例子";

type Term = {
  zh: string;
  en: string;
  abbr?: string;
  zhExplanation: string;
  enExplanation: string;
};

type Person = {
  id: string;
  initials: string;
  name: string;
  role: string;
  institution: string;
  focus: string[];
  bio: string;
  career: string;
  papers: { title: string; year: number; note: string }[];
};

type Institution = {
  id: string;
  name: string;
  short: string;
  location: string;
  kind: string;
  description: string;
  direction: string;
  why: string;
  researchers: string[];
};

type Section = {
  title: string;
  simple: string;
  professional: string;
  terms?: Term[];
};

type Story = {
  id: string;
  source: string;
  sourceType: string;
  age: string;
  date: string;
  title: string;
  titleZh: string;
  topics: string[];
  importance: number;
  relevance: number;
  sections: Section[];
  limitation?: string;
  authors: string[];
  institutions: string[];
  sources: string[];
  exploration?: boolean;
};

const TERMS: Record<string, Term> = {
  plm: {
    zh: "蛋白质语言模型",
    en: "Protein Language Model",
    abbr: "PLM",
    zhExplanation: "一种从大量蛋白质序列中学习氨基酸排列规律的 AI 模型。它能帮助预测蛋白质的结构、功能和可能的改造方向。",
    enExplanation: "An AI model trained on protein sequences to learn statistical and biological patterns that support structure, function, and design tasks.",
  },
  diffusion: {
    zh: "扩散模型",
    en: "Diffusion Model",
    zhExplanation: "一种从随机噪声出发，通过多步修正逐渐生成目标结构的生成式模型。",
    enExplanation: "A generative model that iteratively denoises a random sample into a structured output such as a molecule or protein backbone.",
  },
  singleCell: {
    zh: "单细胞转录组",
    en: "Single-cell transcriptomics",
    abbr: "scRNA-seq",
    zhExplanation: "在单个细胞层面测量基因表达，帮助研究者看见组织中不同细胞的状态和差异。",
    enExplanation: "Measurement of gene expression at single-cell resolution, revealing cell types, states, and responses hidden in bulk samples.",
  },
  multimodal: {
    zh: "多模态学习",
    en: "Multimodal learning",
    zhExplanation: "让模型同时理解多种类型的数据，例如基因表达、染色质开放性和显微图像。",
    enExplanation: "Machine learning that jointly represents and reasons over multiple data modalities.",
  },
  causal: {
    zh: "因果扰动",
    en: "Causal perturbation",
    zhExplanation: "通过主动改变基因或细胞条件，观察结果变化，从而判断因果关系，而不只是相关性。",
    enExplanation: "An intervention that changes a biological variable so researchers can estimate causal rather than correlational effects.",
  },
};

const PEOPLE: Person[] = [
  {
    id: "maya-chen",
    initials: "MC",
    name: "Dr. Maya Chen",
    role: "Assistant Professor",
    institution: "Stanford University",
    focus: ["Protein Design", "Enzyme Engineering"],
    bio: "她研究如何让生成式 AI 在明确的化学约束下设计可实验验证的蛋白质。",
    career: "MIT 生物工程博士，曾在欧洲分子生物学实验室从事博士后研究，现任 Stanford 生物工程系助理教授。",
    papers: [
      { title: "Constraint-aware generation of catalytic protein scaffolds", year: 2026, note: "与当前新闻最相关" },
      { title: "Learning functional priors from protein families", year: 2024, note: "代表当前研究方向" },
      { title: "Data-efficient enzyme landscape modeling", year: 2022, note: "奠定方法基础" },
    ],
  },
  {
    id: "leo-martin",
    initials: "LM",
    name: "Dr. Leo Martin",
    role: "Research Scientist",
    institution: "European Molecular Biology Laboratory",
    focus: ["Machine Learning", "Structural Biology"],
    bio: "他开发连接蛋白质序列、三维结构和实验功能读数的机器学习方法。",
    career: "ETH Zürich 计算机科学博士，现任 EMBL 研究科学家，并与多个湿实验室合作。",
    papers: [
      { title: "Joint sequence–structure representations for enzyme design", year: 2026, note: "与当前新闻最相关" },
      { title: "Geometric priors for protein function", year: 2024, note: "代表当前研究方向" },
      { title: "Benchmarking learned protein representations", year: 2021, note: "领域常用基准" },
    ],
  },
  {
    id: "elena-rossi",
    initials: "ER",
    name: "Dr. Elena Rossi",
    role: "Principal Investigator",
    institution: "Wellcome Sanger Institute",
    focus: ["Single-cell Genomics", "Foundation Models"],
    bio: "她用单细胞和扰动实验研究免疫细胞如何响应疾病与治疗。",
    career: "University of Cambridge 遗传学博士，曾任 Broad Institute 博士后，现领导 Sanger 的计算基因组学团队。",
    papers: [
      { title: "A perturbation atlas of human immune cells", year: 2025, note: "代表性资源" },
      { title: "Foundation models for cross-tissue cell states", year: 2026, note: "与当前新闻最相关" },
      { title: "Generalizing cell-state predictors across cohorts", year: 2023, note: "奠定研究方向" },
    ],
  },
  {
    id: "noah-williams",
    initials: "NW",
    name: "Noah Williams",
    role: "VP, Machine Learning",
    institution: "Aster Therapeutics",
    focus: ["Drug Discovery", "Translational AI"],
    bio: "他负责把多模态基础模型用于靶点发现和早期药物项目决策。",
    career: "Carnegie Mellon University 机器学习博士，曾在制药企业负责计算药物发现，现任 Aster Therapeutics 机器学习副总裁。",
    papers: [
      { title: "A multimodal foundation model for early drug discovery", year: 2026, note: "当前团队核心工作" },
      { title: "Learning from negative assay outcomes", year: 2024, note: "代表当前研究方向" },
      { title: "Prospective evaluation of virtual screening", year: 2022, note: "强调真实验证" },
    ],
  },
];

const INSTITUTIONS: Institution[] = [
  {
    id: "stanford",
    name: "Stanford University",
    short: "SU",
    location: "California, United States",
    kind: "Research university",
    description: "美国领先研究型大学，在计算机科学、生物工程、医学与创业生态之间有紧密连接。",
    direction: "蛋白质设计、基础模型、基因组学、医学 AI 与转化研究。",
    why: "很多 AI × Bio 方法会同时在这里完成算法开发、临床合作和公司转化，值得持续关注。",
    researchers: ["maya-chen"],
  },
  {
    id: "embl",
    name: "European Molecular Biology Laboratory",
    short: "EMBL",
    location: "Heidelberg, Germany · European network",
    kind: "Intergovernmental research organisation",
    description: "欧洲重要的生命科学研究机构，在多个成员国设有站点，强调开放资源和跨学科研究。",
    direction: "结构生物学、计算生物学、成像、基因组学和生物信息学基础设施。",
    why: "EMBL 连接欧洲研究网络，并产出大量可复用的数据、工具和方法。",
    researchers: ["leo-martin"],
  },
  {
    id: "sanger",
    name: "Wellcome Sanger Institute",
    short: "WSI",
    location: "Cambridge, United Kingdom",
    kind: "Genomics research institute",
    description: "以大规模基因组学、数据资源和人类疾病研究著称的非营利研究机构。",
    direction: "单细胞图谱、癌症基因组学、病原体监测与计算基因组学。",
    why: "这里的数据集常成为 AI × Bio 模型训练和独立评估的重要基础。",
    researchers: ["elena-rossi"],
  },
  {
    id: "aster",
    name: "Aster Therapeutics",
    short: "AT",
    location: "Boston, United States",
    kind: "Biotechnology company · mock",
    description: "Phase 1 使用的虚构生物科技公司，代表将多模态 AI 用于早期药物发现的团队。",
    direction: "靶点发现、多模态生物数据、虚拟筛选和转化验证。",
    why: "用于展示公司型机构 profile，以及研究成果如何进入真实研发决策。",
    researchers: ["noah-williams"],
  },
];

const sectionTitles = ["发生了什么？", "他们想解决什么？", "怎么做的？", "结果怎么样？", "为什么值得我知道？"];

const STORIES: Story[] = [
  {
    id: "001",
    source: "bioRxiv",
    sourceType: "preprint",
    age: "3 小时前",
    date: "2026-09-13",
    title: "A generative model designs functional enzymes for novel reactions",
    titleZh: "生成式模型为从未见过的化学反应设计出候选功能酶",
    topics: ["蛋白质设计", "生成式 AI", "酶工程"],
    importance: 0.89,
    relevance: 0.93,
    authors: ["maya-chen", "leo-martin"],
    institutions: ["stanford", "embl"],
    sources: ["Original paper", "arXiv", "GitHub", "Lab blog"],
    sections: [
      {
        title: sectionTitles[0],
        simple: "研究团队让 AI 按照目标反应来设计新的酶，并挑选出一批值得实验的候选。",
        professional: "团队训练了一个结合蛋白质序列与三维骨架条件的生成模型。模型先提出可能折叠稳定的序列，再依据催化位点几何和底物结合约束筛选。",
        terms: [TERMS.plm, TERMS.diffusion],
      },
      {
        title: sectionTitles[1],
        simple: "传统酶改造通常从天然蛋白出发，搜索范围窄、实验次数多。",
        professional: "定向进化依赖已有活性起点。对于自然界中缺少对应模板的反应，研究者希望直接探索更广的序列空间，同时保留催化残基的合理几何。",
      },
      {
        title: sectionTitles[2],
        simple: "模型先生成大量序列，再用结构预测和能量计算层层筛选。",
        professional: "候选序列经过结构一致性、活性位点 RMSD、口袋可达性与计算能量过滤。最终少量高分候选进入合成与纯化流程。",
      },
      {
        title: sectionTitles[3],
        simple: "部分候选在计算测试中表现很好，但真正的实验结果仍然有限。",
        professional: "论文报告多个候选通过计算 benchmark，其中少数完成初步生化测定。现有结果支持方法可行性，但还不能证明它能稳定生成高活性、可规模化生产的酶。",
      },
      {
        title: sectionTitles[4],
        simple: "如果方法经得起更多实验验证，新反应的酶设计可能更快。",
        professional: "这项工作代表蛋白质生成从“像天然蛋白”走向“满足指定功能约束”。对绿色化学、药物合成和工业催化都有潜在意义。",
      },
    ],
    limitation: "目前主要结果仍来自 computational benchmark，wet-lab validation 的候选数量较少，尚未证明广泛适用。",
  },
  {
    id: "002",
    source: "Nature Biotechnology",
    sourceType: "research article",
    age: "6 小时前",
    date: "2026-09-13",
    title: "A single-cell foundation model predicts unseen perturbation responses",
    titleZh: "单细胞基础模型尝试预测从未做过的基因扰动结果",
    topics: ["单细胞", "基础模型", "基因组学"],
    importance: 0.94,
    relevance: 0.76,
    authors: ["elena-rossi"],
    institutions: ["sanger"],
    sources: ["Original paper", "PubMed", "OpenAlex", "Code"],
    sections: [
      {
        title: sectionTitles[0],
        simple: "研究者训练了一个细胞模型，用来预测某个基因被改变后细胞会如何反应。",
        professional: "模型在多个 scRNA-seq 扰动数据集上进行预训练，以细胞状态、扰动身份和剂量为条件生成干预后的表达谱。",
        terms: [TERMS.singleCell, TERMS.causal],
      },
      {
        title: sectionTitles[1],
        simple: "实验不可能穷举每个基因、细胞类型和剂量组合。",
        professional: "组合空间会随基因、细胞背景、时间点与剂量快速增长。模型试图通过迁移已见模式，减少需要优先开展的实验数量。",
      },
      {
        title: sectionTitles[2],
        simple: "它把不同实验室的数据放进同一个表示空间，再学习干预前后的变化。",
        professional: "研究使用批次校正、掩码表达建模和条件生成目标，并保留独立实验室数据作为严格外部测试集。",
      },
      {
        title: sectionTitles[3],
        simple: "对相似细胞和常见扰动预测较准，遇到真正陌生的生物条件时仍会变差。",
        professional: "在 held-out perturbation 与跨数据集评估中优于基线，但对稀有细胞状态、强非线性反应和组合扰动的提升有限。",
      },
      {
        title: sectionTitles[4],
        simple: "它展示了 AI 可以帮助决定“下一个最值得做的实验”。",
        professional: "价值不只是生成表达矩阵，而是用不确定性和预期信息增益辅助实验排序；这可能成为自动化实验平台的决策层。",
      },
    ],
    limitation: "跨实验室泛化仍不稳定，模型预测不能替代真实扰动实验。",
  },
  {
    id: "003",
    source: "arXiv",
    sourceType: "paper",
    age: "9 小时前",
    date: "2026-09-13",
    title: "Multimodal biological models learn transferable disease representations",
    titleZh: "多模态生物模型把影像、组学和文本连接到统一的疾病表示",
    topics: ["多模态", "疾病模型", "转化 AI"],
    importance: 0.82,
    relevance: 0.67,
    authors: ["noah-williams"],
    institutions: ["aster"],
    sources: ["Original paper", "arXiv", "Hugging Face"],
    sections: [
      {
        title: sectionTitles[0],
        simple: "一个新模型同时学习组织图像、基因表达和医学文本。",
        professional: "该模型使用 modality-specific encoders 与共享潜在空间，对病理切片、转录组向量和经过筛选的文本描述进行对齐训练。",
        terms: [TERMS.multimodal],
      },
      {
        title: sectionTitles[1],
        simple: "不同生物数据各自只看到疾病的一部分，而且常常难以组合。",
        professional: "队列间的数据缺失模式不同，直接拼接特征会限制可用样本并放大批次差异。",
      },
      {
        title: sectionTitles[2],
        simple: "模型先分别理解每种数据，再把它们映射到共同空间。",
        professional: "训练目标结合跨模态对比学习、缺失模态重建与疾病标签监督，以提高不完整样本上的迁移能力。",
      },
      {
        title: sectionTitles[3],
        simple: "几个公开数据集上有提升，但还没有证明能改善真实临床决策。",
        professional: "在生存分层和亚型分类上超过单模态基线，不过增益在不同队列间波动，且均为回顾性分析。",
      },
      {
        title: sectionTitles[4],
        simple: "它能帮你判断“多模态基础模型”是否正在接近真实应用。",
        professional: "关键观察点是外部验证、缺失模态鲁棒性和 prospective utility，而不是只看单个 benchmark 的平均分。",
      },
    ],
    limitation: "全部结果来自回顾性队列；没有前瞻性临床验证，也未报告不同人群中的完整公平性评估。",
  },
  {
    id: "004",
    source: "Cell Systems",
    sourceType: "perspective",
    age: "昨天",
    date: "2026-09-12",
    title: "What reproducible evaluation should mean for AI-enabled biology",
    titleZh: "AI × Bio 需要什么样的可复现实验评估标准？",
    topics: ["评估标准", "开放科学", "实验验证"],
    importance: 0.79,
    relevance: 0.31,
    authors: ["leo-martin", "elena-rossi"],
    institutions: ["embl", "sanger"],
    sources: ["Original article", "PubMed", "Community discussion"],
    exploration: true,
    sections: [
      {
        title: sectionTitles[0],
        simple: "一组研究者提出了一套评估 AI 生物学模型的报告清单。",
        professional: "文章将评估拆分为数据谱系、拆分策略、独立复现、湿实验验证、失败案例和资源成本六个层级。",
      },
      {
        title: sectionTitles[1],
        simple: "很多论文分数很好，却很难判断是否真的能用于新实验。",
        professional: "随机拆分可能产生同源泄漏，单实验室数据会让模型利用批次特征，缺少阴性结果则会高估实际成功率。",
      },
      {
        title: sectionTitles[2],
        simple: "他们比较了现有 benchmark，并给出统一的披露模板。",
        professional: "作者复核多个常用 benchmark 的数据依赖关系，并提出按时间、实验室与序列相似性进行隔离的最低标准。",
      },
      {
        title: sectionTitles[3],
        simple: "这是评议文章，不是一个已被全行业采用的新标准。",
        professional: "清单能暴露常见问题，但尚缺少期刊、会议和数据平台的共同执行机制。",
      },
      {
        title: sectionTitles[4],
        simple: "懂得看评估方法，能帮助你分辨真正进展和漂亮的 benchmark。",
        professional: "对求职和行业判断而言，能追问数据泄漏、外部验证和 prospective evidence，比只复述模型架构更有价值。",
      },
    ],
  },
];

const feedbackOptions: Feedback[] = ["太复杂", "太简单", "多来这种", "少来这种", "多举例子"];

function readLocal<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export default function Home() {
  const [view, setView] = useState<View>("feed");
  const [mode, setMode] = useState<FeedMode>("for-you");
  const [selectedStory, setSelectedStory] = useState<Story | null>(STORIES[0]);
  const [storyMobileOpen, setStoryMobileOpen] = useState(false);
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [selectedInstitution, setSelectedInstitution] = useState<Institution | null>(null);
  const [selectedTerm, setSelectedTerm] = useState<Term | null>(null);
  const [savedStories, setSavedStories] = useState<string[]>([]);
  const [savedPeople, setSavedPeople] = useState<string[]>([]);
  const [savedInstitutions, setSavedInstitutions] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<Record<string, Feedback[]>>({});
  const [toast, setToast] = useState("");
  const [savedTab, setSavedTab] = useState<"stories" | "people" | "institutions">("stories");
  const [depth, setDepth] = useState("balanced");
  const [examples, setExamples] = useState("some");
  const [topics, setTopics] = useState(["蛋白质设计", "药物发现", "单细胞"]);
  const [sources, setSources] = useState(["arXiv", "bioRxiv", "PubMed"]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setSavedStories(readLocal("bioai:saved-stories", []));
      setSavedPeople(readLocal("bioai:saved-people", []));
      setSavedInstitutions(readLocal("bioai:saved-institutions", []));
      setFeedback(readLocal("bioai:feedback", {}));
      setDepth(readLocal("bioai:depth", "balanced"));
      setExamples(readLocal("bioai:examples", "some"));
      setTopics(readLocal("bioai:topics", ["蛋白质设计", "药物发现", "单细胞"]));
      setSources(readLocal("bioai:sources", ["arXiv", "bioRxiv", "PubMed"]));
      setHydrated(true);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => { if (hydrated) localStorage.setItem("bioai:saved-stories", JSON.stringify(savedStories)); }, [savedStories, hydrated]);
  useEffect(() => { if (hydrated) localStorage.setItem("bioai:saved-people", JSON.stringify(savedPeople)); }, [savedPeople, hydrated]);
  useEffect(() => { if (hydrated) localStorage.setItem("bioai:saved-institutions", JSON.stringify(savedInstitutions)); }, [savedInstitutions, hydrated]);
  useEffect(() => { if (hydrated) localStorage.setItem("bioai:feedback", JSON.stringify(feedback)); }, [feedback, hydrated]);
  useEffect(() => { if (hydrated) localStorage.setItem("bioai:depth", JSON.stringify(depth)); }, [depth, hydrated]);
  useEffect(() => { if (hydrated) localStorage.setItem("bioai:examples", JSON.stringify(examples)); }, [examples, hydrated]);
  useEffect(() => { if (hydrated) localStorage.setItem("bioai:topics", JSON.stringify(topics)); }, [topics, hydrated]);
  useEffect(() => { if (hydrated) localStorage.setItem("bioai:sources", JSON.stringify(sources)); }, [sources, hydrated]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 1900);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (selectedTerm) setSelectedTerm(null);
      else if (selectedPerson) setSelectedPerson(null);
      else if (selectedInstitution) setSelectedInstitution(null);
      else {
        setSelectedStory(null);
        setStoryMobileOpen(false);
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [selectedTerm, selectedPerson, selectedInstitution]);

  const feedStories = useMemo(() => {
    return [...STORIES].sort((a, b) => mode === "latest" ? b.date.localeCompare(a.date) || b.id.localeCompare(a.id) : ((b.importance * .55 + b.relevance * .30) - (a.importance * .55 + a.relevance * .30)));
  }, [mode]);

  const showToast = (message: string) => setToast(message);
  const toggleArray = (value: string, current: string[], setter: (next: string[]) => void, label: string) => {
    const next = current.includes(value) ? current.filter((id) => id !== value) : [...current, value];
    setter(next);
    showToast(current.includes(value) ? `已从收藏移除${label}` : `已收藏${label}`);
  };

  const applyFeedback = (storyId: string, option: Feedback) => {
    setFeedback((current) => {
      const chosen = current[storyId] || [];
      const next = chosen.includes(option) ? chosen.filter((item) => item !== option) : [...chosen.filter((item) => {
        if (["太复杂", "太简单"].includes(option)) return !["太复杂", "太简单"].includes(item);
        if (["多来这种", "少来这种"].includes(option)) return !["多来这种", "少来这种"].includes(item);
        return true;
      }), option];
      return { ...current, [storyId]: next };
    });
    const message: Record<Feedback, string> = {
      太复杂: "已记住：解释会更浅显，主题偏好不变",
      太简单: "已记住：解释会更专业，主题偏好不变",
      多来这种: "已提高相关主题、作者和机构偏好",
      少来这种: "已降低相关主题、作者和机构偏好",
      多举例子: "已记住：后续解释会增加例子",
    };
    showToast(message[option]);
  };

  const navigate = (next: View) => {
    setView(next);
    setSelectedStory(next === "feed" ? STORIES[0] : null);
    setStoryMobileOpen(false);
    setSelectedPerson(null);
    setSelectedInstitution(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const openStory = (story: Story) => {
    setSelectedStory(story);
    setStoryMobileOpen(true);
  };

  return (
    <div className={`app-shell ${selectedStory && view === "feed" ? "has-detail" : ""}`}>
      <aside className="desktop-sidebar" aria-label="主导航">
        <Brand />
        <nav className="side-nav">
          <NavButton active={view === "feed"} label="Feed" count="04" onClick={() => navigate("feed")} />
          <NavButton active={view === "saved"} label="Saved" count={String(savedStories.length + savedPeople.length + savedInstitutions.length).padStart(2, "0")} onClick={() => navigate("saved")} />
          <NavButton active={view === "settings"} label="Settings" onClick={() => navigate("settings")} />
        </nav>
        <div className="side-context">
          <p className="eyebrow">// FILTERS</p>
          <div className="lens-line"><span className="status-dot" /> for_you</div>
          <p>└ latest</p>
        </div>
        <div className="side-context source-list">
          <p className="eyebrow">// SOURCES</p>
          <span>› arXiv <b>[12]</b></span>
          <span>› bioRxiv <b>[08]</b></span>
          <span>› PubMed <b>[05]</b></span>
          <span>› Nature <b>[04]</b></span>
          <span>› Company / Lab <b>[06]</b></span>
        </div>
        <div className="side-context topics-list">
          <p className="eyebrow">// TOPICS (TOP)</p>
          <span>蛋白质设计 <b>0.93</b></span>
          <span>药物发现 <b>0.76</b></span>
          <span>单细胞 <b>0.64</b></span>
          <span>基础模型 <b>0.58</b></span>
        </div>
        <p className="side-footer">v0.1.0<br />/ home / ai-bio<br /><span>_</span></p>
      </aside>

      <main className="main-column">
        <header className="topbar">
          <div className="mobile-brand"><Brand compact /></div>
          <div className="terminal-path">
            <span>▱</span>
            <b>{view}</b>
            {view === "feed" && <><i>/</i><em>{mode === "for-you" ? "for_you" : "latest"}</em></>}
          </div>
          {view === "feed" && (
            <div className="segmented" aria-label="Feed mode">
              <button className={mode === "for-you" ? "active" : ""} onClick={() => setMode("for-you")}>For You</button>
              <button className={mode === "latest" ? "active" : ""} onClick={() => setMode("latest")}>Latest</button>
            </div>
          )}
          {view !== "feed" && <h1>{view === "saved" ? "Saved" : "Settings"}</h1>}
          <span className="region-pill">[ US + EUROPE ]</span>
        </header>

        {view === "feed" && (
          <div className="feed-wrap">
            <div className="feed-intro">
              <div>
                <p className="eyebrow">{mode === "for-you" ? "PERSONALIZED FEED" : "QUALIFIED TIME STREAM"}</p>
                <h1>{mode === "for-you" ? "今天值得知道的 AI × Bio" : "最新合格信息"}</h1>
              </div>
              <p>{mode === "for-you" ? "重要性优先，保留少量探索内容。" : "只按时间排列，不受个人偏好影响。"}</p>
            </div>
            <div className="story-list">
              {feedStories.map((story, index) => (
                <StoryCard
                  key={story.id}
                  story={story}
                  index={index + 1}
                  isSaved={savedStories.includes(story.id)}
                  selectedFeedback={feedback[story.id] || []}
                  onOpen={() => openStory(story)}
                  onSave={() => toggleArray(story.id, savedStories, setSavedStories, " Story")}
                  onFeedback={(option) => applyFeedback(story.id, option)}
                  onTerm={setSelectedTerm}
                  onPerson={(id) => setSelectedPerson(PEOPLE.find((person) => person.id === id) || null)}
                  onInstitution={(id) => setSelectedInstitution(INSTITUTIONS.find((institution) => institution.id === id) || null)}
                />
              ))}
            </div>
          </div>
        )}

        {view === "saved" && (
          <SavedView
            tab={savedTab}
            setTab={setSavedTab}
            storyIds={savedStories}
            peopleIds={savedPeople}
            institutionIds={savedInstitutions}
            onStory={openStory}
            onPerson={setSelectedPerson}
            onInstitution={setSelectedInstitution}
          />
        )}

        {view === "settings" && (
          <SettingsView depth={depth} setDepth={setDepth} examples={examples} setExamples={setExamples} topics={topics} setTopics={setTopics} sources={sources} setSources={setSources} showToast={showToast} />
        )}
      </main>

      <nav className="mobile-nav" aria-label="底部导航">
        <NavButton active={view === "feed"} label="Feed" onClick={() => navigate("feed")} />
        <NavButton active={view === "saved"} label="Saved" count={String(savedStories.length + savedPeople.length + savedInstitutions.length)} onClick={() => navigate("saved")} />
        <NavButton active={view === "settings"} label="Settings" onClick={() => navigate("settings")} />
      </nav>

      {selectedStory && (
        <Drawer
          title={`/ story/${selectedStory.id}`}
          pinned={view === "feed"}
          mobileOpen={storyMobileOpen}
          onClose={() => { setSelectedStory(null); setStoryMobileOpen(false); }}
        >
          <StoryDetail
            story={selectedStory}
            isSaved={savedStories.includes(selectedStory.id)}
            selectedFeedback={feedback[selectedStory.id] || []}
            onSave={() => toggleArray(selectedStory.id, savedStories, setSavedStories, " Story")}
            onFeedback={(option) => applyFeedback(selectedStory.id, option)}
            onTerm={setSelectedTerm}
            onPerson={(id) => setSelectedPerson(PEOPLE.find((person) => person.id === id) || null)}
            onInstitution={(id) => setSelectedInstitution(INSTITUTIONS.find((institution) => institution.id === id) || null)}
          />
        </Drawer>
      )}

      {selectedPerson && (
        <Drawer title="PEOPLE" onClose={() => setSelectedPerson(null)} nested={Boolean(selectedStory)}>
          <PersonProfile
            person={selectedPerson}
            isSaved={savedPeople.includes(selectedPerson.id)}
            onSave={() => toggleArray(selectedPerson.id, savedPeople, setSavedPeople, " People")}
            onInstitution={() => setSelectedInstitution(INSTITUTIONS.find((item) => item.name === selectedPerson.institution) || null)}
            onStory={(story) => { setSelectedPerson(null); openStory(story); }}
          />
        </Drawer>
      )}

      {selectedInstitution && (
        <Drawer title="INSTITUTION" onClose={() => setSelectedInstitution(null)} nested={Boolean(selectedStory)}>
          <InstitutionProfile
            institution={selectedInstitution}
            isSaved={savedInstitutions.includes(selectedInstitution.id)}
            onSave={() => toggleArray(selectedInstitution.id, savedInstitutions, setSavedInstitutions, " Institution")}
            onPerson={(person) => { setSelectedInstitution(null); setSelectedPerson(person); }}
            onStory={(story) => { setSelectedInstitution(null); openStory(story); }}
          />
        </Drawer>
      )}

      {selectedTerm && <TermModal term={selectedTerm} onClose={() => setSelectedTerm(null)} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? "compact" : ""}`}>
      <div className="brand-mark">AI <span>×</span> BIO<i /></div>
      {!compact && <p>read slowly. connect the dots.</p>}
    </div>
  );
}

function NavButton({ active, label, count, onClick }: { active: boolean; label: string; count?: string; onClick: () => void }) {
  return (
    <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>
      <span>{label}</span>{count && <small>{count}</small>}
    </button>
  );
}

function StoryCard({ story, index, isSaved, selectedFeedback, onOpen, onSave, onFeedback, onTerm, onPerson, onInstitution }: {
  story: Story; index: number; isSaved: boolean; selectedFeedback: Feedback[]; onOpen: () => void; onSave: () => void; onFeedback: (f: Feedback) => void; onTerm: (term: Term) => void; onPerson: (id: string) => void; onInstitution: (id: string) => void;
}) {
  const [openSections, setOpenSections] = useState<number[]>([]);
  const toggleSection = (index: number) => setOpenSections((current) => current.includes(index) ? current.filter((item) => item !== index) : [...current, index]);
  return (
    <article className="story-card">
      <div className="story-meta-row">
        <div className="story-kicker">
          <span className="story-index">[{String(index).padStart(2, "0")}]</span>
          <span className="source-name">{story.source}</span>
          <span>{story.age}</span>
          <span>{story.sourceType}</span>
          {story.exploration && <span className="explore-badge">探索</span>}
        </div>
        <button className={`icon-button ${isSaved ? "saved" : ""}`} onClick={onSave} aria-label={isSaved ? "取消收藏" : "收藏"}>{isSaved ? "★" : "☆"}</button>
      </div>
      <button className="story-title-button" onClick={onOpen}>
        <h2>{story.title}</h2>
        <p>{story.titleZh}</p>
      </button>

      <div className="five-sections">
        {story.sections.map((section, sectionIndex) => {
          const open = openSections.includes(sectionIndex);
          return (
            <div className={`story-section ${open ? "open" : ""}`} key={section.title}>
              <button className="section-summary" onClick={() => toggleSection(sectionIndex)} aria-expanded={open}>
                <span className="section-number">{sectionIndex + 1}</span>
                <span><b>{section.title}</b><em>{section.simple}</em></span>
                <span className="chevron">{open ? "−" : "+"}</span>
              </button>
              {open && (
                <div className="professional-inline">
                  <span>PROFESSIONAL</span>
                  <p>{section.professional}</p>
                  {section.terms?.map((term) => <button className="term-link" key={term.en} onClick={() => onTerm(term)}>{term.en}{term.abbr ? ` (${term.abbr})` : ""}</button>)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {story.limitation && <div className="warning-compact"><b>⚠ 注意</b><span>{story.limitation}</span></div>}

      <div className="entity-row">
        <span className="entity-label">机构</span>
        <div>{story.institutions.map((id) => {
          const institution = INSTITUTIONS.find((item) => item.id === id)!;
          return <button className="chip" key={id} onClick={() => onInstitution(id)}>{institution.name}</button>;
        })}</div>
      </div>
      <div className="entity-row">
        <span className="entity-label">作者</span>
        <div>{story.authors.map((id) => {
          const person = PEOPLE.find((item) => item.id === id)!;
          return <button className="person-chip" key={id} onClick={() => onPerson(id)}><Avatar initials={person.initials} small /><span>{person.name}<small>{person.institution}</small></span></button>;
        })}</div>
      </div>

      <div className="source-row"><span>SOURCES</span>{story.sources.map((source, i) => <button key={source} onClick={() => showExternalDemo(source)}>{i === 0 ? "↗ " : ""}{source}</button>)}</div>
      <FeedbackBar selected={selectedFeedback} onFeedback={onFeedback} />
      <button className="open-story" onClick={onOpen}>阅读全文 <span>→</span></button>
    </article>
  );
}

function FeedbackBar({ selected, onFeedback }: { selected: Feedback[]; onFeedback: (feedback: Feedback) => void }) {
  return (
    <div className="feedback-bar" aria-label="反馈">
      {feedbackOptions.map((option) => <button key={option} className={selected.includes(option) ? "active" : ""} onClick={() => onFeedback(option)}>{option}</button>)}
    </div>
  );
}

function StoryDetail({ story, isSaved, selectedFeedback, onSave, onFeedback, onTerm, onPerson, onInstitution }: {
  story: Story; isSaved: boolean; selectedFeedback: Feedback[]; onSave: () => void; onFeedback: (f: Feedback) => void; onTerm: (term: Term) => void; onPerson: (id: string) => void; onInstitution: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState<number[]>([0]);
  const toggle = (index: number) => setExpanded((items) => items.includes(index) ? items.filter((item) => item !== index) : [...items, index]);
  return (
    <div className="detail-content">
      <div className="detail-heading">
        <p className="story-kicker"><span className="source-name">{story.source}</span><span>{story.date}</span><span>{story.sourceType}</span></p>
        <h2>{story.title}</h2>
        <p className="detail-title-zh">{story.titleZh}</p>
        <div className="topic-row">{story.topics.map((topic) => <span key={topic}>{topic}</span>)}</div>
      </div>
      <div className="original-actions">
        <button onClick={() => showExternalDemo("Original Source")}>↗ Original Source</button>
        <button onClick={onSave}>{isSaved ? "★ Saved" : "☆ Save"}</button>
      </div>
      <div className="detail-sections">
        {story.sections.map((section, index) => {
          const isExpanded = expanded.includes(index);
          return (
            <section key={section.title} className="detail-section">
              <div className="detail-section-title"><span>{String(index + 1).padStart(2, "0")}</span><h3>{section.title}</h3></div>
              <p className="simple-copy">{section.simple}</p>
              <button className="expand-button" onClick={() => toggle(index)}>{isExpanded ? "收起专业解释 ↑" : "展开专业解释 ↓"}</button>
              {isExpanded && (
                <div className="professional-copy">
                  <p>{section.professional}</p>
                  {section.terms && section.terms.length > 0 && (
                    <div className="term-list"><span>关键术语</span>{section.terms.map((term) => <button key={term.en} onClick={() => onTerm(term)}>{term.zh}<small>{term.en}{term.abbr ? ` · ${term.abbr}` : ""}</small></button>)}</div>
                  )}
                </div>
              )}
            </section>
          );
        })}
      </div>
      {story.limitation && <div className="warning-box"><strong>⚠ 注意</strong><p>{story.limitation}</p></div>}
      <section className="detail-entities">
        <p className="eyebrow">CORE AUTHORS</p>
        {story.authors.map((id) => {
          const person = PEOPLE.find((item) => item.id === id)!;
          return <button className="entity-card" key={id} onClick={() => onPerson(id)}><Avatar initials={person.initials} /><span><b>{person.name}</b><small>{person.role} · {person.institution}</small><em>{person.focus.join(" · ")}</em></span><i>→</i></button>;
        })}
      </section>
      <section className="detail-entities">
        <p className="eyebrow">INSTITUTIONS</p>
        <div className="institution-buttons">{story.institutions.map((id) => {
          const institution = INSTITUTIONS.find((item) => item.id === id)!;
          return <button key={id} onClick={() => onInstitution(id)}><b>{institution.short}</b><span>{institution.name}<small>{institution.location}</small></span><i>→</i></button>;
        })}</div>
      </section>
      <div className="source-stack"><p className="eyebrow">STORY CLUSTER · {story.sources.length} SOURCES</p>{story.sources.map((source, i) => <button key={source} onClick={() => showExternalDemo(source)}><span>{i === 0 ? "ORIGINAL" : String(i + 1).padStart(2, "0")}</span><b>{source}</b><i>↗</i></button>)}</div>
      <div className="detail-feedback"><p>这条解释对你有帮助吗？</p><FeedbackBar selected={selectedFeedback} onFeedback={onFeedback} /></div>
    </div>
  );
}

function Avatar({ initials, small = false }: { initials: string; small?: boolean }) {
  return <span className={`avatar ${small ? "small" : ""}`} aria-label="可靠照片暂缺，显示姓名首字母">{initials}</span>;
}

function Drawer({ title, onClose, nested = false, pinned = false, mobileOpen = true, children }: { title: string; onClose: () => void; nested?: boolean; pinned?: boolean; mobileOpen?: boolean; children: React.ReactNode }) {
  return (
    <div className={`drawer-layer ${nested ? "nested" : ""} ${pinned ? "pinned" : ""} ${mobileOpen ? "mobile-open" : ""}`} role="dialog" aria-modal={pinned ? "false" : "true"}>
      <button className="drawer-scrim" aria-label="关闭" onClick={onClose} />
      <aside className="drawer-panel">
        <div className="drawer-bar"><span>{title}</span><button onClick={onClose}>[ close ]</button></div>
        {children}
      </aside>
    </div>
  );
}

function TermModal({ term, onClose }: { term: Term; onClose: () => void }) {
  return (
    <div className="term-modal-layer" role="dialog" aria-modal="true">
      <button className="term-scrim" aria-label="关闭术语" onClick={onClose} />
      <div className="term-modal">
        <div className="term-modal-top"><span>TERMINOLOGY</span><button onClick={onClose}>×</button></div>
        <p className="term-zh">{term.zh}</p>
        <h2>{term.en}{term.abbr && <small>{term.abbr}</small>}</h2>
        <div className="term-definition"><span>中文</span><p>{term.zhExplanation}</p></div>
        <div className="term-definition"><span>ENGLISH</span><p>{term.enExplanation}</p></div>
        <button className="term-close" onClick={onClose}>知道了</button>
      </div>
    </div>
  );
}

function PersonProfile({ person, isSaved, onSave, onInstitution, onStory }: { person: Person; isSaved: boolean; onSave: () => void; onInstitution: () => void; onStory: (story: Story) => void }) {
  const related = STORIES.filter((story) => story.authors.includes(person.id));
  return (
    <div className="profile-content">
      <div className="profile-hero"><Avatar initials={person.initials} /><div><p className="eyebrow">RESEARCHER</p><h2>{person.name}</h2><p>{person.role}</p><button onClick={onInstitution}>{person.institution} →</button></div></div>
      <button className={`save-profile ${isSaved ? "active" : ""}`} onClick={onSave}>{isSaved ? "★ 已收藏" : "☆ 收藏人物"}</button>
      <ProfileSection label="他 / 她是谁"><p>{person.bio}</p></ProfileSection>
      <ProfileSection label="教育和职业经历"><p>{person.career}</p></ProfileSection>
      <ProfileSection label="主要研究方向"><div className="topic-row">{person.focus.map((focus) => <span key={focus}>{focus}</span>)}</div></ProfileSection>
      <ProfileSection label="代表论文 · 3"><div className="paper-list">{person.papers.map((paper, index) => <button key={paper.title} onClick={() => showExternalDemo("Representative paper")}><span>{String(index + 1).padStart(2, "0")}</span><div><b>{paper.title}</b><small>{paper.year} · {paper.note}</small></div><i>↗</i></button>)}</div></ProfileSection>
      <ProfileSection label="最近相关 Story"><div className="related-list">{related.map((story) => <button key={story.id} onClick={() => onStory(story)}><span>{story.source}</span><b>{story.titleZh}</b><i>→</i></button>)}</div></ProfileSection>
    </div>
  );
}

function InstitutionProfile({ institution, isSaved, onSave, onPerson, onStory }: { institution: Institution; isSaved: boolean; onSave: () => void; onPerson: (person: Person) => void; onStory: (story: Story) => void }) {
  const related = STORIES.filter((story) => story.institutions.includes(institution.id));
  return (
    <div className="profile-content">
      <div className="institution-hero"><span>{institution.short}</span><div><p className="eyebrow">{institution.kind}</p><h2>{institution.name}</h2><p>{institution.location}</p></div></div>
      <button className={`save-profile ${isSaved ? "active" : ""}`} onClick={onSave}>{isSaved ? "★ 已收藏" : "☆ 收藏机构"}</button>
      <ProfileSection label="是什么机构"><p>{institution.description}</p></ProfileSection>
      <ProfileSection label="AI × Bio 主要方向"><p>{institution.direction}</p></ProfileSection>
      <ProfileSection label="为什么值得认识"><p>{institution.why}</p></ProfileSection>
      <ProfileSection label="核心研究者"><div className="mini-people">{institution.researchers.map((id) => {
        const person = PEOPLE.find((item) => item.id === id)!;
        return <button key={id} onClick={() => onPerson(person)}><Avatar initials={person.initials} small /><span><b>{person.name}</b><small>{person.focus.join(" · ")}</small></span><i>→</i></button>;
      })}</div></ProfileSection>
      <ProfileSection label="最近相关 Story"><div className="related-list">{related.map((story) => <button key={story.id} onClick={() => onStory(story)}><span>{story.source}</span><b>{story.titleZh}</b><i>→</i></button>)}</div></ProfileSection>
    </div>
  );
}

function ProfileSection({ label, children }: { label: string; children: React.ReactNode }) {
  return <section className="profile-section"><p className="eyebrow">{label}</p>{children}</section>;
}

function SavedView({ tab, setTab, storyIds, peopleIds, institutionIds, onStory, onPerson, onInstitution }: {
  tab: "stories" | "people" | "institutions"; setTab: (tab: "stories" | "people" | "institutions") => void; storyIds: string[]; peopleIds: string[]; institutionIds: string[]; onStory: (story: Story) => void; onPerson: (person: Person) => void; onInstitution: (institution: Institution) => void;
}) {
  const empty = tab === "stories" ? storyIds.length === 0 : tab === "people" ? peopleIds.length === 0 : institutionIds.length === 0;
  return (
    <div className="page-wrap">
      <div className="page-heading"><p className="eyebrow">YOUR REFERENCE SHELF</p><h1>稍后回来，继续读懂。</h1><p>收藏只保留真正想再看的 Story、人物和机构。</p></div>
      <div className="saved-tabs">
        <button className={tab === "stories" ? "active" : ""} onClick={() => setTab("stories")}>Story <span>{storyIds.length}</span></button>
        <button className={tab === "people" ? "active" : ""} onClick={() => setTab("people")}>People <span>{peopleIds.length}</span></button>
        <button className={tab === "institutions" ? "active" : ""} onClick={() => setTab("institutions")}>Institution <span>{institutionIds.length}</span></button>
      </div>
      {empty && <div className="empty-state"><span>☆</span><h2>还没有收藏</h2><p>在 Feed 里点星标，内容就会出现在这里。</p></div>}
      <div className="saved-list">
        {tab === "stories" && storyIds.map((id) => { const story = STORIES.find((item) => item.id === id)!; return <button key={id} onClick={() => onStory(story)}><span className="saved-source">{story.source}</span><b>{story.title}</b><small>{story.titleZh}</small><i>→</i></button>; })}
        {tab === "people" && peopleIds.map((id) => { const person = PEOPLE.find((item) => item.id === id)!; return <button key={id} onClick={() => onPerson(person)}><Avatar initials={person.initials} /><span><b>{person.name}</b><small>{person.role} · {person.institution}</small></span><i>→</i></button>; })}
        {tab === "institutions" && institutionIds.map((id) => { const institution = INSTITUTIONS.find((item) => item.id === id)!; return <button key={id} onClick={() => onInstitution(institution)}><span className="institution-avatar">{institution.short}</span><span><b>{institution.name}</b><small>{institution.location}</small></span><i>→</i></button>; })}
      </div>
    </div>
  );
}

function SettingsView({ depth, setDepth, examples, setExamples, topics, setTopics, sources, setSources, showToast }: { depth: string; setDepth: (value: string) => void; examples: string; setExamples: (value: string) => void; topics: string[]; setTopics: (value: string[]) => void; sources: string[]; setSources: (value: string[]) => void; showToast: (message: string) => void }) {
  const toggle = (item: string, values: string[], setter: (items: string[]) => void) => setter(values.includes(item) ? values.filter((value) => value !== item) : [...values, item]);
  return (
    <div className="page-wrap settings-page">
      <div className="page-heading"><p className="eyebrow">PERSONAL READING PREFERENCES</p><h1>让解释更适合你。</h1><p>解释偏好和内容偏好分开保存，不会因为“太复杂”而少看到重要主题。</p></div>
      <SettingsGroup number="01" title="Explanation depth" description="控制默认中文解释的技术深度。">
        <ChoiceRow values={[{ id: "simple", label: "浅显", desc: "尽量少术语" }, { id: "balanced", label: "平衡", desc: "默认推荐" }, { id: "technical", label: "专业", desc: "更多技术细节" }]} selected={depth} onSelect={(id) => { setDepth(id); showToast("解释深度已保存"); }} />
      </SettingsGroup>
      <SettingsGroup number="02" title="Example amount" description="决定解释中使用多少具体例子。">
        <ChoiceRow values={[{ id: "few", label: "少量", desc: "更简洁" }, { id: "some", label: "适量", desc: "关键处举例" }, { id: "many", label: "更多", desc: "更具体" }]} selected={examples} onSelect={(id) => { setExamples(id); showToast("例子偏好已保存"); }} />
      </SettingsGroup>
      <SettingsGroup number="03" title="Topics" description="影响 For You 的排序，不会从 Latest 删除内容。">
        <ToggleChips items={["蛋白质设计", "药物发现", "单细胞", "基因组学", "实验自动化", "临床 AI"]} selected={topics} onToggle={(item) => toggle(item, topics, setTopics)} />
      </SettingsGroup>
      <SettingsGroup number="04" title="Sources" description="第一版优先使用论文与权威索引。">
        <ToggleChips items={["arXiv", "bioRxiv", "PubMed", "OpenAlex", "Lab blogs"]} selected={sources} onToggle={(item) => toggle(item, sources, setSources)} />
      </SettingsGroup>
      <SettingsGroup number="05" title="Geography" description="当前产品的 hard filter。">
        <div className="geo-lock"><span className="status-dot" /><div><b>United States + Europe</b><small>已锁定 · 后续可通过配置修改</small></div><span>LOCKED</span></div>
      </SettingsGroup>
    </div>
  );
}

function SettingsGroup({ number, title, description, children }: { number: string; title: string; description: string; children: React.ReactNode }) {
  return <section className="settings-group"><div className="settings-title"><span>{number}</span><div><h2>{title}</h2><p>{description}</p></div></div>{children}</section>;
}

function ChoiceRow({ values, selected, onSelect }: { values: { id: string; label: string; desc: string }[]; selected: string; onSelect: (id: string) => void }) {
  return <div className="choice-row">{values.map((value) => <button key={value.id} className={selected === value.id ? "active" : ""} onClick={() => onSelect(value.id)}><b>{value.label}</b><small>{value.desc}</small></button>)}</div>;
}

function ToggleChips({ items, selected, onToggle }: { items: string[]; selected: string[]; onToggle: (item: string) => void }) {
  return <div className="toggle-chips">{items.map((item) => <button key={item} className={selected.includes(item) ? "active" : ""} onClick={() => onToggle(item)}><span>{selected.includes(item) ? "✓" : "+"}</span>{item}</button>)}</div>;
}

function showExternalDemo(source: string) {
  window.dispatchEvent(new CustomEvent("bioai:toast", { detail: source }));
  alert(`${source}\n\nPhase 1 使用 mock source；Phase 3 接入真实来源后将在新窗口打开。`);
}
