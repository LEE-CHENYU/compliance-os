"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import FilingChecklistCard from "@/components/form8843/FilingChecklistCard";
import { getUser, type AuthUser } from "@/lib/auth";
import { downloadForm8843Pdf, getForm8843Order, type Form8843OrderResponse } from "@/lib/marketplace";

const ONBOARDING_STORAGE_KEY = "guardian_form_8843_onboarding";
const ONBOARDING_PROMPT_DISMISS_PREFIX = "guardian_form_8843_prompt_dismissed";

function formatStatus(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  return value.replace(/_/g, " ");
}

function matchesEmail(user: AuthUser | null, email: string): boolean {
  if (!user || !email) {
    return false;
  }
  return user.email.trim().toLowerCase() === email.trim().toLowerCase();
}

export default function SuccessContent({ orderId }: { orderId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const autoDownloadHandledRef = useRef(false);

  const [order, setOrder] = useState<Form8843OrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [freshCompletion, setFreshCompletion] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [showOnboardingPrompt, setShowOnboardingPrompt] = useState(false);

  useEffect(() => {
    setCurrentUser(getUser());
  }, []);

  useEffect(() => {
    if (!orderId) {
      setError("Missing order ID");
      return;
    }

    let cancelled = false;
    getForm8843Order(orderId)
      .then((result) => {
        if (!cancelled) {
          setOrder(result);
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load order");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const raw = window.sessionStorage.getItem(ONBOARDING_STORAGE_KEY);
    if (!raw) {
      return;
    }

    try {
      const parsed = JSON.parse(raw) as { orderId?: string; email?: string };
      if (parsed.orderId === orderId) {
        setFreshCompletion(true);
        if (parsed.email) {
          setSubmittedEmail(parsed.email);
        }
      }
    } catch {
      window.sessionStorage.removeItem(ONBOARDING_STORAGE_KEY);
    }
  }, [orderId]);

  useEffect(() => {
    if (typeof window === "undefined" || currentUser || !freshCompletion) {
      setShowOnboardingPrompt(false);
      return;
    }

    const dismissed = window.sessionStorage.getItem(`${ONBOARDING_PROMPT_DISMISS_PREFIX}:${orderId}`);
    setShowOnboardingPrompt(dismissed !== "1");
  }, [currentUser, freshCompletion, orderId]);

  const dashboardHref = "/dashboard?source=form8843";
  const sameAccountEmail = matchesEmail(currentUser, submittedEmail);
  const shouldSwitchAccount = Boolean(currentUser && submittedEmail && !sameAccountEmail);
  const downloadRedirectHref = `/login?next=${encodeURIComponent(`/form-8843/success?orderId=${encodeURIComponent(orderId)}&download=1`)}`;
  const canDownload = Boolean(order?.pdf_url);
  const pendingDownload = searchParams.get("download") === "1";

  function dismissOnboardingPrompt() {
    setShowOnboardingPrompt(false);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(`${ONBOARDING_PROMPT_DISMISS_PREFIX}:${orderId}`, "1");
    }
  }

  const handleDownload = useCallback(async (fromRedirect = false) => {
    if (!orderId || !canDownload) {
      return;
    }

    setDownloadError(null);

    if (!currentUser || shouldSwitchAccount) {
      if (!fromRedirect) {
        router.push(downloadRedirectHref);
      }
      return;
    }

    setDownloadLoading(true);
    try {
      await downloadForm8843Pdf(orderId);
    } catch (nextError) {
      setDownloadError(nextError instanceof Error ? nextError.message : "Could not download the PDF");
    } finally {
      setDownloadLoading(false);
    }
  }, [canDownload, currentUser, downloadRedirectHref, orderId, router, shouldSwitchAccount]);

  useEffect(() => {
    if (!pendingDownload || !currentUser || autoDownloadHandledRef.current) {
      return;
    }

    autoDownloadHandledRef.current = true;
    const cleanUrl = `/form-8843/success?orderId=${encodeURIComponent(orderId)}`;

    if (shouldSwitchAccount) {
      setDownloadError(
        submittedEmail
          ? `Sign in with ${submittedEmail} to download this PDF.`
          : "Sign in with the same email used for this form to download the PDF.",
      );
      router.replace(cleanUrl);
      return;
    }

    void handleDownload(true);
    router.replace(cleanUrl);
  }, [currentUser, handleDownload, orderId, pendingDownload, router, shouldSwitchAccount, submittedEmail]);

  const introCopy = currentUser
    ? "Download the PDF, follow the filing checklist, and keep the filing visible in Guardian if you want reminders later."
    : "Sign in to download the PDF, then follow the filing checklist and keep the filing visible in Guardian if you want reminders later.";

  const downloadButtonLabel = downloadLoading
    ? "Downloading..."
    : !currentUser
      ? "Sign in to download PDF"
      : shouldSwitchAccount
        ? "Switch account to download"
        : "Download PDF";

  return (
    <>
      <div className="mx-auto max-w-5xl rounded-[32px] border border-white/80 bg-white/82 p-8 shadow-[0_28px_80px_rgba(61,84,128,0.08)] backdrop-blur md:p-12">
        <div className="mb-6 inline-flex rounded-full border border-[#dce6f3] bg-[#eef5ff] px-4 py-2 text-[12px] font-semibold uppercase tracking-[0.18em] text-[#5f78a8]">
          Form 8843 ready
        </div>
        <h1 className="text-[34px] font-extrabold tracking-tight text-[#0d1424]">Your form is ready. The next step is getting it filed and tracked.</h1>
        <p className="mt-4 max-w-3xl text-[16px] leading-7 text-[#556480]">
          {introCopy}
        </p>

        <div className="mt-8 grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Order</div>
            <div className="mt-2 break-all text-[14px] font-medium text-[#1a2942]">{orderId || "Not provided"}</div>
          </div>
          <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Status</div>
            <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{formatStatus(order?.status || (error ? "Unavailable" : "Loading"))}</div>
          </div>
          <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Mailing state</div>
            <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{formatStatus(order?.mailing_status || "Loading")}</div>
          </div>
          <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Email status</div>
            <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{formatStatus(order?.email_status || "Pending or skipped")}</div>
          </div>
        </div>

        {error ? (
          <div className="mt-8 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
            {error}
          </div>
        ) : null}

        {downloadError ? (
          <div className="mt-6 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
            {downloadError}
          </div>
        ) : null}

        {shouldSwitchAccount && submittedEmail ? (
          <div className="mt-6 rounded-2xl border border-[#f1e3b4] bg-[#fff9eb] px-4 py-3 text-[14px] leading-6 text-[#775a13]">
            This form was prepared with {submittedEmail}. Sign in with that email to download the PDF and keep it in the right Guardian account.
          </div>
        ) : null}

        <div className="mt-8 flex flex-col gap-3 md:flex-row">
          <button
            type="button"
            onClick={() => {
              void handleDownload();
            }}
            disabled={!canDownload || downloadLoading}
            className={`inline-flex items-center justify-center rounded-full px-6 py-3 text-[15px] font-semibold transition ${
              canDownload && !downloadLoading
                ? "bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] hover:bg-[#4f82de]"
                : "cursor-not-allowed bg-[#d9e3f0] text-[#90a0bb]"
            }`}
          >
            {downloadButtonLabel}
          </button>
          <Link
            href="/form-8843"
            className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-6 py-3 text-[15px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
          >
            Start another draft
          </Link>
          {currentUser ? (
            <Link
              href={dashboardHref}
              className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-6 py-3 text-[15px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
            >
              Open dashboard
            </Link>
          ) : null}
        </div>

        {!currentUser ? (
          <div className="mt-4 text-[13px] leading-6 text-[#6d7c95]">
            Use the same email from this form when you sign in if you want the filing saved in the right Guardian account.
          </div>
        ) : null}

        {order ? <FilingChecklistCard order={order} onOrderChange={setOrder} /> : null}
      </div>

      {showOnboardingPrompt ? (
        <div className="fixed bottom-4 left-4 right-4 z-40 max-w-sm rounded-[24px] border border-[#dbe5f2] bg-white/96 p-5 shadow-[0_24px_60px_rgba(31,49,87,0.18)] backdrop-blur md:bottom-6 md:left-6 md:right-auto">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">Next step</div>
              <h2 className="mt-2 text-[20px] font-bold tracking-tight text-[#0d1424]">Set up your Guardian check</h2>
            </div>
            <button
              type="button"
              onClick={dismissOnboardingPrompt}
              className="rounded-full border border-[#dbe5f2] px-3 py-1 text-[12px] font-semibold text-[#6d7c95] transition hover:text-[#0d1424]"
            >
              Dismiss
            </button>
          </div>
          <p className="mt-3 text-[14px] leading-6 text-[#556480]">
            Tell Guardian whether you are studying, working on OPT or STEM OPT, or running a company so the dashboard can surface the right document checks and deadlines next.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href="/check?source=form8843"
              onClick={dismissOnboardingPrompt}
              className="inline-flex items-center justify-center rounded-full bg-[#0f1728] px-5 py-2.5 text-[14px] font-semibold text-white transition hover:bg-[#1b2741]"
            >
              Continue onboarding
            </Link>
            <Link
              href={dashboardHref}
              onClick={dismissOnboardingPrompt}
              className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-5 py-2.5 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
            >
              Go to dashboard
            </Link>
          </div>
        </div>
      ) : null}
    </>
  );
}
