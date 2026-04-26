import type { Metadata } from "next";

import { SITE_URL } from "@/lib/site";

// Auth pages are noindex — no SEO value, and indexed login pages
// can attract bots. Keep canonical pointed at /login so the dupes
// caused by ?next=… params consolidate.
export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to Guardian to access your dashboard.",
  alternates: { canonical: `${SITE_URL}/login` },
  robots: { index: false, follow: false },
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
