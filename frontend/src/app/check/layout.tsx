import type { Metadata } from "next";

// Check flow is interactive (uploads + Q&A) — not a content surface.
// Keep noindex even though robots.txt also disallows /check.
export const metadata: Metadata = {
  title: "Find my risks",
  robots: { index: false, follow: false, nocache: true },
};

export default function CheckLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
