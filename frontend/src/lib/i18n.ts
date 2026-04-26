"use client";

import { useEffect, useState } from "react";

export type Lang = "en" | "zh";

const STORAGE_KEY = "guardian_lang";

function detectInitial(): Lang {
  if (typeof window === "undefined") return "en";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "zh" || stored === "en") return stored;
  // First visit: pick from browser locale.
  const nav = navigator.language || (navigator as { userLanguage?: string }).userLanguage || "";
  return nav.toLowerCase().startsWith("zh") ? "zh" : "en";
}

/** Hook: returns the active language and a setter. Persists to localStorage. */
export function useLang(): { lang: Lang; setLang: (l: Lang) => void } {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => {
    setLangState(detectInitial());
  }, []);
  const setLang = (l: Lang) => {
    setLangState(l);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, l);
    }
  };
  return { lang, setLang };
}

/**
 * Strings for the find-lawyer flow. UI chrome only — search results,
 * firm rationales, credentials, and the PDF/HTML report content come
 * from the model in English. A separate "render report in Chinese"
 * feature would require an additional model pass.
 */
type Dict = Record<string, string | ((n: number) => string)>;

export const FIND_LAWYER_STRINGS: Record<Lang, Dict> = {
  en: {
    // Intake
    eyebrow: "Find the right professional",
    pageTitle: "Tell us about your case. We’ll find the right lawyer.",
    pageBlurb:
      "Describe your situation and optionally upload any relevant documents. Three research agents will search across different axes — elite boutiques, startup-focused firms, and federal-court litigators — and return a ranked tier list scored against externally-verifiable credentials only.",
    fieldVertical: "What kind of help do you need?",
    fieldPurpose: "Short label for this engagement",
    fieldPurposeHelp: "Used to tag results so you can find them later.",
    fieldPurposePlaceholder: "e.g. H-1B petition — 2026 cap",
    fieldBrief: "Case description",
    fieldBriefHelp:
      "The more specific, the better — agents use this to judge whether a firm has published on your exact issue.",
    fieldBriefPlaceholder:
      'Tell the research agents about your situation. Include:\n• The specific legal/tax question\n• Any regulatory wrinkles you already know about\n• Geography preferences (home state, willingness to engage remotely)\n• Budget sensitivity\n• Timeline',
    fieldFiles: "Supporting documents (optional)",
    fieldFilesHelp: "PDF, DOCX, TXT, or MD · up to 8 files",
    fieldFilesEmpty: "Drop files or click to upload",
    fieldFilesSelected: (n: number) =>
      n === 1 ? "1 file selected" : `${n} files selected`,
    btnBack: "← Back",
    btnStart: "Start search",
    btnStarting: "Starting search…",
    blockerLead: "To enable search:",
    blockerPurpose: "add a short engagement label (4+ chars)",
    blockerBrief: (n: number) =>
      `case description needs ${n} more character${n === 1 ? "" : "s"}`,
    briefWeak: "needs more detail",
    briefOkay: "okay — more detail = better matches",
    briefStrong: "strong context",
    ready: "Ready to dispatch 3 research agents in parallel.",
    asideHowTitle: "How this works",
    asideHowSub: "Three research agents, one ranked tier list.",
    asideHowBlurb:
      "Each agent searches a distinct slice of the market so you don’t end up with ten clones of the same firm.",
    aside01Title: "Elite boutiques",
    aside01Body:
      "Chambers-ranked firms with AILA past leadership and state-bar certifications.",
    aside02Title: "Startup + founder-focused",
    aside02Body:
      "Firms that have actually written about the 2024 H-1B rule and handle owner-beneficiary petitions.",
    aside03Title: "Federal-court litigators",
    aside03Body:
      "Former DOJ/OIL attorneys; counsel of record in ITServe-lineage APA challenges.",
    asideStdTitle: "Credential standard",
    asideStdBody:
      "Scoring uses externally-verifiable signals only — Chambers, AILA elected leadership, PACER filings, third-party press. A firm’s own marketing copy is excluded.",

    // Status page
    statusPagePill: "Professional search",
    statusBtnNew: "← New search",
    statusStarted: "Started",
    statusFinished: "finished",
    statusFailed: "Search failed",
    statusAgents: "Research agents",
    statusPolling: "Polling every 3s…",
    statusQueued: "Queued — dispatching shortly…",
    statusSpinning: "Spinning up research agents…",
    statusSpinningSub:
      "This typically takes 60 – 120 seconds per agent, running in parallel.",
    personaSearching: "searching…",
    personaFailed: "failed",
    personaFirms: (n: number) => `${n} firms`,
    tierTitle: "Tier report",
    tierFirms: (n: number) => `${n} firms`,
    tierBlurb:
      "Scored by externally-verifiable credentials (Chambers, AILA leadership, PACER filings) — marketing copy from firm websites is excluded from weighting.",
    tierEmptyHint:
      "Search finished but no firms were ingested. Check per-agent errors above.",
    btnDownloadPDF: "Download PDF",
    btnDownloadPDFBusy: "Preparing PDF…",
    btnViewWeb: "View web version",
    rowFee: "Fee range",
    rowStatus: "Status",
    rowNext: "Next",
    statusValueQueued: "queued",
    statusValueRunning: "running",
    statusValueComplete: "complete",
    statusValueFailedShort: "failed",
    loading: "Loading…",
  },
  zh: {
    // Intake
    eyebrow: "寻找合适的专业人士",
    pageTitle: "告诉我们您的情况，我们帮您找到合适的律师。",
    pageBlurb:
      "描述您的情况，并可选择上传相关文件。三个研究代理将从不同角度并行搜索 — 精英精品律所、初创/创始人导向律所、联邦法院诉讼律师 — 并基于可外部验证的资质对律所进行打分排名。",
    fieldVertical: "您需要哪类专业帮助？",
    fieldPurpose: "本次咨询的简短标签",
    fieldPurposeHelp: "用于标记搜索结果，方便之后查找。",
    fieldPurposePlaceholder: "例如：H-1B 申请 — 2026 抽签",
    fieldBrief: "案件描述",
    fieldBriefHelp:
      "越具体越好 — 代理会据此判断律所是否在您的具体议题上发表过观点。",
    fieldBriefPlaceholder:
      "向研究代理说明您的情况，建议包括：\n• 具体的法律 / 税务问题\n• 您已知的监管难点\n• 地理位置偏好（所在州、是否接受远程合作）\n• 预算敏感度\n• 时间线",
    fieldFiles: "辅助文件（可选）",
    fieldFilesHelp: "PDF、DOCX、TXT 或 MD · 最多 8 个文件",
    fieldFilesEmpty: "拖放文件或点击上传",
    fieldFilesSelected: (n: number) => `已选择 ${n} 个文件`,
    btnBack: "← 返回",
    btnStart: "开始搜索",
    btnStarting: "正在启动搜索…",
    blockerLead: "请补全以下信息以启用搜索：",
    blockerPurpose: "请填写至少 4 个字符的咨询标签",
    blockerBrief: (n: number) => `案件描述还需要 ${n} 个字符`,
    briefWeak: "需要更多细节",
    briefOkay: "可以了 — 描述越详细，匹配越精准",
    briefStrong: "信息充分",
    ready: "准备就绪，将并行调度 3 个研究代理。",
    asideHowTitle: "工作原理",
    asideHowSub: "三个研究代理，一份排名报告。",
    asideHowBlurb:
      "每个代理从不同的角度搜索市场，避免十家相似律所重复出现。",
    aside01Title: "精英精品律所",
    aside01Body:
      "Chambers 排名律所，拥有 AILA 前任领导职务及州律师协会认证。",
    aside02Title: "初创 / 创始人导向",
    aside02Body:
      "对 2024 年 H-1B 新规有公开分析、处理过 owner-beneficiary 申请的律所。",
    aside03Title: "联邦法院诉讼律师",
    aside03Body:
      "前司法部 OIL 律师；ITServe 系列 APA 诉讼的代理律师。",
    asideStdTitle: "资质标准",
    asideStdBody:
      "评分仅采用可外部验证的信号 — Chambers、AILA 选任领导职务、PACER 法院记录、第三方媒体。律所自家的营销内容不计入评分。",

    // Status page
    statusPagePill: "专业人士搜索",
    statusBtnNew: "← 新搜索",
    statusStarted: "开始时间",
    statusFinished: "完成于",
    statusFailed: "搜索失败",
    statusAgents: "研究代理",
    statusPolling: "每 3 秒轮询…",
    statusQueued: "排队中 — 即将派发…",
    statusSpinning: "正在启动研究代理…",
    statusSpinningSub:
      "每个代理通常需要 60 – 120 秒，多个代理并行运行。",
    personaSearching: "搜索中…",
    personaFailed: "失败",
    personaFirms: (n: number) => `共 ${n} 家律所`,
    tierTitle: "层级排名报告",
    tierFirms: (n: number) => `${n} 家律所`,
    tierBlurb:
      "基于可外部验证的资质（Chambers 评级、AILA 领导职务、PACER 法院记录）评分 — 律所自家营销内容不计入。",
    tierEmptyHint: "搜索完成但未导入任何律所。请查看上方各代理的错误信息。",
    btnDownloadPDF: "下载 PDF",
    btnDownloadPDFBusy: "正在生成 PDF…",
    btnViewWeb: "查看网页版",
    rowFee: "费用范围",
    rowStatus: "状态",
    rowNext: "下一步",
    statusValueQueued: "排队中",
    statusValueRunning: "运行中",
    statusValueComplete: "已完成",
    statusValueFailedShort: "失败",
    loading: "加载中…",
  },
};

/** Vertical labels are translated separately so they stay in sync with
 *  whatever the dropdown shows. */
export const VERTICAL_LABELS: Record<Lang, Record<string, { label: string; helper: string }>> = {
  en: {
    immigration_attorney: {
      label: "Immigration attorney — H-1B / general",
      helper: "H-1B, OPT, employment-based, family-based, asylum",
    },
    immigration_eb5: {
      label: "Immigration attorney — EB-5",
      helper: "Investor visas: I-526E, I-829, source-of-funds, RC due diligence (RIA-era)",
    },
    tax_attorney: { label: "Tax attorney", helper: "International tax, FBAR, expat, complex filings" },
    corporate_attorney: { label: "Corporate attorney", helper: "Formation, contracts, M&A, equity" },
    cpa: { label: "CPA", helper: "Tax prep, nonresident filings, business accounting" },
    bank: { label: "Bank / banker", helper: "Business banking, non-US-resident accounts" },
    caa: { label: "Certifying Acceptance Agent (ITIN)", helper: "ITIN applications" },
  },
  zh: {
    immigration_attorney: {
      label: "移民律师 — H-1B / 综合",
      helper: "H-1B、OPT、雇主担保、家庭担保、政治庇护",
    },
    immigration_eb5: {
      label: "移民律师 — EB-5 投资移民",
      helper: "投资者签证：I-526E、I-829、资金来源、RC 项目尽调（RIA 新规）",
    },
    tax_attorney: { label: "税务律师", helper: "国际税务、FBAR、海外居民、复杂申报" },
    corporate_attorney: { label: "公司律师", helper: "公司设立、合同、并购、股权" },
    cpa: { label: "注册会计师（CPA）", helper: "报税、非居民申报、企业会计" },
    bank: { label: "银行 / 银行家", helper: "企业银行、非美国居民账户" },
    caa: { label: "ITIN 认证代理（CAA）", helper: "ITIN 申请" },
  },
};

export const PERSONA_LABELS_I18N: Record<Lang, Record<string, string>> = {
  en: {
    elite_boutique: "Elite Boutique",
    startup_founder: "Startup Founder",
    litigation_contrarian: "Litigation Contrarian",
    eb5_specialist: "EB-5 Specialist",
    securities_sophisticated: "Securities Sophisticated",
    source_of_funds: "Source-of-Funds Specialist",
  },
  zh: {
    elite_boutique: "精英精品律所",
    startup_founder: "初创 / 创始人导向",
    litigation_contrarian: "联邦诉讼律师",
    eb5_specialist: "EB-5 专家",
    securities_sophisticated: "证券法精通",
    source_of_funds: "资金来源专家",
  },
};

export function personaLabel(lang: Lang, id: string): string {
  if (id in PERSONA_LABELS_I18N[lang]) return PERSONA_LABELS_I18N[lang][id];
  if (id.startsWith("tuned_")) {
    const tail = id.slice("tuned_".length).replace(/_/g, " ");
    return lang === "zh" ? `定制 · ${tail}` : `Tuned · ${tail.replace(/\b\w/g, (c) => c.toUpperCase())}`;
  }
  return id.replace(/_/g, " ");
}
