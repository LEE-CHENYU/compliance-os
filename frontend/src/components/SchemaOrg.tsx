/**
 * JSON-LD structured data for the Guardian landing page.
 *
 * Emits Organization + WebSite + SoftwareApplication + FAQPage
 * schemas in a single <script type="application/ld+json">. Used by
 * Google SGE, Gemini, ChatGPT, Claude web search, and Perplexity
 * to cite pages with rich context.
 */

const SITE_URL = "https://guardiancompliance.app";

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
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html }}
    />
  );
}
