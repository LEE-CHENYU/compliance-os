"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  getSubscriptionState,
  openBillingPortal,
  startProSubscriptionCheckout,
  type SubscriptionState,
} from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";
import { PRICING_STRINGS, useLang } from "@/lib/i18n";
import LangToggle from "@/components/LangToggle";
import { trackSubscriptionEvent } from "@/lib/analytics";

export default function PricingPageWrapper() {
  return (
    <Suspense fallback={null}>
      <PricingPage />
    </Suspense>
  );
}

function PricingPage() {
  const router = useRouter();
  const search = useSearchParams();
  const { lang, setLang } = useLang();
  const t = PRICING_STRINGS[lang];

  const [state, setState] = useState<SubscriptionState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isZh = lang === "zh";
  const loggedIn = isLoggedIn();
  const canceledFlag = search?.get("canceled") === "1";

  // Pull entitlement so the CTA reflects state ("Continue Pro" vs "Start Pro").
  // No-op when signed out (returns null silently).
  useEffect(() => {
    if (!loggedIn) return;
    getSubscriptionState()
      .then((s) => setState(s))
      .catch(() => undefined);
  }, [loggedIn]);

  // Mixpanel: emit once per page mount with the user's current tier so
  // we can build a Free → Pro funnel by entry-tier.
  useEffect(() => {
    trackSubscriptionEvent("subscription_pricing_viewed", {
      tier: state?.tier ?? (loggedIn ? "unknown" : "anonymous"),
      canceled_flag: canceledFlag,
      lang,
    });
    // Intentionally only track on first mount; tier may load slightly
    // after but the initial "anonymous"/"unknown" event is the funnel
    // entry signal we care about.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleProCTA() {
    if (!loggedIn) {
      // Bounce through the auth modal — return to /pricing after.
      router.push("/login?next=/pricing");
      return;
    }
    setBusy(true);
    setError(null);
    trackSubscriptionEvent("subscription_pro_checkout_clicked", {
      tier: state?.tier ?? "unknown",
      lang,
    });
    try {
      // If they already have a Pro/Trial sub, send them to the billing
      // portal instead. /checkout would 409 otherwise.
      if (state?.is_pro) {
        const { url } = await openBillingPortal("/dashboard");
        window.location.href = url;
        return;
      }
      const { url } = await startProSubscriptionCheckout({
        successPath: "/dashboard?subscribed=1",
        cancelPath: "/pricing?canceled=1",
      });
      window.location.href = url;
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      trackSubscriptionEvent("subscription_pro_checkout_failed", { message, lang });
      setError(message);
      setBusy(false);
    }
  }

  const proCTALabel = busy
    ? isZh
      ? "正在跳转…"
      : "Redirecting…"
    : !loggedIn
      ? (t.proCTASignedOut as string)
      : state?.is_pro
        ? (t.proCTAFromTrial as string)
        : (t.proCTA as string);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(91,141,238,0.18),_transparent_32%),linear-gradient(180deg,#edf3f9_0%,#e6eef6_42%,#f4f7fb_100%)] px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => router.push("/")}
            className="rounded-full border border-white/80 bg-white/75 px-4 py-2 text-sm font-medium text-[#52627d] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur transition hover:text-[#1a2036]"
          >
            {t.backHome as string}
          </button>
          <LangToggle lang={lang} onChange={setLang} />
        </div>

        <header className="rounded-[32px] border border-white/70 bg-white/72 p-8 text-center shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
          <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
            {t.eyebrow as string}
          </div>
          <h1 className="mt-3 font-[Charter,Georgia,serif] text-[40px] font-bold leading-[1.1] tracking-tight text-[#0d1424]">
            {t.title as string}
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-[15px] leading-7 text-[#556480]">
            {t.subtitle as string}
          </p>
          {state?.is_pro && state?.tier === "pro_trial" && (
            <div className="mx-auto mt-5 inline-flex max-w-xl items-center gap-2 rounded-full border border-[#cfe1ff] bg-[#eaf2ff] px-4 py-2 text-[12.5px] font-medium text-[#2f5bae]">
              {t.trialNote as string}
            </div>
          )}
          {canceledFlag && (
            <div className="mx-auto mt-5 inline-flex max-w-xl items-center gap-2 rounded-full border border-[#ffe3c9] bg-[#fff6ea] px-4 py-2 text-[12.5px] font-medium text-[#9c5a1c]">
              {isZh
                ? "您已取消结账。如需重新开通,请点击下方按钮。"
                : "Checkout canceled. Subscribe whenever you're ready."}
            </div>
          )}
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Free tier */}
          <div className="rounded-[32px] border border-white/70 bg-white/72 p-7 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
            <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
              {t.freeTitle as string}
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-[44px] font-extrabold leading-none text-[#0d1424]">
                {t.freePrice as string}
              </span>
              <span className="text-[14px] font-medium text-[#7b8ba5]">
                {t.freeUnit as string}
              </span>
            </div>
            <p className="mt-3 text-[14px] leading-6 text-[#556480]">
              {t.freeBlurb as string}
            </p>
            <ul className="mt-5 space-y-2 text-[14px] text-[#40536f]">
              {[t.freeFeat1, t.freeFeat2, t.freeFeat3, t.freeFeat4].map((feat, i) => (
                <li key={i} className="flex items-start gap-2">
                  <Check />
                  <span>{feat as string}</span>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => router.push("/find-lawyer")}
              className="mt-7 w-full rounded-full border border-[#dbe5f2] bg-white/90 px-5 py-2.5 text-[14px] font-semibold text-[#40536f] shadow-[0_8px_24px_rgba(42,64,102,0.06)] transition hover:border-[#5b8dee] hover:text-[#1a2036]"
            >
              {t.freeCTA as string}
            </button>
          </div>

          {/* Pro tier */}
          <div className="relative rounded-[32px] border border-[#5b8dee]/30 bg-gradient-to-br from-white via-[#f5faff] to-[#eaf2ff] p-7 shadow-[0_28px_80px_rgba(91,141,238,0.18)] backdrop-blur">
            <div className="absolute -top-3 right-7 rounded-full bg-[#5b8dee] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-white shadow-[0_8px_24px_rgba(91,141,238,0.4)]">
              {t.proBadge as string}
            </div>
            <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#5b8dee]">
              {t.proTitle as string}
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-[44px] font-extrabold leading-none text-[#0d1424]">
                {t.proPrice as string}
              </span>
              <span className="text-[14px] font-medium text-[#7b8ba5]">
                {t.proUnit as string}
              </span>
            </div>
            <p className="mt-3 text-[14px] leading-6 text-[#556480]">
              {t.proBlurb as string}
            </p>
            <ul className="mt-5 space-y-2 text-[14px] text-[#40536f]">
              {[t.proFeat1, t.proFeat2, t.proFeat3, t.proFeat4].map((feat, i) => (
                <li key={i} className="flex items-start gap-2">
                  <Check primary />
                  <span>{feat as string}</span>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={handleProCTA}
              disabled={busy}
              className="mt-7 w-full rounded-full bg-[#5b8dee] px-5 py-2.5 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de] disabled:cursor-wait disabled:bg-[#a8bce8]"
            >
              {proCTALabel}
            </button>
            {error && (
              <div className="mt-3 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-3 py-2 text-[12px] text-[#a33a3a]">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* FAQ */}
        <section className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
          <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
            {t.faqTitle as string}
          </div>
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            {[
              { q: t.faq1Q, a: t.faq1A },
              { q: t.faq2Q, a: t.faq2A },
              { q: t.faq3Q, a: t.faq3A },
              { q: t.faq4Q, a: t.faq4A },
            ].map((item, i) => (
              <div key={i}>
                <div className="text-[15px] font-semibold text-[#0d1424]">
                  {item.q as string}
                </div>
                <p className="mt-1 text-[13.5px] leading-6 text-[#556480]">
                  {item.a as string}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function Check({ primary }: { primary?: boolean }) {
  return (
    <svg
      aria-hidden="true"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke={primary ? "#5b8dee" : "#5ab474"}
      strokeWidth="2.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="mt-0.5 shrink-0"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}
