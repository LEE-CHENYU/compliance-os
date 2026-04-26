import type { Metadata } from "next";

import { OG_IMAGE, SITE_NAME, SITE_URL } from "@/lib/site";

const TITLE = "Connect Guardian to Claude, Codex, and OpenClaw";
const DESC =
  "Generate a scoped API token (gdn_oc_…) for Guardian's MCP server or OpenClaw chat integration. Tokens are read-only by default and revocable any time from the same page.";
const URL = `${SITE_URL}/connect`;

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: URL },
  openGraph: {
    type: "website",
    url: URL,
    siteName: SITE_NAME,
    title: TITLE,
    description: DESC,
    images: [{ url: OG_IMAGE, width: 1024, height: 1024, alt: "Guardian connect" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESC,
    images: [OG_IMAGE],
  },
};

export default function ConnectLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
