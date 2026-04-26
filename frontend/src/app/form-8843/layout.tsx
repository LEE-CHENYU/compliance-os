import type { Metadata } from "next";

import { OG_IMAGE, SITE_NAME, SITE_URL } from "@/lib/site";
import { FORM_8843_SCHEMA, JsonLdScript } from "@/components/SchemaOrg";

const TITLE = "Free Form 8843 generator for F-1 / J-1 / M-1 / Q visitors";
const DESC =
  "Generate IRS Form 8843 (Statement for Exempt Individuals) in 7 fields. Required every year for F-1, J-1, M-1, and Q nonresident students, scholars, teachers, and trainees — even with zero US income. Free PDF download with the mailing instructions and IRS Austin address.";
const URL = `${SITE_URL}/form-8843`;

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
    images: [{ url: OG_IMAGE, width: 1024, height: 1024, alt: "Guardian Form 8843 generator" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESC,
    images: [OG_IMAGE],
  },
};

export default function Form8843Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <JsonLdScript data={FORM_8843_SCHEMA} />
      {children}
    </>
  );
}
