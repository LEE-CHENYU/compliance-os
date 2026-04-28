import type { Metadata } from "next";

import { OG_IMAGE, SITE_NAME, SITE_URL } from "@/lib/site";
import { FIND_LAWYER_SCHEMA, JsonLdScript } from "@/components/SchemaOrg";

const TITLE = "Find a vetted professional — attorneys, CPAs, banks, and CAAs";
const DESC =
  "Tell Guardian your case and get a curated shortlist of attorneys, CPAs, banking providers, or CAAs with persona-fit reasoning. $15 per search; saved results tracked in your dashboard alongside your case documents and Gmail threads.";
const URL = `${SITE_URL}/find-lawyer`;

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
    images: [{ url: OG_IMAGE, width: 1024, height: 1024, alt: "Guardian — professional search" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESC,
    images: [OG_IMAGE],
  },
};

export default function FindLawyerLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <JsonLdScript data={FIND_LAWYER_SCHEMA} />
      {children}
    </>
  );
}
