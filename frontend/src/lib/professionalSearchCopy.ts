import type { Lang } from "@/lib/i18n";

export type ProfessionalSearchVocabulary = {
  isAttorney: boolean;
  orgSingular: string;
  orgPlural: string;
  unknownOrg: string;
  leadLabel: string;
  alternateLabel: string;
  alternateHeader: string;
  reportDossierCopy: string;
  hiddenPreviewCopy: (hiddenCount: number) => string;
  resultCount: (count: number) => string;
  trackingCount: (count: number) => string;
  trackingPrompt: string;
  credentialCaveat: string;
  enrichmentTitle: string;
  enrichmentBody: string;
  enrichmentFailedBody: string;
  paidProgress: (enriched: number, total: number) => string;
  paidComplete: (enriched: number) => string;
  paidFailed: string;
  benefitDocs: string;
  benefitComms: string;
  proTrialBody: string;
  guardianCtaEyebrow: string;
  guardianCtaTitle: string;
  guardianCtaBody: string;
  guardianCtaSubject: string;
};

function plural(count: number, singular: string, pluralForm: string) {
  return count === 1 ? singular : pluralForm;
}

function verticalKind(vertical: string | null | undefined) {
  const normalized = (vertical ?? "").toLowerCase();
  if (
    normalized.includes("attorney") ||
    normalized.includes("lawyer") ||
    normalized.startsWith("immigration") ||
    normalized.includes("eb5")
  ) {
    return "attorney";
  }
  if (normalized === "cpa" || normalized.includes("accounting") || normalized.includes("tax_cpa")) return "cpa";
  if (normalized.includes("bank")) return "bank";
  if (normalized === "caa" || normalized.includes("acceptance_agent") || normalized.includes("itin")) return "caa";
  return "provider";
}

export function professionalSearchVocabulary(
  vertical: string | null | undefined,
  lang: Lang,
): ProfessionalSearchVocabulary {
  const kind = verticalKind(vertical);
  const isZh = lang === "zh";
  const isAttorney = kind === "attorney";

  if (isZh) {
    const base = {
      isAttorney,
      alternateLabel: "备选联系人",
      resultCount: (count: number) => `${count} 个结果`,
      trackingCount: (count: number) => `${count} 个结果已加入案件`,
      trackingPrompt: "将结果加入案件，方便后续跟进",
      paidFailed: "深度核实失败 — 可在面板的账户页面联系我们重新触发。",
      benefitComms: "将邮件、咨询笔记、合同等集中管理 — 与合规时间线一起呈现。",
      proTrialBody: "包含每月 1 次专业搜索 + 无限文件提取。我们会在试用结束时自动续费您刚才使用的卡，可随时取消。",
    };
    if (kind === "attorney") {
      return {
        ...base,
        orgSingular: "律所",
        orgPlural: "律所",
        unknownOrg: "未知律所",
        leadLabel: "主办律师",
        alternateHeader: "同所更匹配的律师",
        reportDossierCopy: "PDF + 网页版报告，包含完整律所简介、可验证资质与原始资料链接",
        hiddenPreviewCopy: (hiddenCount) => `还有 ${hiddenCount} 家律所、完整简介与联系方式`,
        credentialCaveat: "上方仅为律所层面的资质，指定律师本人的个人评级须在解锁后核实。",
        enrichmentTitle: "正在核实律师个人资质",
        enrichmentBody: "我们正在为每家律所核实指定律师的个人 Chambers / Legal500 等级、备选合伙人、来源链接 — 通常 2-3 分钟。完成后此处会自动更新。",
        enrichmentFailedBody: "我们无法为本次搜索完成深度核实。原始律所列表已保留 — 您可在面板的账户页面联系我们重新触发。",
        paidProgress: (enriched, total) => `正在核实律师个人资质 — ${enriched}/${total} 家完成`,
        paidComplete: (enriched) => `✓ 已为 ${enriched} 家律所完成深度核实`,
        benefitDocs: "上传并整理律所所需的文件 — 护照扫描件、I-797、资金来源材料、历次申请记录。Guardian 数据室让所有材料随时备查。",
        guardianCtaEyebrow: "或者由 Guardian 律师为您处理",
        guardianCtaTitle: "想让我们的律师亲自跟进?",
        guardianCtaBody: "如果上面的律所对比不是您想要的，我们的内部律师可以直接接管整个案件 — 文件准备、提交、与 USCIS 沟通全程负责。请告诉我们您的情况，我们会回复定价方案。",
        guardianCtaSubject: "Guardian attorney engagement inquiry",
      };
    }
    if (kind === "cpa") {
      return {
        ...base,
        orgSingular: "CPA/会计师事务所",
        orgPlural: "CPA/会计师事务所",
        unknownOrg: "未知 CPA/会计师事务所",
        leadLabel: "主办 CPA / 联系人",
        alternateHeader: "同机构更匹配的联系人",
        reportDossierCopy: "PDF + 网页版报告，包含完整 CPA/会计师事务所简介、可验证资质与原始资料链接",
        hiddenPreviewCopy: (hiddenCount) => `还有 ${hiddenCount} 个 CPA 搜索结果、完整简介与联系方式`,
        credentialCaveat: "上方仅为机构层面的资质；解锁后会在可用时补充个人联系人核实。",
        enrichmentTitle: "正在核实个人联系人资质",
        enrichmentBody: "我们正在核实主办联系人资质、同机构更匹配的联系人与来源链接 — 通常 2-3 分钟。完成后此处会自动更新。",
        enrichmentFailedBody: "我们无法为本次搜索完成深度核实。原始 CPA/会计师事务所列表已保留 — 您可在面板的账户页面联系我们重新触发。",
        paidProgress: (enriched, total) => `正在核实联系人资质 — ${enriched}/${total} 个结果完成`,
        paidComplete: (enriched) => `✓ 已为 ${enriched} 个结果完成深度核实`,
        benefitDocs: "上传并整理服务方可能需要的文件 — 报税表、账簿、FBAR/FATCA 材料、实体文件等。Guardian 数据室让所有材料随时备查。",
        guardianCtaEyebrow: "需要 Guardian 协助跟进?",
        guardianCtaTitle: "想让我们协助整理下一步?",
        guardianCtaBody: "如果上面的 CPA/会计师事务所对比不是您想要的，我们可以帮您整理材料、明确问题清单，并协助您推进下一步。",
        guardianCtaSubject: "Guardian CPA search follow-up",
      };
    }
    if (kind === "bank") {
      return {
        ...base,
        orgSingular: "银行/开户服务方",
        orgPlural: "银行/开户服务方",
        unknownOrg: "未知银行/开户服务方",
        leadLabel: "主办银行联系人",
        alternateHeader: "同机构更匹配的联系人",
        reportDossierCopy: "PDF + 网页版报告，包含完整银行/开户服务方简介、可验证资料与原始链接",
        hiddenPreviewCopy: (hiddenCount) => `还有 ${hiddenCount} 个开户服务结果、完整简介与联系方式`,
        credentialCaveat: "上方仅为机构层面的资料；解锁后会在可用时补充个人联系人核实。",
        enrichmentTitle: "正在核实个人联系人资料",
        enrichmentBody: "我们正在核实主办联系人、同机构更匹配的联系人与来源链接 — 通常 2-3 分钟。完成后此处会自动更新。",
        enrichmentFailedBody: "我们无法为本次搜索完成深度核实。原始服务方列表已保留 — 您可在面板的账户页面联系我们重新触发。",
        paidProgress: (enriched, total) => `正在核实联系人资料 — ${enriched}/${total} 个结果完成`,
        paidComplete: (enriched) => `✓ 已为 ${enriched} 个结果完成深度核实`,
        benefitDocs: "上传并整理开户服务方可能需要的文件 — 护照、地址证明、实体文件、资金来源材料等。Guardian 数据室让所有材料随时备查。",
        guardianCtaEyebrow: "需要 Guardian 协助跟进?",
        guardianCtaTitle: "想让我们协助整理下一步?",
        guardianCtaBody: "如果上面的开户服务方对比不是您想要的，我们可以帮您整理材料、明确问题清单，并协助您推进下一步。",
        guardianCtaSubject: "Guardian banking search follow-up",
      };
    }
    return {
      ...base,
      orgSingular: "服务方",
      orgPlural: "服务方",
      unknownOrg: "未知服务方",
      leadLabel: "主办联系人",
      alternateHeader: "更匹配的联系人",
      reportDossierCopy: "PDF + 网页版报告，包含完整服务方简介、可验证资料与原始链接",
      hiddenPreviewCopy: (hiddenCount) => `还有 ${hiddenCount} 个结果、完整简介与联系方式`,
      credentialCaveat: "上方仅为机构层面的资料；解锁后会在可用时补充个人联系人核实。",
      enrichmentTitle: "正在核实个人联系人资料",
      enrichmentBody: "我们正在核实主办联系人、备选联系人与来源链接 — 通常 2-3 分钟。完成后此处会自动更新。",
      enrichmentFailedBody: "我们无法为本次搜索完成深度核实。原始服务方列表已保留 — 您可在面板的账户页面联系我们重新触发。",
      paidProgress: (enriched, total) => `正在核实联系人资料 — ${enriched}/${total} 个结果完成`,
      paidComplete: (enriched) => `✓ 已为 ${enriched} 个结果完成深度核实`,
      benefitDocs: "上传并整理服务方可能需要的文件。Guardian 数据室让所有材料随时备查。",
      guardianCtaEyebrow: "需要 Guardian 协助跟进?",
      guardianCtaTitle: "想让我们协助整理下一步?",
      guardianCtaBody: "如果上面的服务方对比不是您想要的，我们可以帮您整理材料、明确问题清单，并协助您推进下一步。",
      guardianCtaSubject: "Guardian professional search follow-up",
    };
  }

  const base = {
    isAttorney,
    alternateLabel: "Alternate contact",
    resultCount: (count: number) => `${count} ${plural(count, "result", "results")}`,
    paidFailed: "Individual verification failed — contact support from the dashboard to re-trigger it.",
    benefitComms: "Keep emails, consultation notes, and contracts in one place — alongside your timeline of compliance deadlines.",
    proTrialBody: "Includes 1 professional search per month + unlimited document extractions. Auto-renews to the card you just used at trial end — cancel anytime in the billing portal.",
  };

  if (kind === "attorney") {
    return {
      ...base,
      orgSingular: "firm",
      orgPlural: "firms",
      unknownOrg: "Unknown firm",
      leadLabel: "Lead attorney",
      alternateLabel: "Alternate attorney",
      alternateHeader: "Better-fit attorneys at this firm",
      reportDossierCopy: "PDF + HTML report — full firm dossiers, credentials, and verification sources",
      hiddenPreviewCopy: (hiddenCount) => `${hiddenCount} more ${plural(hiddenCount, "firm", "firms")}, full dossiers, credentials, contact info`,
      resultCount: (count) => `${count} ${plural(count, "firm", "firms")}`,
      trackingCount: (count) => `${count} ${plural(count, "firm", "firms")} tracked for this case`,
      trackingPrompt: "Track firms to your case to organize outreach",
      credentialCaveat: "Credentials above are firm-level. The named lead attorney's individual band is verified after unlock.",
      enrichmentTitle: "Verifying individual attorney credentials",
      enrichmentBody: "Per-firm: confirming the named lead attorney's individual Chambers / Legal500 band, alternate same-firm partners, and source URL liveness. Usually 2-3 min — refreshes here automatically.",
      enrichmentFailedBody: "We couldn't complete per-firm verification. The base firm list is preserved — contact us from the dashboard to re-trigger it.",
      paidProgress: (enriched, total) => `Verifying individual attorney credentials — ${enriched}/${total} ${plural(total, "firm", "firms")} complete`,
      paidComplete: (enriched) => `✓ Per-firm verification complete (${enriched} ${plural(enriched, "firm", "firms")})`,
      benefitDocs: "Upload and organize the files this firm will ask for — passport scans, I-797s, source-of-funds paperwork, prior filings. Guardian's data room keeps them ready.",
      guardianCtaEyebrow: "Or have a Guardian attorney handle this",
      guardianCtaTitle: "Want hands-on Guardian counsel?",
      guardianCtaBody: "If you'd rather skip the shortlist comparison, a Guardian-staffed attorney can take the case end-to-end — drafting, filing, USCIS correspondence. Tell us about your situation and we'll come back with pricing.",
      guardianCtaSubject: "Guardian attorney engagement inquiry",
    };
  }

  if (kind === "cpa") {
    return {
      ...base,
      orgSingular: "CPA practice",
      orgPlural: "CPA practices",
      unknownOrg: "Unknown CPA practice",
      leadLabel: "Lead CPA/contact",
      alternateHeader: "Better-fit contacts at this practice",
      reportDossierCopy: "PDF + HTML report — full CPA practice dossiers, credentials, and verification sources",
      hiddenPreviewCopy: (hiddenCount) => `${hiddenCount} more ${plural(hiddenCount, "CPA practice", "CPA practices")}, full dossiers, credentials, contact info`,
      resultCount: (count) => `${count} ${plural(count, "CPA practice", "CPA practices")}`,
      trackingCount: (count) => `${count} ${plural(count, "CPA practice", "CPA practices")} tracked for this case`,
      trackingPrompt: "Track CPA practices to your case to organize outreach",
      credentialCaveat: "Credentials above are practice-level. Individual contact verification is included after unlock when available.",
      enrichmentTitle: "Verifying individual contact credentials",
      enrichmentBody: "Confirming named lead contact credentials, better-fit same-practice contacts, and source URL liveness. Usually 2-3 min — refreshes here automatically.",
      enrichmentFailedBody: "We couldn't complete individual verification. The base CPA practice list is preserved — contact us from the dashboard to re-trigger it.",
      paidProgress: (enriched, total) => `Verifying individual contact credentials — ${enriched}/${total} ${plural(total, "practice", "practices")} complete`,
      paidComplete: (enriched) => `✓ Individual verification complete (${enriched} ${plural(enriched, "practice", "practices")})`,
      benefitDocs: "Upload and organize the files this practice may ask for — tax returns, books, FBAR/FATCA material, entity records, and prior filings. Guardian's data room keeps them ready.",
      guardianCtaEyebrow: "Need Guardian help with next steps?",
      guardianCtaTitle: "Want help turning this shortlist into action?",
      guardianCtaBody: "If you'd rather skip the shortlist comparison, Guardian can help organize the file, clarify the questions to ask, and move you toward the right CPA engagement.",
      guardianCtaSubject: "Guardian CPA search follow-up",
    };
  }

  if (kind === "bank") {
    return {
      ...base,
      orgSingular: "banking provider",
      orgPlural: "banking providers",
      unknownOrg: "Unknown banking provider",
      leadLabel: "Lead banker/contact",
      alternateHeader: "Better-fit contacts at this provider",
      reportDossierCopy: "PDF + HTML report — full banking provider dossiers, credentials, and verification sources",
      hiddenPreviewCopy: (hiddenCount) => `${hiddenCount} more ${plural(hiddenCount, "banking provider", "banking providers")}, full dossiers, credentials, contact info`,
      resultCount: (count) => `${count} ${plural(count, "banking provider", "banking providers")}`,
      trackingCount: (count) => `${count} ${plural(count, "banking provider", "banking providers")} tracked for this case`,
      trackingPrompt: "Track banking providers to your case to organize outreach",
      credentialCaveat: "Credentials above are provider-level. Individual contact verification is included after unlock when available.",
      enrichmentTitle: "Verifying individual contact details",
      enrichmentBody: "Confirming named lead contact details, better-fit same-provider contacts, and source URL liveness. Usually 2-3 min — refreshes here automatically.",
      enrichmentFailedBody: "We couldn't complete individual verification. The base provider list is preserved — contact us from the dashboard to re-trigger it.",
      paidProgress: (enriched, total) => `Verifying individual contacts — ${enriched}/${total} ${plural(total, "provider", "providers")} complete`,
      paidComplete: (enriched) => `✓ Individual verification complete (${enriched} ${plural(enriched, "provider", "providers")})`,
      benefitDocs: "Upload and organize the files this provider may ask for — passports, proof of address, entity documents, and source-of-funds material. Guardian's data room keeps them ready.",
      guardianCtaEyebrow: "Need Guardian help with next steps?",
      guardianCtaTitle: "Want help turning this shortlist into action?",
      guardianCtaBody: "If you'd rather skip the shortlist comparison, Guardian can help organize the file, clarify the questions to ask, and move you toward the right provider.",
      guardianCtaSubject: "Guardian banking search follow-up",
    };
  }

  return {
    ...base,
    orgSingular: "provider",
    orgPlural: "providers",
    unknownOrg: "Unknown provider",
    leadLabel: "Lead contact",
    alternateHeader: "Better-fit contacts at this provider",
    reportDossierCopy: "PDF + HTML report — full provider dossiers, credentials, and verification sources",
    hiddenPreviewCopy: (hiddenCount) => `${hiddenCount} more ${plural(hiddenCount, "provider", "providers")}, full dossiers, credentials, contact info`,
    resultCount: (count) => `${count} ${plural(count, "provider", "providers")}`,
    trackingCount: (count) => `${count} ${plural(count, "provider", "providers")} tracked for this case`,
    trackingPrompt: "Track providers to your case to organize outreach",
    credentialCaveat: "Credentials above are provider-level. Individual contact verification is included after unlock when available.",
    enrichmentTitle: "Verifying individual contact details",
    enrichmentBody: "Confirming named lead contact details, better-fit contacts, and source URL liveness. Usually 2-3 min — refreshes here automatically.",
    enrichmentFailedBody: "We couldn't complete individual verification. The base provider list is preserved — contact us from the dashboard to re-trigger it.",
    paidProgress: (enriched, total) => `Verifying individual contacts — ${enriched}/${total} ${plural(total, "provider", "providers")} complete`,
    paidComplete: (enriched) => `✓ Individual verification complete (${enriched} ${plural(enriched, "provider", "providers")})`,
    benefitDocs: "Upload and organize the files this provider may ask for. Guardian's data room keeps them ready.",
    guardianCtaEyebrow: "Need Guardian help with next steps?",
    guardianCtaTitle: "Want help turning this shortlist into action?",
    guardianCtaBody: "If you'd rather skip the shortlist comparison, Guardian can help organize the file, clarify the questions to ask, and move you toward the right engagement.",
    guardianCtaSubject: "Guardian professional search follow-up",
  };
}
