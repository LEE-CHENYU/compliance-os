import type { Metadata } from "next";

export const dynamic = "force-dynamic";

// Tokenized share-page URLs are scoped to a single recipient (lawyer
// or CPA). Indexing them would leak case data — strong noindex.
export const metadata: Metadata = {
  title: "Shared case",
  robots: { index: false, follow: false, nocache: true, noarchive: true },
};

export default function ShareLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
