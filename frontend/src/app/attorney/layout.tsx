import type { Metadata } from "next";

// Attorney portal is auth-gated. Noindex so partner URLs don't leak.
export const metadata: Metadata = {
  title: "Attorney portal",
  robots: { index: false, follow: false, nocache: true },
};

export default function AttorneyLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
