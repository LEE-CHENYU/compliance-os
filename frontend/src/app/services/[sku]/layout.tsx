import type { Metadata } from "next";

import { OG_IMAGE, SITE_NAME, SITE_URL } from "@/lib/site";

export const dynamic = "force-dynamic";

// Per-SKU metadata. Hardcoded rather than fetched at build time so
// metadata renders even if the marketplace API is briefly down.
// Keep in sync with the active marketplace SKUs in
// compliance_os/web/services/marketplace_service.py.
const SKUS: Record<string, { title: string; description: string }> = {
  form_8843_free: {
    title: "Form 8843 generator (free) — F-1 / J-1 / M-1 / Q",
    description:
      "Generate IRS Form 8843 in 7 fields. Free PDF download with mailing instructions to IRS Austin. Required annually for nonresident students, scholars, teachers, and trainees.",
  },
  student_tax_1040nr: {
    title: "Student tax (1040-NR) package — nonresident return prep",
    description:
      "Nonresident student tax return prep. We pull W-2, 1042-S, 1098-T, and treaty rates, generate Form 1040-NR with Schedule OI, and walk you through filing.",
  },
  h1b_doc_check: {
    title: "H-1B document review — petition cross-check",
    description:
      "Cross-check your H-1B petition against the Klasko gold-standard package: I-129, LCA, beneficiary identity, full I-20 lineage, employment history, business plan, and corporate registration.",
  },
  fbar_check: {
    title: "FBAR aggregation check — FinCEN 114 filing readiness",
    description:
      "Aggregate your foreign financial accounts and check FBAR (FinCEN 114) filing thresholds. Required for US persons with $10K+ across foreign accounts at any point during the year.",
  },
  election_83b: {
    title: "83(b) election filing — 30-day founder kit",
    description:
      "Strict 30-day window. Generate the 83(b) election letter, certified-mail labels, and IRS receipt tracking for founders and early employees with restricted stock.",
  },
  opt_execution: {
    title: "OPT application — attorney-supported filing",
    description:
      "Full attorney-supported OPT and STEM OPT application package. I-983 review, I-765 preparation, employer documentation, and timing checks against your I-20 program end date.",
  },
  opt_advisory: {
    title: "OPT advisory consultation",
    description:
      "1:1 attorney advisory call for OPT timing strategy, employer changes, travel during OPT, and STEM OPT extension planning.",
  },
};

export function generateMetadata({ params }: { params: { sku: string } }): Metadata {
  const sku = params.sku;
  const info = SKUS[sku];
  const url = `${SITE_URL}/services/${sku}`;
  const title = info?.title ?? "Service";
  const description =
    info?.description ??
    "Guardian service detail. Tax filings, immigration document review, and entity setup for nonresidents and US-based founders.";
  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      url,
      siteName: SITE_NAME,
      title,
      description,
      images: [{ url: OG_IMAGE, width: 1024, height: 1024, alt: title }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [OG_IMAGE],
    },
    // Unknown SKUs (e.g. legacy or experimental) shouldn't be indexed
    // until they have curated copy.
    robots: info ? undefined : { index: false, follow: false },
  };
}

export default function ServiceDetailLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
