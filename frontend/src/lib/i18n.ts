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
    personaSkipped: "skipped",
    personaFirms: (n: number) => `${n} firms`,
    tierTitle: "Tier report",
    tierFirms: (n: number) => `${n} firms`,
    tierBlurb:
      "Scored by externally-verifiable credentials (Chambers, AILA leadership, PACER filings) — marketing copy from firm websites is excluded from weighting.",
    tierEmptyHint:
      "Search finished but no firms were ingested. Please rerun the search or contact Guardian support.",
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
    personaSkipped: "已跳过",
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
      label: "Immigration attorney — general",
      helper: "OPT, employment-based, family-based, asylum",
    },
    immigration_h1b: {
      label: "Immigration attorney — H-1B",
      helper: "H-1B cap, transfer, amendment, founder / small-employer petitions, OPT bridge",
    },
    immigration_o1_niw: {
      label: "Immigration attorney — O-1 / NIW",
      helper: "O-1, NIW, EB-1A, extraordinary ability, profile evidence, RFE / appeal strategy",
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
      label: "移民律师 — 综合",
      helper: "OPT、雇主担保、家庭担保、政治庇护",
    },
    immigration_h1b: {
      label: "移民律师 — H-1B",
      helper: "H-1B 抽签、transfer、amendment、创始人 / 小雇主 petition、OPT 衔接",
    },
    immigration_o1_niw: {
      label: "移民律师 — O-1 / NIW",
      helper: "O-1、NIW、EB-1A、杰出人才、证据策略、RFE / appeal 策略",
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
    employment_green_card: "Employment Green Card",
    family_humanitarian: "Family / Humanitarian",
    student_opt_status: "Student / OPT Status",
    niw_eb1_profile: "NIW / EB-1 Profile",
    o1_extraordinary_ability: "O-1 Extraordinary Ability",
    talent_rfe_appeals: "Talent RFE / Appeals",
    eb5_specialist: "EB-5 Specialist",
    securities_sophisticated: "Securities Sophisticated",
    source_of_funds: "Source-of-Funds Specialist",
    i829_redeployment: "I-829 / Redeployment",
    mandamus_delay: "Mandamus / Delay",
    regional_center_diligence: "Regional Center Diligence",
    cross_border_tax: "Cross-Border Tax",
    crypto_digital_assets: "Crypto / Digital Assets",
    penalty_relief: "Penalty Relief",
    disclosure_remediation: "Disclosure Remediation",
    estate_gift_cross_border: "Estate / Gift",
    international_info_returns: "International Information Returns",
    startup_formation: "Startup Formation",
    safes_and_notes: "SAFEs and Notes",
    cross_border_equity: "Cross-Border Equity",
    commercial_ip_contracts: "Commercial / IP Contracts",
    employment_contractors: "Employment / Contractors",
    m_and_a_diligence: "M&A Diligence",
    international_tax: "International Tax CPA",
    equity_crypto_tax: "Equity / Crypto Tax",
    expat_tax: "Expat Tax",
    foreign_owned_entity: "Foreign-Owned Entity",
    founder_accounting: "Founder Accounting",
    state_sales_tax: "State / Sales Tax",
    audit_defense: "Audit Defense",
    foreign_founder_banking: "Foreign-Founder Banking",
    startup_banking: "Startup Banking",
    premium_relationship: "Premium Relationship",
    irs_authorized_caa: "IRS-Authorized CAA",
    china_corridor_caa: "China-Corridor CAA",
    fast_turnaround_caa: "Fast-Turnaround CAA",
  },
  zh: {
    elite_boutique: "精英精品律所",
    startup_founder: "初创 / 创始人导向",
    litigation_contrarian: "联邦诉讼律师",
    employment_green_card: "职业绿卡 / 杰出人才",
    family_humanitarian: "家庭 / 人道移民",
    student_opt_status: "学生 / OPT 身份",
    niw_eb1_profile: "NIW / EB-1 背景策略",
    o1_extraordinary_ability: "O-1 杰出人才",
    talent_rfe_appeals: "人才类 RFE / 上诉",
    eb5_specialist: "EB-5 专家",
    securities_sophisticated: "证券法精通",
    source_of_funds: "资金来源专家",
    i829_redeployment: "I-829 / 再投资",
    mandamus_delay: "曼达穆斯 / 延误诉讼",
    regional_center_diligence: "区域中心尽调",
    cross_border_tax: "跨境税务",
    crypto_digital_assets: "加密资产税务",
    penalty_relief: "罚款减免",
    disclosure_remediation: "披露 / 补正",
    estate_gift_cross_border: "跨境赠与 / 遗产",
    international_info_returns: "国际信息申报",
    startup_formation: "初创设立",
    safes_and_notes: "SAFE / 可转债",
    cross_border_equity: "跨境股权",
    commercial_ip_contracts: "商业合同 / IP",
    employment_contractors: "雇佣 / 承包商",
    m_and_a_diligence: "并购尽调",
    international_tax: "国际税务 CPA",
    equity_crypto_tax: "股权 / 加密税务",
    expat_tax: "海外美国纳税人",
    foreign_owned_entity: "外国人持股实体",
    founder_accounting: "创始人会计",
    state_sales_tax: "州税 / 销售税",
    audit_defense: "稽查应对",
    foreign_founder_banking: "外国创始人银行",
    startup_banking: "初创银行",
    premium_relationship: "高端关系银行",
    irs_authorized_caa: "IRS 授权 CAA",
    china_corridor_caa: "中国通道 CAA",
    fast_turnaround_caa: "快速 ITIN CAA",
  },
};

/**
 * Per-vertical preview of the search agents the selector can run for the
 * intake page's right-hand "How this works" panel. The list shifts to
 * match the selected vertical so users see what kind of professionals
 * we can look for, while the backend prunes irrelevant agents from the
 * actual run. Falls back to immigration_attorney when a vertical doesn't
 * yet have a curated preview.
 *
 * The backend ships matching persona YAMLs for every vertical listed in
 * VERTICAL_LABELS; keep this preview list in sync with those canonical
 * search axes.
 */
type PersonaPreview = { title: string; body: string };

export const PERSONA_PREVIEWS_BY_VERTICAL: Record<Lang, Record<string, PersonaPreview[]>> = {
  en: {
    immigration_h1b: [
      {
        title: "H-1B boutiques",
        body: "Business-immigration firms with specialty-occupation, wage, amendment, and transfer judgment.",
      },
      {
        title: "Startup + founder H-1B",
        body: "Counsel for owner-beneficiary, small-employer, pre-revenue, and cap-table-sensitive petitions.",
      },
      {
        title: "H-1B litigators",
        body: "AAO, APA, mandamus, denial, NOID, and difficult RFE strategy for high-risk filings.",
      },
      {
        title: "F-1 / OPT bridge counsel",
        body: "SEVIS, CPT, OPT/STEM OPT, cap-gap, travel, and change-of-status timing before H-1B.",
      },
    ],
    immigration_o1_niw: [
      {
        title: "NIW + EB-1A strategy",
        body: "Profile evaluation, field-impact evidence, recommendation letters, citations, publications, and I-140 timing.",
      },
      {
        title: "O-1 petition counsel",
        body: "O-1A/O-1B criteria, advisory opinions, agent petitioners, itineraries, and extension strategy.",
      },
      {
        title: "Talent-petition appeals",
        body: "RFE, NOID, denial, AAO, refile, and federal-court judgment for O-1, NIW, and EB-1A cases.",
      },
    ],
    immigration_attorney: [
      {
        title: "Elite boutiques",
        body: "Chambers-ranked firms with AILA past leadership and state-bar certifications.",
      },
      {
        title: "Startup + founder-focused",
        body: "Firms that have actually written about the 2024 H-1B rule and handle owner-beneficiary petitions.",
      },
      {
        title: "Federal-court litigators",
        body: "Former DOJ/OIL attorneys; counsel of record in ITServe-lineage APA challenges.",
      },
      {
        title: "Employment green-card counsel",
        body: "PERM, NIW, EB-1, O-1, priority-date, and adjustment strategy for work-based cases.",
      },
      {
        title: "Student / OPT status counsel",
        body: "F-1, OPT/STEM OPT, CPT, SEVIS, cap-gap, reinstatement, and travel-timing risk.",
      },
      {
        title: "Family + humanitarian counsel",
        body: "I-130/I-485, waivers, asylum, VAWA, U/T visas, and removal-adjacent risk.",
      },
    ],
    immigration_eb5: [
      {
        title: "EB-5 specialists",
        body: "Chambers EB-5 ranking, AILA EB-5 Committee leadership, IIUSA participation, and EB5 Investors Top-25 recognition.",
      },
      {
        title: "Securities-sophisticated counsel",
        body: "RIA integrity-period offering structures, redeployment mechanics, and federal-court securities-law fluency.",
      },
      {
        title: "Source-of-funds specialists",
        body: "Multi-step path-of-funds tracing for China / India / Vietnam origin; documented federal-court SOF wins.",
      },
      {
        title: "Regional-center diligence",
        body: "Project, NCE/JCE, TEA/set-aside, business-plan, and offering-package review before wiring funds.",
      },
      {
        title: "I-829 + redeployment",
        body: "Sustainment, material change, job creation, redeployment, and post-investment RFE strategy.",
      },
      {
        title: "Mandamus / delay litigation",
        body: "EB-5-specific APA and mandamus counsel for delayed I-526E, I-829, AOS, or consular stages.",
      },
    ],
    tax_attorney: [
      {
        title: "Cross-border practitioners",
        body: "Treaty-position attorneys with FTC / GILTI / Subpart F experience and active US-China practice.",
      },
      {
        title: "Penalty-relief litigators",
        body: "Reasonable-cause defenses with Tax Court track record and IRS-appeals experience.",
      },
      {
        title: "Disclosure + remediation",
        body: "Streamlined / OVDP / FBAR / FATCA practice; specialty in late-filing remediation.",
      },
      {
        title: "Information-return penalties",
        body: "5471, 5472, 3520, 8938, 8865, 8858, FBAR, and reasonable-cause strategy.",
      },
      {
        title: "Crypto + digital assets",
        body: "DeFi, staking, airdrops, wallet tracing, basis reconstruction, and amended-position risk.",
      },
      {
        title: "Estate + gift cross-border",
        body: "Foreign gifts, inheritance, trusts, 3520/709, expatriation, and family wealth transfers.",
      },
    ],
    cpa: [
      {
        title: "International tax CPAs",
        body: "1040NR, dual-status, treaty positions, and foreign-owned US LLC reporting (5472 / 1120-F).",
      },
      {
        title: "Founder-friendly bookkeepers",
        body: "S-corp / C-corp / LLC bookkeeping, payroll, and quarterly estimates with founders' work-style.",
      },
      {
        title: "Audit-defense specialists",
        body: "IRS examination representation; voluntary disclosure / streamlined consulting.",
      },
      {
        title: "Foreign-owned entity CPAs",
        body: "Form 5472, pro-forma 1120, disregarded entities, owner ledgers, EIN/ITIN, and BOI coordination.",
      },
      {
        title: "Expat tax CPAs",
        body: "FEIE, FTC, FBAR/FATCA, foreign employer, dual-status, and globally mobile taxpayer filings.",
      },
      {
        title: "Equity + crypto tax CPAs",
        body: "ISOs, NSOs, RSUs, 83(b), AMT, 8949, crypto basis, and transaction reconciliation.",
      },
      {
        title: "State + sales-tax CPAs",
        body: "Nexus, registrations, franchise tax, SaaS/ecommerce taxability, notices, and filing calendars.",
      },
    ],
    corporate_attorney: [
      {
        title: "Startup formation specialists",
        body: "Delaware C-corp + founder agreements, vesting, IP assignment, 83(b) workflow.",
      },
      {
        title: "SAFE / convertible-note counsel",
        body: "Clean YC-SAFE practice, 409A coordination, secondary-sale mechanics.",
      },
      {
        title: "Cross-border equity / cap table",
        body: "Foreign founders, NRA tax issues, F-class shares, withholding-tax structuring.",
      },
      {
        title: "Commercial + IP contracts",
        body: "MSAs, SOWs, SaaS terms, DPAs, vendor agreements, IP assignments, and product counsel.",
      },
      {
        title: "Employment + contractors",
        body: "Offer letters, advisor agreements, contractor classification, PEO/payroll, and IP assignment.",
      },
      {
        title: "M&A + diligence",
        body: "LOIs, asset purchases, acqui-hires, escrow, closing mechanics, and small-company diligence.",
      },
    ],
    bank: [
      {
        title: "Foreign-founder friendly banks",
        body: "ITIN onboarding, no-SSN account opening, cross-border KYC.",
      },
      {
        title: "Startup-banking + Stripe-ready",
        body: "Fast onboarding, no minimums, integrates cleanly with Stripe / Mercury / Brex flows.",
      },
      {
        title: "Premium-relationship banks",
        body: "Concierge service, USD/CNY rails, multi-currency wire pricing.",
      },
    ],
    caa: [
      {
        title: "IRS-authorized CAAs",
        body: "Current Form 13551 in good standing; can certify ID copies for ITIN applications.",
      },
      {
        title: "China-corridor practitioners",
        body: "Chinese-language intake; certifications recognized by US consulates in China.",
      },
      {
        title: "Fast-turnaround firms",
        body: "Documented sub-30-day processing times and batch-volume experience.",
      },
    ],
  },
  zh: {
    immigration_h1b: [
      {
        title: "H-1B 精品律所",
        body: "处理 specialty occupation、工资水平、amendment、transfer 和雇主材料判断的商务移民律所。",
      },
      {
        title: "初创 / 创始人 H-1B",
        body: "适合 owner-beneficiary、小雇主、pre-revenue、cap table 敏感的 petition。",
      },
      {
        title: "H-1B 诉讼律师",
        body: "处理 AAO、APA、mandamus、denial、NOID 和高风险 RFE 策略。",
      },
      {
        title: "F-1 / OPT 衔接",
        body: "SEVIS、CPT、OPT/STEM OPT、cap-gap、旅行和 H-1B change-of-status 时点。",
      },
    ],
    immigration_o1_niw: [
      {
        title: "NIW + EB-1A 策略",
        body: "背景评估、领域影响证据、推荐信、引用、发表记录和 I-140 时点。",
      },
      {
        title: "O-1 petition 律师",
        body: "O-1A/O-1B 标准、advisory opinion、agent petitioner、itinerary 和延期策略。",
      },
      {
        title: "人才类 petition 上诉",
        body: "O-1、NIW、EB-1A 的 RFE、NOID、denial、AAO、重新递交和联邦法院判断。",
      },
    ],
    immigration_attorney: [
      {
        title: "精英精品律所",
        body: "Chambers 排名律所,AILA 历任理事会成员,州律协认证。",
      },
      {
        title: "初创 / 创始人导向",
        body: "处理过 2024 年 H-1B 新规、能办理创始人本人持股公司担保的律所。",
      },
      {
        title: "联邦法院诉讼律师",
        body: "前 DOJ / OIL 律师;在 ITServe 系列 APA 诉讼中担任主辩。",
      },
      {
        title: "职业绿卡律师",
        body: "PERM、NIW、EB-1、O-1、优先日和 I-485 / 领馆处理策略。",
      },
      {
        title: "学生 / OPT 身份律师",
        body: "F-1、OPT/STEM OPT、CPT、SEVIS、cap-gap、恢复身份和旅行时点风险。",
      },
      {
        title: "家庭 / 人道移民律师",
        body: "I-130/I-485、豁免、庇护、VAWA、U/T 签证和递解风险。",
      },
    ],
    immigration_eb5: [
      {
        title: "EB-5 专精律所",
        body: "Chambers EB-5 上榜、AILA EB-5 委员会担任要职、IIUSA 成员、EB5 Investors Top-25 律师。",
      },
      {
        title: "证券法精通",
        body: "熟悉 RIA 新规下的发行结构、重新部署机制,以及联邦证券法实务。",
      },
      {
        title: "资金来源专家",
        body: "中国 / 印度 / 越南来源资金多步骤路径追溯;有联邦法院 SOF 胜诉记录。",
      },
      {
        title: "区域中心尽调",
        body: "汇款前审查项目、NCE/JCE、TEA / 预留名额、商业计划和发行文件。",
      },
      {
        title: "I-829 / 再投资",
        body: "维持投资、重大变化、就业创造、再投资和投后 RFE 策略。",
      },
      {
        title: "曼达穆斯 / 延误诉讼",
        body: "针对 I-526E、I-829、AOS 或领馆阶段延误的 EB-5 APA / mandamus 律师。",
      },
    ],
    tax_attorney: [
      {
        title: "跨境税务律师",
        body: "熟悉中美税收协定,FTC / GILTI / Subpart F 实务,有活跃中美客户。",
      },
      {
        title: "罚款减免诉讼律师",
        body: "在税务法院有 reasonable cause 抗辩记录,熟悉 IRS Appeals 流程。",
      },
      {
        title: "披露 / 合规补正",
        body: "Streamlined / OVDP / FBAR / FATCA 实务专精;迟报情况补救经验丰富。",
      },
      {
        title: "国际信息申报罚款",
        body: "5471、5472、3520、8938、8865、8858、FBAR 和 reasonable-cause 策略。",
      },
      {
        title: "加密资产税务",
        body: "DeFi、staking、空投、钱包追踪、成本基础重建和补报风险。",
      },
      {
        title: "跨境赠与 / 遗产",
        body: "外国赠与、继承、信托、3520/709、弃籍税和家庭财富转移。",
      },
    ],
    cpa: [
      {
        title: "国际税务 CPA",
        body: "1040NR、双重身份、协定身份申报,以及外国人持股美国 LLC 报税(5472 / 1120-F)。",
      },
      {
        title: "创始人友好型会计",
        body: "S-corp / C-corp / LLC 账务、工资单、季度预估税款,适合创始人工作节奏。",
      },
      {
        title: "稽查应对专家",
        body: "IRS 审计代表;自愿披露 / streamlined 咨询。",
      },
      {
        title: "外国人持股实体 CPA",
        body: "Form 5472、pro-forma 1120、disregarded entity、业主往来账、EIN/ITIN 和 BOI 协调。",
      },
      {
        title: "海外美国纳税人 CPA",
        body: "FEIE、FTC、FBAR/FATCA、外国雇主、双重身份和全球流动纳税人申报。",
      },
      {
        title: "股权 + 加密税务 CPA",
        body: "ISO、NSO、RSU、83(b)、AMT、8949、加密资产成本基础和交易核对。",
      },
      {
        title: "州税 + 销售税 CPA",
        body: "Nexus、注册、franchise tax、SaaS / 电商税务、通知和申报日历。",
      },
    ],
    corporate_attorney: [
      {
        title: "初创公司设立",
        body: "Delaware C-corp、创始人协议、股权 vesting、知识产权转让、83(b) 流程。",
      },
      {
        title: "SAFE / 可转债律师",
        body: "标准 YC-SAFE 实务、409A 协调、二级市场转让机制。",
      },
      {
        title: "跨境股权 / 股权架构",
        body: "外国创始人、NRA 税务、F 类股、预提税结构设计。",
      },
      {
        title: "商业合同 / IP",
        body: "MSA、SOW、SaaS 条款、DPA、供应商协议、IP 转让和产品法律支持。",
      },
      {
        title: "雇佣 / 承包商",
        body: "offer letter、顾问协议、承包商分类、PEO/工资单和 IP 转让。",
      },
      {
        title: "并购 + 尽调",
        body: "LOI、资产收购、acqui-hire、escrow、交割机制和小公司尽调。",
      },
    ],
    bank: [
      {
        title: "外国创始人友好型银行",
        body: "ITIN 开户、无 SSN 开户、跨境 KYC。",
      },
      {
        title: "初创 + Stripe 兼容",
        body: "开户快、无最低存款、与 Stripe / Mercury / Brex 流程兼容。",
      },
      {
        title: "私人银行级服务",
        body: "礼宾服务、美元 / 人民币通道、多币种电汇定价。",
      },
    ],
    caa: [
      {
        title: "IRS 授权 CAA",
        body: "持有有效 Form 13551,可为 ITIN 申请认证身份证件。",
      },
      {
        title: "中国通道律所",
        body: "中文受理;在中国境内的美国领事馆认可的认证机构。",
      },
      {
        title: "快速处理律所",
        body: "30 天内完成的处理记录,具备批量办理经验。",
      },
    ],
  },
};

/** Pick the preview list for a given vertical, with a sensible fallback. */
export function personaPreviewsFor(lang: Lang, vertical: string): PersonaPreview[] {
  const map = PERSONA_PREVIEWS_BY_VERTICAL[lang];
  return map[vertical] ?? map["immigration_attorney"];
}

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
      "Free for casual document review and one-off professional searches. Upgrade to Pro when your data room outgrows the basics.",
    freeTitle: "Free",
    freePrice: "$0",
    freeUnit: "/ month",
    freeBlurb: "For checking a quick document or running a single professional search.",
    freeFeat1: "10 document extractions / month",
    freeFeat2: "Professional search at $15 per report",
    freeFeat3: "Permanent access to purchased reports",
    freeFeat4: "MCP + Claude integration",
    freeCTA: "Get started",
    proTitle: "Pro",
    proPrice: "$20",
    proUnit: "/ month",
    proBadge: "Most popular",
    proBlurb: "For navigators actively managing their visa, tax, or compliance work.",
    proFeat1: "Unlimited document extractions",
    proFeat2: "1 professional search included / month",
    proFeat3: "Additional searches at $15 each",
    proFeat4: "Cancel anytime in the billing portal",
    proCTA: "Start Pro",
    proCTAFromTrial: "Continue Pro",
    proCTASignedOut: "Sign in to subscribe",
    trialNote:
      "Already paid for a professional search? You're already on a 30-day Pro trial — no card required.",
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
    faq4Q: "Do trial users get the free professional search?",
    faq4A:
      "No — the included monthly search is a paid-Pro perk only. Trial users still pay $15 per search, but get unlimited extractions during the trial.",
    backHome: "← Back to home",
  },
  zh: {
    eyebrow: "套餐",
    title: "按需付费,无月租门槛",
    subtitle:
      "偶尔上传一份文件、做一次专业人士搜索 — 免费即可。当您的资料室真正进入活跃使用期,再升级到 Pro。",
    freeTitle: "免费版",
    freePrice: "$0",
    freeUnit: "/ 月",
    freeBlurb: "适合快速审阅一份文件或一次性专业人士搜索。",
    freeFeat1: "每月 10 次文档解析",
    freeFeat2: "专业人士搜索单次 $15",
    freeFeat3: "已购报告永久可访问",
    freeFeat4: "支持 MCP / Claude 集成",
    freeCTA: "开始使用",
    proTitle: "Pro",
    proPrice: "$20",
    proUnit: "/ 月",
    proBadge: "推荐",
    proBlurb: "适合正在主动处理签证、税务或合规事务的用户。",
    proFeat1: "无限次文档解析",
    proFeat2: "每月赠送 1 次专业人士搜索",
    proFeat3: "超出后每次 $15",
    proFeat4: "随时通过 Stripe 自助取消",
    proCTA: "开通 Pro",
    proCTAFromTrial: "继续 Pro 订阅",
    proCTASignedOut: "登录后订阅",
    trialNote:
      "购买过专业人士搜索? 您已自动获得 30 天 Pro 试用 — 无需信用卡。",
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
    faq4Q: "试用用户也能获赠专业人士搜索吗?",
    faq4A:
      "不能 — 每月赠送 1 次专业人士搜索仅限付费 Pro 用户。试用用户仍需按 $15 单次付费,但解析次数在试用期内不限。",
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
      "Each upload triggers OCR + structured extraction (a paid LLM call). Free resets on the 1st of next month — or upgrade to Pro for unlimited extractions and one free professional search per month.",
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
      "每次上传都会触发 OCR + 结构化抽取(付费 LLM 调用)。免费额度将于下月 1 日重置 — 或升级到 Pro,享受无限次解析及每月 1 次免费专业人士搜索。",
    paywallUpgrade: "升级到 Pro · $20/月",
    paywallDismiss: "稍后再说",
    paywallReset: (date: string) => `${date} 重置`,
    proSearchHint: "本期赠送 1 次免费搜索",
    proSearchUsed: "本期赠送已用完,后续每次 $15",
  },
};
