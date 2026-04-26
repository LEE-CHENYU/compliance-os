"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import {
  startProSubscriptionCheckout,
  type ExtractionQuotaExceededDetail,
} from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";
import { PRO_STRINGS, useLang } from "@/lib/i18n";
import { trackSubscriptionEvent } from "@/lib/analytics";

/** Shown when an upload returns 402 (extraction quota exhausted).
 *  Surfaces the limit + reset date and offers a one-click upgrade.
 */
export default function ExtractionPaywallModal({
  open,
  detail,
  onClose,
}: {
  open: boolean;
  detail: ExtractionQuotaExceededDetail | null;
  onClose: () => void;
}) {
  const router = useRouter();
  const { lang } = useLang();
  const t = PRO_STRINGS[lang];
  const isZh = lang === "zh";

  useEffect(() => {
    if (!open) return;
    trackSubscriptionEvent("subscription_paywall_modal_viewed", {
      tier: detail?.tier ?? "unknown",
      used: detail?.used,
      limit: detail?.limit,
      lang,
    });
  }, [open, detail, lang]);

  if (!open) return null;

  const resetLabel = detail?.reset_at
    ? new Date(detail.reset_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  function handleDismiss() {
    trackSubscriptionEvent("subscription_paywall_modal_dismissed", { lang });
    onClose();
  }

  async function handleUpgrade() {
    trackSubscriptionEvent("subscription_paywall_upgrade_clicked", { lang });
    if (!isLoggedIn()) {
      router.push("/login?next=/pricing");
      return;
    }
    try {
      const { url } = await startProSubscriptionCheckout({
        successPath: "/dashboard?subscribed=1",
        cancelPath: "/dashboard",
      });
      window.location.href = url;
    } catch {
      // Fall back to /pricing — checkout creation can fail e.g. if the
      // user already has an active sub (409). The pricing page handles
      // both states correctly.
      router.push("/pricing");
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-[#0d1424]/30 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-[28px] border border-white/70 bg-white/90 p-7 shadow-[0_30px_80px_rgba(56,85,131,0.18)] backdrop-blur-xl">
        <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#9c5a1c]">
          {isZh ? "需要升级" : "Upgrade required"}
        </div>
        <h3 className="mt-3 font-[Charter,Georgia,serif] text-[24px] font-bold leading-[1.2] text-[#0d1424]">
          {t.paywallTitle as string}
        </h3>
        <p className="mt-3 text-[13.5px] leading-6 text-[#556480]">
          {t.paywallBody as string}
        </p>
        {resetLabel && (
          <p className="mt-3 text-[12px] font-medium text-[#7b8ba5]">
            {(t.paywallReset as (d: string) => string)(resetLabel)}
          </p>
        )}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleUpgrade}
            className="inline-flex items-center gap-2 rounded-full bg-[#5b8dee] px-5 py-2.5 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de]"
          >
            {t.paywallUpgrade as string}
          </button>
          <button
            type="button"
            onClick={handleDismiss}
            className="rounded-full border border-[#dbe5f2] bg-white/90 px-4 py-2 text-[13px] font-semibold text-[#52627d] transition hover:text-[#1a2036]"
          >
            {t.paywallDismiss as string}
          </button>
        </div>
      </div>
    </div>
  );
}
