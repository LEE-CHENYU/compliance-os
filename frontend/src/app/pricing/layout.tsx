import type { Metadata } from "next";

import { OG_IMAGE, SITE_NAME, SITE_URL } from "@/lib/site";
import { JsonLdScript, PRICING_SCHEMA } from "@/components/SchemaOrg";

const TITLE = "Pricing — Free, Pro $20/mo, $15 per professional search";
const DESC =
  "Free Form 8843 generation and document cross-checks. Guardian Pro at $20/mo unlocks unlimited document extraction, monthly professional searches, and priority email support. Pay $15 per one-off professional search and get 30 days of Pro free.";
const URL = `${SITE_URL}/pricing`;

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
    images: [{ url: OG_IMAGE, width: 1024, height: 1024, alt: "Guardian" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESC,
    images: [OG_IMAGE],
  },
};

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <JsonLdScript data={PRICING_SCHEMA} />
      {children}
    </>
  );
}
