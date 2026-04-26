import type { Metadata } from "next";

export const dynamic = "force-dynamic";

// User-specific case pages — already gated by auth, but extra noindex
// signal in case auth ever leaks (e.g. via crawler with a stolen cookie).
export const metadata: Metadata = {
  title: "Case",
  robots: { index: false, follow: false, nocache: true },
};

export default function CaseLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
