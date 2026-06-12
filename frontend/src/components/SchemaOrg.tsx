/**
 * JSON-LD structured data for Guardian routes.
 *
 * Emits per-page schema (Organization + WebSite + SoftwareApplication
 * + FAQPage on landing; Product/Offer on /pricing; Service on
 * /find-lawyer; ItemList on /services; HowTo on /docs/install;
 * WebApplication + FAQ on /form-8843). Used by Google SGE, Gemini,
 * ChatGPT, Claude web search, and Perplexity to cite pages with
 * rich context.
 */

import { SITE_URL } from "@/lib/site";

const schema = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}#organization`,
      name: "Guardian",
      url: SITE_URL,
      email: "fretin13@gmail.com",
      description:
        "Guardian is a compliance copilot for nonresidents, STEM OPT and H-1B workers, international students, and foreign-owned US entities.",
      sameAs: ["https://github.com/LEE-CHENYU/compliance-os"],
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}#website`,
      url: SITE_URL,
      name: "Guardian",
      publisher: { "@id": `${SITE_URL}#organization` },
      inLanguage: "en-US",
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${SITE_URL}#app`,
      name: "Guardian",
      operatingSystem: "Web, macOS, Windows, Linux",
      applicationCategory: "BusinessApplication",
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      description:
        "Cross-check your immigration and tax documents. Generate Form 8843, 1040-NR, FBAR, Form 5472 filings. Organize case packages for immigration attorneys and CPAs. Integrates with Claude Code, Claude Desktop, Codex via 23 MCP tools.",
      featureList: [
        "Form 8843 generation with mailing kit",
        "H-1B petition package template (59 slots)",
        "CPA tax engagement template (27 slots) for Form 5472 + 1120 scope",
        "FBAR aggregation check",
        "I-983 STEM OPT training plan review",
        "Tokenized data-room share links for lawyers and CPAs",
        "MCP server with 23 tools for Claude Code / Desktop / Codex",
        "Chat integration via OpenClaw (WhatsApp, Telegram, Discord, Slack)",
        "Local document parsing (PDF, DOCX) with automatic classification",
        "RAG-indexed document search over your personal data room",
      ],
      url: SITE_URL,
      publisher: { "@id": `${SITE_URL}#organization` },
    },
    {
      "@type": "FAQPage",
      mainEntity: [
        {
          "@type": "Question",
          name: "What is Guardian?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Guardian is a compliance copilot that cross-checks immigration and tax documents (I-20, I-983, I-94, W-2, 1042-S, EADs, tax returns) to find mismatches, missing forms, and deadline risks before USCIS or the IRS does. It runs as a web app and as an MCP server inside Claude Code, Claude Desktop, or Codex.",
          },
        },
        {
          "@type": "Question",
          name: "Who is Guardian for?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "International graduate students on F-1, STEM OPT workers, H-1B beneficiaries at small companies, nonresident-alien entrepreneurs with US LLCs (Form 5472 scope), and the immigration attorneys / CPAs they work with.",
          },
        },
        {
          "@type": "Question",
          name: "How do I connect Guardian to Claude Code or Codex?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Paste \"Install Guardian MCP by following https://guardiancompliance.app/AGENTS.md\" to your Claude Code or Codex session. The agent will fetch the install instructions, run pip install, configure your client, and verify the connection. Alternatively, follow the manual 3-step guide at https://guardiancompliance.app/docs/install.",
          },
        },
        {
          "@type": "Question",
          name: "Does Guardian cost anything?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "The core product is free to start. Form 8843 generation is free. Document cross-checks are free. Premium services (attorney-supported filings, tax packages with a CPA) are available in the marketplace at https://guardiancompliance.app/services.",
          },
        },
        {
          "@type": "Question",
          name: "Is my data secure?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Your data is encrypted at rest on SOC 2 Type II infrastructure (Fly.io + Neon). Documents are used only for compliance checks on your behalf. Share links are scoped, revocable JWTs with configurable expiry. Local document parsing runs on your machine when connected via MCP, so sensitive data stays on your device.",
          },
        },
        {
          "@type": "Question",
          name: "What forms does Guardian help with?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Form 8843, Form 1040-NR, FBAR (FinCEN 114), Form 5472 + pro forma 1120, I-983 STEM OPT training plans, H-1B petition packages (full I-20 lineage, corporate formation, registration, employment history, business plans), and 83(b) elections.",
          },
        },
      ],
    },
  ],
};

export function LandingSchema() {
  // Next.js recommends this pattern for JSON-LD in the app router.
  // Safe here: `schema` is a hardcoded object literal, no user input.
  const __html = JSON.stringify(schema);
  return (
    <script
      type="application/ld+json"
      suppressHydrationWarning
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html }}
    />
  );
}

// ---------- Per-route schema data ----------
// Consumed by route-level layout.tsx files via plain
// <script type="application/ld+json">{JSON.stringify(...)}</script>.
// Centralising the data here keeps schema diffs reviewable and lets
// non-React tooling (sitemap, llms.txt builder) reuse the same constants.

const PRICING_URL = `${SITE_URL}/pricing`;
export const PRICING_SCHEMA = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Product",
      name: "Guardian Pro",
      description:
        "Unlimited document extraction, monthly professional searches, priority email support, and a personal compliance vault for nonresidents and US-based founders.",
      brand: { "@type": "Brand", name: "Guardian" },
      offers: [
        {
          "@type": "Offer",
          name: "Guardian Pro — monthly",
          price: "20",
          priceCurrency: "USD",
          url: PRICING_URL,
          availability: "https://schema.org/InStock",
        },
        {
          "@type": "Offer",
          name: "On-demand professional search",
          price: "15",
          priceCurrency: "USD",
          description: "Single-use professional search; 30 days of Guardian Pro included.",
          url: PRICING_URL,
          availability: "https://schema.org/InStock",
        },
        {
          "@type": "Offer",
          name: "Free tier",
          price: "0",
          priceCurrency: "USD",
          description: "Form 8843 generation, single document cross-check, share link.",
          url: PRICING_URL,
          availability: "https://schema.org/InStock",
        },
      ],
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
        { "@type": "ListItem", position: 2, name: "Pricing", item: PRICING_URL },
      ],
    },
  ],
} as const;

const FIND_LAWYER_URL = `${SITE_URL}/find-lawyer`;
export const FIND_LAWYER_SCHEMA = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Service",
      name: "Guardian professional matching",
      serviceType: "Attorney and CPA shortlisting",
      provider: { "@type": "Organization", name: "Guardian", url: SITE_URL },
      areaServed: "United States",
      audience: {
        "@type": "Audience",
        audienceType:
          "F-1, OPT, STEM OPT, H-1B, EB-5, family-based green card applicants and US-based foreign founders",
      },
      offers: {
        "@type": "Offer",
        price: "15",
        priceCurrency: "USD",
        description: "Single-use professional search; 30 days of Guardian Pro included.",
        url: FIND_LAWYER_URL,
      },
      hasOfferCatalog: {
        "@type": "OfferCatalog",
        name: "Practice areas covered",
        itemListElement: [
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "Immigration attorney" } },
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "EB-5 immigration attorney" } },
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "Tax attorney" } },
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "Corporate attorney" } },
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "CPA — nonresident tax" } },
        ],
      },
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
        { "@type": "ListItem", position: 2, name: "Find a professional", item: FIND_LAWYER_URL },
      ],
    },
  ],
} as const;

const SERVICES_URL = `${SITE_URL}/services`;
const SERVICES_LIST = [
  { name: "Form 8843 generator", url: `${SITE_URL}/services/form_8843_free`, desc: "Free Form 8843 PDF + mailing kit for F-1 / J-1 / M-1 / Q nonresidents." },
  { name: "Student tax (1040-NR) package", url: `${SITE_URL}/services/student_tax_1040nr`, desc: "Nonresident student tax return prep with treaty-rate review." },
  { name: "H-1B document review", url: `${SITE_URL}/services/h1b_doc_check`, desc: "Cross-check H-1B petition documents against the Klasko gold-standard package." },
  { name: "FBAR aggregation check", url: `${SITE_URL}/services/fbar_check`, desc: "Aggregate foreign financial accounts and check FBAR filing thresholds." },
  { name: "83(b) election filing", url: `${SITE_URL}/services/election_83b`, desc: "30-day 83(b) election kit for founders and early employees." },
  { name: "OPT execution + advisory", url: `${SITE_URL}/services/opt_execution`, desc: "Attorney-supported OPT and STEM OPT applications." },
];
export const SERVICES_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "ItemList",
  name: "Guardian services marketplace",
  url: SERVICES_URL,
  itemListElement: SERVICES_LIST.map((s, i) => ({
    "@type": "ListItem",
    position: i + 1,
    url: s.url,
    name: s.name,
    description: s.desc,
  })),
} as const;

const INSTALL_URL = `${SITE_URL}/docs/install`;
export const INSTALL_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "HowTo",
  name: "Install Guardian MCP",
  description:
    "3-step install for the Guardian MCP server in Claude Code, Claude Desktop, or Codex CLI.",
  totalTime: "PT3M",
  url: INSTALL_URL,
  step: [
    {
      "@type": "HowToStep",
      position: 1,
      name: "Install the MCP server",
      text: "Run pip install \"compliance-os[agent]\" to install the Guardian MCP server with Python 3.11+. Use the stdio path for local-only document access, or skip ahead for the hosted SSE option.",
    },
    {
      "@type": "HowToStep",
      position: 2,
      name: "Configure your client",
      text: "Add the Guardian MCP block to ~/.claude.json (Claude Code), claude_desktop_config.json (Claude Desktop), or ~/.codex/config.toml (Codex CLI). Paste your token from /connect.",
    },
    {
      "@type": "HowToStep",
      position: 3,
      name: "Verify the connection",
      text: "Restart your client. The Guardian server should appear in the MCP tools list with 23 tools (case_active_search, guardian_status, gmail_search, parse_document, generate_form_8843, etc.).",
    },
  ],
  tool: [
    { "@type": "HowToTool", name: "Claude Code" },
    { "@type": "HowToTool", name: "Claude Desktop" },
    { "@type": "HowToTool", name: "Codex CLI" },
  ],
} as const;

const FORM_8843_URL = `${SITE_URL}/form-8843`;
export const FORM_8843_SCHEMA = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebApplication",
      name: "Guardian Form 8843 generator",
      applicationCategory: "FinanceApplication",
      operatingSystem: "Web",
      description:
        "Generate IRS Form 8843 (Statement for Exempt Individuals) in 7 fields. Required every year for F-1, J-1, M-1, and Q nonresident students, scholars, teachers, and trainees — even with zero US income.",
      url: FORM_8843_URL,
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      featureList: [
        "Generates IRS Form 8843 PDF",
        "Mailing instructions to IRS Austin TX",
        "F-1, J-1, M-1, Q visa support",
        "Substantial Presence Test exemption attestation",
        "No account required",
      ],
    },
    {
      "@type": "FAQPage",
      mainEntity: [
        {
          "@type": "Question",
          name: "Who needs to file Form 8843?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "F-1, J-1, M-1, and Q nonresident students, scholars, teachers, and trainees must file Form 8843 every year they were physically present in the US under one of these visa categories — even if they had no US income and don't have to file Form 1040-NR.",
          },
        },
        {
          "@type": "Question",
          name: "Is Form 8843 free to file?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Yes. Form 8843 is filed by mailing a paper PDF to the IRS in Austin, TX. There is no IRS filing fee. Guardian generates the PDF for free with no account required.",
          },
        },
        {
          "@type": "Question",
          name: "When is Form 8843 due?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "If you also file Form 1040-NR, attach Form 8843 and mail by April 15. If you only file Form 8843 (no other return), the deadline is June 15.",
          },
        },
      ],
    },
  ],
} as const;

/**
 * Per-route JSON-LD <script>. Uses the same dangerouslySetInnerHTML
 * pattern as LandingSchema so Google's parser sees raw JSON (HTML5
 * <script> children are raw-text — entity decoding does NOT happen).
 *
 * Safe: only static, hardcoded schema objects are passed in; never
 * user input.
 */
export function JsonLdScript({ data }: { data: Record<string, unknown> | Array<Record<string, unknown>> }) {
  const __html = JSON.stringify(data);
  return (
    <script
      type="application/ld+json"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html }}
    />
  );
}
