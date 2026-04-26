"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getSubscriptionState,
  openBillingPortal,
  type SubscriptionState,
} from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";
import { PRO_STRINGS, useLang } from "@/lib/i18n";
import { trackSubscriptionEvent } from "@/lib/analytics";

/** Small pill that shows extraction usage + an actionable CTA.
 *
 *  Renders nothing until we have state (avoids a flash of "0/10" while
 *  the API loads). Renders nothing for signed-out users — they see the
 *  free experience until they create an account.
 */
export default function ProQuotaBadge({
  className = "",
  refreshKey,
}: {
  className?: string;
  /** Bump to re-fetch state after an action completes (e.g. after upload). */
  refreshKey?: number | string;
}) {
  const router = useRouter();
  const { lang } = useLang();
  const t = PRO_STRINGS[lang];
  const [state, setState] = useState<SubscriptionState | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) return;
    getSubscriptionState()
      .then((s) => setState(s))
      .catch(() => undefined);
  }, [refreshKey]);

  if (!state) return null;

  const isPro = state.is_pro;
  const isTrial = state.tier === "pro_trial";
  const used = state.extraction_quota.used;
  const limit = state.extraction_quota.limit;

  const label = isPro
    ? isTrial
      ? (t.badgeTrial as string)
      : (t.badgePro as string)
    : (t.badgeFree as (used: number, limit: number) => string)(used, limit ?? 0);

  // Color codes the urgency: green (Pro), blue (plenty of free quota left),
  // amber (≥80% used), red (at limit).
  const tone = isPro
    ? "border-[#cfe8d5] bg-[#eaf6ec] text-[#2f7a45]"
    : limit !== null && used >= limit
      ? "border-[#ffd6d6] bg-[#fff4f4] text-[#a33a3a]"
      : limit !== null && used / limit >= 0.8
        ? "border-[#ffe3c9] bg-[#fff6ea] text-[#9c5a1c]"
        : "border-[#dbe5f2] bg-white/80 text-[#40536f]";

  async function handleManageClick() {
    setBusy(true);
    trackSubscriptionEvent("subscription_quota_badge_clicked", {
      tier: state?.tier,
      action: isPro ? "manage" : "upgrade",
      lang,
    });
    try {
      if (isPro && state?.subscription?.has_billing_portal) {
        const { url } = await openBillingPortal("/dashboard");
        window.location.href = url;
        return;
      }
      // Free user (or Pro without a customer record) → pricing page.
      router.push("/pricing");
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleManageClick}
      disabled={busy}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12px] font-semibold shadow-[0_8px_24px_rgba(42,64,102,0.06)] transition hover:opacity-90 disabled:cursor-wait disabled:opacity-60 ${tone} ${className}`}
      title={
        isPro
          ? (t.badgeManage as string)
          : (t.badgeUpgrade as string)
      }
    >
      <span>{label}</span>
      <span className="opacity-70">·</span>
      <span className="opacity-90">
        {isPro ? (t.badgeManage as string) : (t.badgeUpgrade as string)}
      </span>
    </button>
  );
}
