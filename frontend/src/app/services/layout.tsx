import type { Metadata } from "next";

import { OG_IMAGE, SITE_NAME, SITE_URL } from "@/lib/site";
import { JsonLdScript, SERVICES_SCHEMA } from "@/components/SchemaOrg";

const TITLE = "Services — tax filings, immigration document review, entity setup";
const DESC =
  "Browse Guardian services: free Form 8843, student tax (1040-NR) packages, FBAR aggregation check, H-1B document review, 83(b) election filings, OPT advisory, foreign-owned LLC tax compliance (Form 5472 + pro forma 1120). Most services run as a guided wizard with optional attorney or CPA support.";
const URL = `${SITE_URL}/services`;

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
    images: [{ url: OG_IMAGE, width: 1024, height: 1024, alt: "Guardian services" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESC,
    images: [OG_IMAGE],
  },
};

export default function ServicesLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <JsonLdScript data={SERVICES_SCHEMA} />
      {children}
    </>
  );
}
