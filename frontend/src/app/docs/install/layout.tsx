import type { Metadata } from "next";

import { OG_IMAGE, SITE_NAME, SITE_URL } from "@/lib/site";
import { INSTALL_SCHEMA, JsonLdScript } from "@/components/SchemaOrg";

const TITLE = "Install Guardian MCP — Claude Code, Claude Desktop, Codex";
const DESC =
  "3-step install for the Guardian MCP server. Stdio (pip install + local config) or hosted SSE (no install). Step-by-step config snippets and copy-paste tokens for Claude Code, Claude Desktop, and Codex CLI.";
const URL = `${SITE_URL}/docs/install`;

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: URL },
  openGraph: {
    type: "article",
    url: URL,
    siteName: SITE_NAME,
    title: TITLE,
    description: DESC,
    images: [{ url: OG_IMAGE, width: 1024, height: 1024, alt: "Guardian install guide" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESC,
    images: [OG_IMAGE],
  },
};

export default function InstallLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <JsonLdScript data={INSTALL_SCHEMA} />
      {children}
    </>
  );
}
