"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";

import {
  claimSearch,
  downloadProfessionalSearchUrl,
  getProfessionalSearch,
  type ProfessionalSearch,
} from "@/lib/api";
import { isLoggedIn, login, register } from "@/lib/auth";
import { useLang } from "@/lib/i18n";
import LangToggle from "@/components/LangToggle";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 30; // ~60 s

/** "Save it to your account" CTA — three concrete benefits, in EN/中文. */
const BENEFITS = {
  en: [
    {
      title: "Access this report anytime",
      body: "Re-download the PDF and HTML from any device. No expiring links — your purchase stays in your account.",
      icon: "report",
    },
    {
      title: "Manage your case documents",
      body: "Upload and organize the files this firm will ask for — passport scans, I-797s, source-of-funds paperwork, prior filings. Guardian's data room keeps them ready.",
      icon: "docs",
    },
    {
      title: "Track ongoing communications",
      body: "Keep emails, consultation notes, and contracts with the firms you reach out to in one place — alongside your timeline of compliance deadlines.",
      icon: "mail",
    },
  ],
  zh: [
    {
      title: "随时访问您的报告",
      body: "从任何设备重新下载 PDF 和网页版。链接永不过期，您的购买永久保存在账户中。",
      icon: "report",
    },
    {
      title: "管理您的案件文件",
      body: "上传并整理律所所需的文件 — 护照扫描件、I-797、资金来源材料、历次申请记录。Guardian 数据室让所有材料随时备查。",
      icon: "docs",
    },
    {
      title: "追踪沟通记录",
      body: "将您与律所之间的邮件、咨询笔记、合同等集中管理 — 与合规时间线一起呈现。",
      icon: "mail",
    },
  ],
} as const;

function Icon({ name }: { name: string }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  if (name === "report")
    return (
      <svg {...common}>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="9" y1="13" x2="15" y2="13" />
        <line x1="9" y1="17" x2="13" y2="17" />
      </svg>
    );
  if (name === "docs")
    return (
      <svg {...common}>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    );
  return (
    <svg {...common}>
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  );
}

export default function PaidPageWrapper() {
  return (
    <Suspense fallback={null}>
      <PaidPage />
    </Suspense>
  );
}

function PaidPage() {
  const params = useParams<{ searchId: string }>();
  const router = useRouter();
  const search = useSearchParams();
  const { lang, setLang } = useLang();
  const isZh = lang === "zh";

  const [row, setRow] = useState<ProfessionalSearch | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [pollTimedOut, setPollTimedOut] = useState(false);
  const [authMode, setAuthMode] = useState<"signup" | "login">("signup");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [claimed, setClaimed] = useState<boolean>(false);

  // Poll until the webhook has marked the search paid (or claimed).
  useEffect(() => {
    let stopped = false;
    let attempts = 0;
    async function poll() {
      try {
        const r = await getProfessionalSearch(params.searchId);
        if (stopped) return;
        setRow(r);
        if (r.is_paid) return; // we're done waiting
      } catch (e) {
        if (stopped) return;
        setPollError(e instanceof Error ? e.message : String(e));
      }
      attempts += 1;
      if (!stopped) {
        if (attempts < MAX_POLL_ATTEMPTS) {
          setTimeout(poll, POLL_INTERVAL_MS);
        } else {
          // Surface the timeout to the user so they're not staring at a
          // forever-spinner. The most common cause is a webhook that
          // hasn't been registered (or has been temporarily delayed by
          // Stripe). Funds are safe regardless — we only mark `paid_at`
          // when the webhook arrives, so retrying later is non-destructive.
          setPollTimedOut(true);
        }
      }
    }
    poll();
    return () => {
      stopped = true;
    };
  }, [params.searchId]);

  // If already logged in (e.g. user paid while logged in), claim immediately.
  useEffect(() => {
    if (row?.is_paid && isLoggedIn() && !row.is_claimed && !claimed) {
      claimSearch(params.searchId)
        .then(() => setClaimed(true))
        .catch(() => undefined);
    }
    if (row?.is_claimed) setClaimed(true);
    // Pre-fill email from Stripe if present.
    if (row?.stripe_customer_email && !email) setEmail(row.stripe_customer_email);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [row?.is_paid, row?.is_claimed, row?.stripe_customer_email]);

  async function handleAuth(e: React.FormEvent) {
    e.preventDefault();
    setAuthBusy(true);
    setAuthError(null);
    try {
      if (authMode === "signup") {
        await register(email, password);
      } else {
        await login(email, password);
      }
      // Now we're logged in — claim the paid search.
      const claimed = await claimSearch(params.searchId);
      setClaimed(true);
      // If the brief was rich enough, the backend auto-created a case
      // (skipping the discovery wizard for users who already supplied
      // substantial context). Land on the case page so they see their
      // search waiting in the Lawyers section. Otherwise fall back to
      // the dashboard.
      const next = claimed.case_id
        ? `/case/${claimed.case_id}`
        : "/dashboard";
      setTimeout(() => router.push(next), 800);
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : String(e));
      setAuthBusy(false);
    }
  }

  const isPaid = !!row?.is_paid;
  const sessionId = search?.get("session_id");

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(91,141,238,0.18),_transparent_32%),linear-gradient(180deg,#edf3f9_0%,#e6eef6_42%,#f4f7fb_100%)] px-6 py-10">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between gap-3">
          <Link
            href={`/find-lawyer/${params.searchId}`}
            className="rounded-full border border-white/80 bg-white/75 px-4 py-2 text-sm font-medium text-[#52627d] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur transition hover:text-[#1a2036]"
          >
            {isZh ? "← 返回搜索" : "← Back to search"}
          </Link>
          <LangToggle lang={lang} onChange={setLang} />
        </div>

        <header className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
          <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#2f7a45]">
            {isZh ? "支付成功" : "Payment received"}
          </div>
          <h1 className="mt-3 font-[Charter,Georgia,serif] text-[40px] font-bold leading-[1.1] text-[#0d1424]">
            {isPaid
              ? isZh
                ? "您的报告已解锁。"
                : "Your report is unlocked."
              : isZh
              ? "正在确认您的支付…"
              : "Confirming your payment…"}
          </h1>
          <p className="mt-3 text-[15px] leading-7 text-[#556480]">
            {isPaid
              ? isZh
                ? "下方提供 PDF 和网页版下载。我们建议您将本次搜索保存到 Guardian 账户，以便日后管理。"
                : "PDF and web versions are below. We recommend saving this search to your Guardian account so you can come back to it later."
              : isZh
              ? "支付通常会在几秒内确认。如果超过一分钟仍未显示，请刷新页面。"
              : "Payment usually confirms within a few seconds. If it's not showing after a minute, refresh the page."}
          </p>
          {sessionId && (
            <div className="mt-3 text-[11px] text-[#7b8ba5]">
              {isZh ? "Stripe 会话" : "Stripe session"}: <code>{sessionId}</code>
            </div>
          )}
          {pollError && (
            <div className="mt-3 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-3 py-2 text-[12px] text-[#a33a3a]">
              {pollError}
            </div>
          )}

          {pollTimedOut && !isPaid && (
            <div className="mt-5 rounded-2xl border border-[#ffe3c9] bg-[#fff6ea] p-4">
              <div className="text-[13px] font-semibold text-[#9c5a1c]">
                {isZh
                  ? "支付确认超时（60 秒）"
                  : "Payment confirmation timed out (60s)"}
              </div>
              <p className="mt-1 text-[12.5px] leading-6 text-[#a06524]">
                {isZh
                  ? "您的款项是安全的 — Guardian 仅在收到 Stripe 的 webhook 通知后才会标记报告为已支付。请稍候片刻再刷新页面。如果问题持续，请联系支持。"
                  : "Your funds are safe — we only mark the report paid when Stripe's webhook arrives. Refresh in a moment, or contact support if it persists."}
              </p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="mt-3 rounded-full border border-[#ffe3c9] bg-white/80 px-4 py-1.5 text-[12px] font-semibold text-[#9c5a1c] hover:bg-white"
              >
                {isZh ? "刷新" : "Refresh"}
              </button>
            </div>
          )}

          {isPaid && (
            <div className="mt-6 flex flex-wrap gap-3">
              <a
                href={`${downloadProfessionalSearchUrl(params.searchId)}?format=pdf`}
                className="inline-flex items-center gap-2 rounded-full bg-[#5b8dee] px-5 py-2.5 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de]"
              >
                {isZh ? "下载 PDF" : "Download PDF"}
              </a>
              <a
                href={downloadProfessionalSearchUrl(params.searchId)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-[#dbe5f2] bg-white/90 px-5 py-2.5 text-[13px] font-semibold text-[#40536f] transition hover:border-[#5b8dee] hover:text-[#1a2036]"
              >
                {isZh ? "查看网页版" : "View web version"}
              </a>
            </div>
          )}
        </header>

        {/* Save-to-account CTA — only when paid and not yet claimed */}
        {isPaid && !claimed && (
          <section className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
            <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
              {isZh ? "保存到 Guardian 账户" : "Save this to your Guardian account"}
            </div>
            <h2 className="mt-2 font-[Charter,Georgia,serif] text-[28px] font-bold leading-tight text-[#0d1424]">
              {isZh
                ? "登录账户，长期使用您的研究成果"
                : "Sign up to keep using what you just bought."}
            </h2>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              {BENEFITS[lang].map((b) => (
                <div
                  key={b.title}
                  className="rounded-2xl border border-[#e4edf7] bg-white/82 p-4 shadow-[0_10px_30px_rgba(61,84,128,0.05)]"
                >
                  <div className="text-[#5b8dee]">
                    <Icon name={b.icon} />
                  </div>
                  <div className="mt-2 text-[14px] font-semibold text-[#0d1424]">{b.title}</div>
                  <p className="mt-1 text-[12.5px] leading-5 text-[#556480]">{b.body}</p>
                </div>
              ))}
            </div>

            <form onSubmit={handleAuth} className="mt-7 grid gap-3 sm:grid-cols-[1fr,1fr,auto]">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={isZh ? "邮箱" : "Email"}
                className="w-full rounded-2xl border border-[#dbe5f2] bg-white/90 px-4 py-3 text-[15px] text-[#0d1424] outline-none transition focus:border-[#5b8dee] focus:ring-4 focus:ring-[#5b8dee]/10"
              />
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isZh ? "密码 (至少 8 位)" : "Password (8+ chars)"}
                className="w-full rounded-2xl border border-[#dbe5f2] bg-white/90 px-4 py-3 text-[15px] text-[#0d1424] outline-none transition focus:border-[#5b8dee] focus:ring-4 focus:ring-[#5b8dee]/10"
              />
              <button
                type="submit"
                disabled={authBusy}
                className="rounded-full bg-[#5b8dee] px-6 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de] disabled:cursor-wait disabled:bg-[#a8bce8]"
              >
                {authBusy
                  ? isZh ? "处理中…" : "Processing…"
                  : authMode === "signup"
                  ? isZh ? "注册并保存" : "Create account & save"
                  : isZh ? "登录并保存" : "Log in & save"}
              </button>
            </form>
            <div className="mt-3 flex items-center justify-between text-[12px] text-[#7b8ba5]">
              <button
                type="button"
                onClick={() => setAuthMode(authMode === "signup" ? "login" : "signup")}
                className="underline-offset-4 hover:text-[#40536f] hover:underline"
              >
                {authMode === "signup"
                  ? isZh
                    ? "已经有账户？登录"
                    : "Already have an account? Log in"
                  : isZh
                  ? "还没有账户？注册"
                  : "New here? Create an account"}
              </button>
              {authError && (
                <span className="rounded-full border border-[#ffd6d6] bg-[#fff4f4] px-3 py-1 text-[#a33a3a]">
                  {authError}
                </span>
              )}
            </div>
          </section>
        )}

        {claimed && (
          <section className="rounded-[32px] border border-[#cfe8d5] bg-[#eaf6ec]/80 p-6 backdrop-blur">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#2f7a45]">
                  {isZh ? "已保存" : "Saved"}
                </div>
                <div className="mt-1 text-[15px] font-semibold text-[#0d1424]">
                  {isZh
                    ? "本次搜索已绑定到您的 Guardian 账户。"
                    : "This search is now linked to your Guardian account."}
                </div>
              </div>
              <Link
                href="/dashboard"
                className="rounded-full bg-[#5b8dee] px-5 py-2 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] hover:bg-[#4f82de]"
              >
                {isZh ? "前往面板 →" : "Go to dashboard →"}
              </Link>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
