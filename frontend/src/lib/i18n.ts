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
// Translation entries are typically static strings, but a few are
// formatter functions that interpolate one or more values (counts,
// dates, etc.). The signatures vary, so we leave the function shape
// intentionally loose — call sites assert the specific signature with
// `as (...) => string` at the use site.
type Dict = Record<
  string,
  string | ((...args: never[]) => string)
>;

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

// ----------------------------------------------------------------------------
// Pricing / Subscription
// ----------------------------------------------------------------------------

export const PRICING_STRINGS: Record<Lang, Dict> = {
  en: {
    eyebrow: "Pricing",
    title: "Pay only when you need professional services",
    subtitle:
      "Free for casual document review and one-off lawyer searches. Upgrade to Pro when your data room outgrows the basics.",
    freeTitle: "Free",
    freePrice: "$0",
    freeUnit: "/ month",
    freeBlurb: "For checking a quick document or running a single lawyer search.",
    freeFeat1: "10 document extractions / month",
    freeFeat2: "Lawyer search at $15 per report",
    freeFeat3: "Permanent access to purchased reports",
    freeFeat4: "MCP + Claude integration",
    freeCTA: "Get started",
    proTitle: "Pro",
    proPrice: "$20",
    proUnit: "/ month",
    proBadge: "Most popular",
    proBlurb: "For navigators actively managing their visa, tax, or compliance work.",
    proFeat1: "Unlimited document extractions",
    proFeat2: "1 lawyer search included / month",
    proFeat3: "Additional searches at $15 each",
    proFeat4: "Cancel anytime in the billing portal",
    proCTA: "Start Pro",
    proCTAFromTrial: "Continue Pro",
    proCTASignedOut: "Sign in to subscribe",
    trialNote:
      "Already paid for a lawyer search? You're already on a 30-day Pro trial — no card required.",
    faqTitle: "Questions",
    faq1Q: "What counts as an extraction?",
    faq1A:
      "Every document you upload triggers OCR + structured extraction. Re-uploading the same file counts again — the cost is per processing run, not per stored file.",
    faq2Q: "What happens at the end of my trial?",
    faq2A:
      "If you've added a card, Pro auto-renews at $20/month. If you haven't, the trial expires and your account drops to Free. You can cancel anytime before then with no charge.",
    faq3Q: "Can I keep my reports if I cancel?",
    faq3A:
      "Yes — every report you've paid for stays accessible from your dashboard, forever. Cancellation only affects future entitlements.",
    faq4Q: "Do trial users get the free lawyer search?",
    faq4A:
      "No — the included monthly search is a paid-Pro perk only. Trial users still pay $15 per search, but get unlimited extractions during the trial.",
    backHome: "← Back to home",
  },
  zh: {
    eyebrow: "套餐",
    title: "按需付费,无月租门槛",
    subtitle:
      "偶尔上传一份文件、做一次律所搜索 — 免费即可。当您的资料室真正进入活跃使用期,再升级到 Pro。",
    freeTitle: "免费版",
    freePrice: "$0",
    freeUnit: "/ 月",
    freeBlurb: "适合快速审阅一份文件或一次性律所搜索。",
    freeFeat1: "每月 10 次文档解析",
    freeFeat2: "律所搜索单次 $15",
    freeFeat3: "已购报告永久可访问",
    freeFeat4: "支持 MCP / Claude 集成",
    freeCTA: "开始使用",
    proTitle: "Pro",
    proPrice: "$20",
    proUnit: "/ 月",
    proBadge: "推荐",
    proBlurb: "适合正在主动处理签证、税务或合规事务的用户。",
    proFeat1: "无限次文档解析",
    proFeat2: "每月赠送 1 次律所搜索",
    proFeat3: "超出后每次 $15",
    proFeat4: "随时通过 Stripe 自助取消",
    proCTA: "开通 Pro",
    proCTAFromTrial: "继续 Pro 订阅",
    proCTASignedOut: "登录后订阅",
    trialNote:
      "购买过律所搜索? 您已自动获得 30 天 Pro 试用 — 无需信用卡。",
    faqTitle: "常见问题",
    faq1Q: "什么算一次解析?",
    faq1A:
      "每次上传文档都会触发 OCR 和结构化抽取。同一份文件重新上传也会重新计费 — 费用按处理次数计,不按存储文件数。",
    faq2Q: "试用结束后会怎样?",
    faq2A:
      "如已绑定信用卡,Pro 将以 $20/月自动续费;未绑定则试用到期后自动降级为免费版。期间可随时取消,无任何费用。",
    faq3Q: "取消后我购买过的报告还能看吗?",
    faq3A:
      "可以 — 已付费的报告永久保留在您的账户中。取消订阅只会影响未来的权益。",
    faq4Q: "试用用户也能获赠律所搜索吗?",
    faq4A:
      "不能 — 每月赠送 1 次律所搜索仅限付费 Pro 用户。试用用户仍需按 $15 单次付费,但解析次数在试用期内不限。",
    backHome: "← 返回首页",
  },
};

// Strings for the dashboard quota badge + upload paywall modal.
export const PRO_STRINGS: Record<Lang, Dict> = {
  en: {
    badgeFree: (used: number, limit: number) =>
      `${used} / ${limit} extractions this month`,
    badgePro: "Pro · unlimited",
    badgeTrial: "Pro Trial · unlimited",
    badgeManage: "Manage",
    badgeUpgrade: "Upgrade",
    paywallTitle: "You've used all 10 free extractions this month",
    paywallBody:
      "Each upload triggers OCR + structured extraction (a paid LLM call). Free resets on the 1st of next month — or upgrade to Pro for unlimited extractions and one free lawyer search per month.",
    paywallUpgrade: "Upgrade to Pro · $20/mo",
    paywallDismiss: "Maybe later",
    paywallReset: (date: string) => `Resets ${date}`,
    proSearchHint: "1 free search included this period",
    proSearchUsed: "Free search used this period — additional are $15",
  },
  zh: {
    badgeFree: (used: number, limit: number) =>
      `本月已用 ${used} / ${limit} 次解析`,
    badgePro: "Pro · 无限制",
    badgeTrial: "Pro 试用 · 无限制",
    badgeManage: "管理",
    badgeUpgrade: "升级",
    paywallTitle: "本月免费解析次数已用完",
    paywallBody:
      "每次上传都会触发 OCR + 结构化抽取(付费 LLM 调用)。免费额度将于下月 1 日重置 — 或升级到 Pro,享受无限次解析及每月 1 次免费律所搜索。",
    paywallUpgrade: "升级到 Pro · $20/月",
    paywallDismiss: "稍后再说",
    paywallReset: (date: string) => `${date} 重置`,
    proSearchHint: "本期赠送 1 次免费搜索",
    proSearchUsed: "本期赠送已用完,后续每次 $15",
  },
};
