"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import FilingChecklistCard from "@/components/form8843/FilingChecklistCard";
import { getUser, login, register, type AuthUser } from "@/lib/auth";
import { getForm8843Order, resolveForm8843PdfUrl, type Form8843OrderResponse } from "@/lib/marketplace";


const ONBOARDING_STORAGE_KEY = "guardian_form_8843_onboarding";

type AuthMode = "register" | "login";

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
  const [order, setOrder] = useState<Form8843OrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

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
      if (parsed.orderId === orderId && parsed.email && !email) {
        setEmail(parsed.email);
      }
    } catch {
      window.sessionStorage.removeItem(ONBOARDING_STORAGE_KEY);
    }
  }, [orderId, email]);

  const pdfUrl = resolveForm8843PdfUrl(order?.pdf_url || null);
  const dashboardHref = "/dashboard?source=form8843";
  const sameAccountEmail = matchesEmail(currentUser, email);
  const needsOnboarding = !currentUser || !sameAccountEmail;

  const onboardingCopy = useMemo(() => {
    if (!currentUser) {
      return "Use the same email from this form if you want to save this filing in Guardian and keep track of the mailing step.";
    }
    if (!sameAccountEmail && email) {
      return `This form was prepared with ${email}. Sign in or create an account with that address if you want it saved in the right Guardian account.`;
    }
    return "This filing is ready to view in Guardian.";
  }, [currentUser, email, sameAccountEmail]);

  async function handleAuthSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authLoading) {
      return;
    }

    setAuthLoading(true);
    setAuthError(null);
    try {
      const user = authMode === "register"
        ? await register(email.trim(), password)
        : await login(email.trim(), password);
      setCurrentUser(user);
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem(ONBOARDING_STORAGE_KEY);
      }
      router.push(dashboardHref);
    } catch (nextError) {
      setAuthError(nextError instanceof Error ? nextError.message : "Could not continue");
    } finally {
      setAuthLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl rounded-[32px] border border-white/80 bg-white/82 p-8 shadow-[0_28px_80px_rgba(61,84,128,0.08)] backdrop-blur md:p-12">
      <div className="mb-6 inline-flex rounded-full border border-[#dce6f3] bg-[#eef5ff] px-4 py-2 text-[12px] font-semibold uppercase tracking-[0.18em] text-[#5f78a8]">
        Form 8843 ready
      </div>
      <h1 className="text-[34px] font-extrabold tracking-tight text-[#0d1424]">Your form is ready. The next step is getting it filed and tracked.</h1>
      <p className="mt-4 max-w-3xl text-[16px] leading-7 text-[#556480]">
        Download the PDF, follow the filing checklist, and if you want a saved record and reminders, keep this filing in Guardian.
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

      <div className="mt-8 flex flex-col gap-3 md:flex-row">
        <a
          href={pdfUrl || "#"}
          target="_blank"
          rel="noreferrer"
          className={`inline-flex items-center justify-center rounded-full px-6 py-3 text-[15px] font-semibold transition ${
            pdfUrl
              ? "bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] hover:bg-[#4f82de]"
              : "pointer-events-none bg-[#d9e3f0] text-[#90a0bb]"
          }`}
        >
          Download PDF
        </a>
        <Link
          href="/form-8843"
          className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-6 py-3 text-[15px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
        >
          Start another draft
        </Link>
        {needsOnboarding ? (
          <button
            type="button"
            onClick={() => {
              document.getElementById("save-in-dashboard")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
            className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-6 py-3 text-[15px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
          >
            Save in Guardian
          </button>
        ) : (
          <Link
            href={dashboardHref}
            className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-6 py-3 text-[15px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
          >
            Open dashboard
          </Link>
        )}
      </div>

      {order ? <FilingChecklistCard order={order} onOrderChange={setOrder} /> : null}

      <section
        id="save-in-dashboard"
        className="mt-8 rounded-[28px] border border-[#dbe5f2] bg-[#fbfdff] p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">Next step</div>
            <h2 className="mt-2 text-[28px] font-bold tracking-tight text-[#0d1424]">
              {needsOnboarding ? "Save this filing in Guardian" : "This filing is ready in Guardian"}
            </h2>
            <p className="mt-3 text-[15px] leading-7 text-[#556480]">{onboardingCopy}</p>
          </div>
          <div className="rounded-2xl border border-[#dbe5f2] bg-white px-4 py-3 text-right shadow-[0_10px_26px_rgba(61,84,128,0.05)]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Why save it</div>
            <div className="mt-2 max-w-[200px] text-[14px] leading-6 text-[#1a2942]">
              Keep the form, the filing status, and the next reminder in one place.
            </div>
          </div>
        </div>

        {needsOnboarding ? (
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.05fr,0.95fr]">
            <form onSubmit={handleAuthSubmit} className="rounded-[24px] border border-[#dbe5f2] bg-white p-5">
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("register");
                    setAuthError(null);
                  }}
                  className={`rounded-full px-4 py-2 text-[13px] font-semibold transition ${
                    authMode === "register"
                      ? "bg-[#0f1728] text-white"
                      : "border border-[#dbe5f2] bg-[#fbfdff] text-[#40536f]"
                  }`}
                >
                  Create account
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("login");
                    setAuthError(null);
                  }}
                  className={`rounded-full px-4 py-2 text-[13px] font-semibold transition ${
                    authMode === "login"
                      ? "bg-[#0f1728] text-white"
                      : "border border-[#dbe5f2] bg-[#fbfdff] text-[#40536f]"
                  }`}
                >
                  Sign in
                </button>
              </div>

              {currentUser && !sameAccountEmail ? (
                <div className="mt-4 rounded-2xl border border-[#f1e3b4] bg-[#fff9eb] px-4 py-3 text-[13px] leading-6 text-[#775a13]">
                  You are currently signed in as {currentUser.email}. Use {email || "the same email from this form"} if you want this filing saved in the right account.
                </div>
              ) : null}

              {authError ? (
                <div className="mt-4 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
                  {authError}
                </div>
              ) : null}

              <div className="mt-4 grid gap-4">
                <label className="block">
                  <div className="mb-2 text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">Email</div>
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    className="w-full rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] px-4 py-3 text-[15px] text-[#0d1424] shadow-[0_8px_28px_rgba(61,84,128,0.04)] outline-none transition focus:border-[#5b8dee] focus:ring-4 focus:ring-[#5b8dee]/10"
                    placeholder="you@example.com"
                  />
                </label>
                <label className="block">
                  <div className="mb-2 text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">Password</div>
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    minLength={6}
                    className="w-full rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] px-4 py-3 text-[15px] text-[#0d1424] shadow-[0_8px_28px_rgba(61,84,128,0.04)] outline-none transition focus:border-[#5b8dee] focus:ring-4 focus:ring-[#5b8dee]/10"
                    placeholder={authMode === "register" ? "Create a password" : "Your password"}
                  />
                </label>
              </div>

              <button
                type="submit"
                disabled={authLoading}
                className="mt-5 inline-flex items-center justify-center rounded-full bg-[#5b8dee] px-6 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de] disabled:cursor-not-allowed disabled:bg-[#9dbcf4]"
              >
                {authLoading
                  ? "Opening Guardian..."
                  : authMode === "register"
                    ? "Create account and continue"
                    : "Sign in and continue"}
              </button>
            </form>

            <div className="rounded-[24px] border border-[#dbe5f2] bg-white p-5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">What this helps with</div>
              <div className="mt-4 space-y-3">
                {[
                  "Keep this Form 8843 saved in one place instead of losing it in downloads.",
                  "Track whether you already mailed it and stop reminders once it is done.",
                  "Get the next relevant tax or immigration tasks based on your documents.",
                ].map((item) => (
                  <div key={item} className="flex gap-3 text-[14px] leading-6 text-[#435774]">
                    <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-[#5b8dee]" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href={dashboardHref}
              className="inline-flex items-center justify-center rounded-full bg-[#5b8dee] px-6 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de]"
            >
              Open dashboard
            </Link>
            <Link
              href="/account/orders"
              className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-6 py-3 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
            >
              View saved orders
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
