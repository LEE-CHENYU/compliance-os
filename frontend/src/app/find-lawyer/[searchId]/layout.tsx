import type { Metadata } from "next";

export const dynamic = "force-dynamic";

// Search-result pages are user-specific, contain firm shortlists tied
// to a paid request, and have nothing to gain from indexing. Strong
// noindex so any leaked URL doesn't get crawled.
export const metadata: Metadata = {
  title: "Lawyer search",
  robots: { index: false, follow: false, nocache: true },
};

export default function SearchLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
