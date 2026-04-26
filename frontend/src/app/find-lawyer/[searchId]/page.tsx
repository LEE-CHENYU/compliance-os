"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  createEngagement,
  downloadProfessionalSearchUrl,
  Engagement,
  getProfessionalSearch,
  listCaseEngagements,
  startCheckout,
  type ProfessionalSearch,
} from "@/lib/api";
import {
  FIND_LAWYER_STRINGS,
  personaLabel,
  useLang,
  type Lang,
} from "@/lib/i18n";
import LangToggle from "@/components/LangToggle";
import { trackProfessionalSearchEvent } from "@/lib/analytics";

const POLL_INTERVAL_MS = 3000;

function formatUSD(n: number | null | undefined): string {
  if (n == null) return "—";
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function safeName(s: string): string {
  return s.replace(/[^a-z0-9-_]+/gi, "-").replace(/-+/g, "-").replace(/^-|-$/g, "").slice(0, 60);
}

/** Download the report by fetching it and triggering a save with the right filename.
 *  Surfaces server-side errors as inline UI instead of letting the browser
 *  save the JSON error body as `download.json`. */
function ReportActions({
  searchId,
  purpose,
  lang,
}: {
  searchId: string;
  purpose: string;
  lang: Lang;
}) {
  const t = FIND_LAWYER_STRINGS[lang];
  const [busy, setBusy] = useState<"pdf" | "html" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function downloadAs(format: "pdf" | "html") {
    setBusy(format);
    setError(null);
    try {
      const res = await fetch(
        `${downloadProfessionalSearchUrl(searchId)}?format=${format}`,
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lawyer-search-${safeName(purpose)}-${searchId.slice(0, 8)}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      trackProfessionalSearchEvent("professional_search_report_downloaded", {
        search_id: searchId,
        format,
        surface: "status_page",
        lang,
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      trackProfessionalSearchEvent("professional_search_report_download_failed", {
        search_id: searchId,
        format,
        message,
        lang,
      });
      setError(message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-end gap-3">
      {error && (
        <span className="rounded-full border border-[#ffd6d6] bg-[#fff4f4] px-3 py-1 text-[11px] font-semibold text-[#a33a3a]">
          {error}
        </span>
      )}
      <button
        type="button"
        onClick={() => downloadAs("pdf")}
        disabled={busy !== null}
        data-testid="find-lawyer-report-download-pdf"
        className="inline-flex items-center gap-2 rounded-full bg-[#5b8dee] px-5 py-2 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de] disabled:cursor-wait disabled:bg-[#a8bce8]"
      >
        <svg
          aria-hidden="true"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        {busy === "pdf" ? (t.btnDownloadPDFBusy as string) : (t.btnDownloadPDF as string)}
      </button>
      <a
        href={downloadProfessionalSearchUrl(searchId)}
        target="_blank"
        rel="noopener noreferrer"
        data-testid="find-lawyer-report-view-web"
        className="text-[12px] font-medium text-[#40536f] underline-offset-4 hover:text-[#1a2036] hover:underline"
      >
        {t.btnViewWeb as string}
      </a>
    </div>
  );
}

function StatusPill({ status }: { status: ProfessionalSearch["status"] }) {
  const palette: Record<ProfessionalSearch["status"], string> = {
    queued: "border-[#dce6f3] bg-white/80 text-[#6d7c95]",
    running: "border-[#cfe1ff] bg-[#eaf2ff] text-[#2f5bae]",
    complete: "border-[#cfe8d5] bg-[#eaf6ec] text-[#2f7a45]",
    failed: "border-[#ffd6d6] bg-[#fff4f4] text-[#a33a3a]",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] shadow-[0_8px_24px_rgba(42,64,102,0.06)] ${palette[status]}`}
    >
      {status}
    </span>
  );
}

function Paywall({
  searchId,
  lang,
}: {
  searchId: string;
  lang: Lang;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isZh = lang === "zh";

  // Fire viewed once when this component renders (i.e. paywall surfaces).
  useEffect(() => {
    trackProfessionalSearchEvent("professional_search_paywall_viewed", {
      search_id: searchId,
      lang,
    });
  }, [searchId, lang]);

  async function go() {
    setBusy(true);
    setError(null);
    trackProfessionalSearchEvent("professional_search_checkout_clicked", {
      search_id: searchId,
      lang,
    });
    try {
      const { url } = await startCheckout(searchId);
      window.location.href = url;
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      trackProfessionalSearchEvent("professional_search_checkout_failed", {
        search_id: searchId,
        message,
        lang,
      });
      setError(message);
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-[#dbe5f2] bg-gradient-to-br from-white via-[#f8fbff] to-[#eaf2ff] p-5 shadow-[0_10px_30px_rgba(61,84,128,0.06)]">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5b8dee]">
            {isZh ? "解锁完整报告" : "Unlock the full report"}
          </div>
          <div className="mt-1 text-[15px] font-semibold text-[#0d1424]">
            {isZh
              ? "PDF + 网页版报告，包含完整律所简介、可验证资质与原始资料链接"
              : "PDF + HTML report — full firm dossiers, credentials, and verification sources"}
          </div>
          <div className="mt-1 text-[12px] text-[#7b8ba5]">
            {isZh
              ? "一次性付费 $15 美元，永久访问。"
              : "One-time $15 USD · permanent access."}
          </div>
        </div>
        <button
          type="button"
          onClick={go}
          disabled={busy}
          data-testid="find-lawyer-checkout"
          className="inline-flex items-center gap-2 rounded-full bg-[#5b8dee] px-5 py-2.5 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de] disabled:cursor-wait disabled:bg-[#a8bce8]"
        >
          {busy
            ? isZh ? "正在跳转到支付…" : "Redirecting to checkout…"
            : isZh ? "$15 解锁" : "Unlock for $15"}
          {!busy && (
            <svg
              aria-hidden="true"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12h14M13 5l7 7-7 7" />
            </svg>
          )}
        </button>
      </div>
      {error && (
        <div data-testid="find-lawyer-checkout-error" className="mt-3 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-3 py-2 text-[12px] text-[#a33a3a]">
          {error}
        </div>
      )}
    </div>
  );
}

function PersonaCard({
  name,
  state,
  lang,
}: {
  name: string;
  state: ProfessionalSearch["persona_status"][string];
  lang: Lang;
}) {
  const t = FIND_LAWYER_STRINGS[lang];
  const status = state?.status ?? "running";
  const statusColors = {
    complete: "text-[#2f7a45]",
    failed: "text-[#a33a3a]",
    running: "text-[#2f5bae]",
  };
  const dotColors = {
    complete: "bg-[#5ab474]",
    failed: "bg-[#d46b6b]",
    running: "bg-[#5b8dee]",
  };
  const s = status as keyof typeof statusColors;

  return (
    <div className="rounded-2xl border border-[#e4edf7] bg-white/82 p-5 shadow-[0_10px_30px_rgba(61,84,128,0.05)]">
      <div className="flex items-baseline justify-between">
        <div className="text-[15px] font-semibold text-[#0d1424]">
          {personaLabel(lang, name)}
        </div>
        <div className={`flex items-center gap-2 text-[12px] font-semibold ${statusColors[s]}`}>
          <span
            className={`h-2 w-2 rounded-full ${dotColors[s]} ${status === "running" ? "animate-pulse" : ""}`}
          />
          {status === "complete"
            ? (t.personaFirms as (n: number) => string)(state.firm_count ?? 0)
            : status === "failed"
            ? (t.personaFailed as string)
            : (t.personaSearching as string)}
        </div>
      </div>
      {state?.error && (
        <div className="mt-2 text-[12px] leading-5 text-[#a33a3a]">
          {state.error}
        </div>
      )}
      {state?.status === "complete" && (
        <div className="mt-2 text-[11px] text-[#7b8ba5]">
          {state.input_tokens?.toLocaleString() ?? 0} in ·{" "}
          {state.output_tokens?.toLocaleString() ?? 0} out
          {state.cache_read_tokens ? (
            <>
              {" "}
              · <span className="text-[#2f5bae]">
                {state.cache_read_tokens.toLocaleString()} cached
              </span>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}


function priorityStyle(priority: string | null): string {
  switch (priority) {
    case "critical":
      return "border-[#ffd6d6] bg-[#fff4f4] text-[#a33a3a]";
    case "high":
      return "border-[#ffe3c9] bg-[#fff6ea] text-[#9c5a1c]";
    case "medium":
      return "border-[#cfe1ff] bg-[#eaf2ff] text-[#2f5bae]";
    case "low":
      return "border-[#dbe5f2] bg-white/80 text-[#6d7c95]";
    default:
      return "border-[#dbe5f2] bg-white/80 text-[#7b8ba5]";
  }
}

export default function SearchStatus() {
  const params = useParams<{ searchId: string }>();
  const router = useRouter();
  const { lang, setLang } = useLang();
  const t = FIND_LAWYER_STRINGS[lang];
  const isZh = lang === "zh";
  const [row, setRow] = useState<ProfessionalSearch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [tracking, setTracking] = useState<string | null>(null);
  const [batchTracking, setBatchTracking] = useState(false);
  const stopped = useRef(false);
  const viewedRef = useRef(false);
  const completedSeenRef = useRef(false);

  useEffect(() => {
    stopped.current = false;
    async function poll() {
      try {
        const data = await getProfessionalSearch(params.searchId);
        if (stopped.current) return;
        setRow(data);
        // Fire status_viewed once on first successful load (with the
        // initial server-known status), and completed_viewed exactly once
        // when the row first transitions to complete in this session.
        if (!viewedRef.current) {
          viewedRef.current = true;
          trackProfessionalSearchEvent("professional_search_status_viewed", {
            search_id: data.id,
            status: data.status,
            vertical: data.vertical,
            is_paid: Boolean(data.is_paid),
          });
        }
        if (!completedSeenRef.current && data.status === "complete") {
          completedSeenRef.current = true;
          trackProfessionalSearchEvent("professional_search_completed_viewed", {
            search_id: data.id,
            vertical: data.vertical,
            is_paid: Boolean(data.is_paid),
            firms_count: data.tier_report?.length ?? 0,
          });
        }
        if (data.status === "complete" || data.status === "failed") {
          stopped.current = true;
          return;
        }
      } catch (e) {
        if (stopped.current) return;
        setError(e instanceof Error ? e.message : String(e));
      }
      if (!stopped.current) setTimeout(poll, POLL_INTERVAL_MS);
    }
    poll();
    return () => {
      stopped.current = true;
    };
  }, [params.searchId]);

  // Once we know the case_id, fetch existing engagements so we can show
  // "tracking" pills on already-tracked firms (and skip them in batch
  // operations). Refreshes after each successful track.
  const caseId = row?.case_id ?? null;
  async function refreshEngagements() {
    if (!caseId) return;
    const fresh = await listCaseEngagements(caseId).catch(() => []);
    setEngagements(fresh);
  }
  useEffect(() => {
    void refreshEngagements();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  async function trackOne(firmName: string) {
    if (!caseId) return;
    setTracking(firmName);
    setError(null);
    try {
      await createEngagement(caseId, {
        firm_name: firmName,
        search_id: params.searchId,
      });
      trackProfessionalSearchEvent("professional_search_firm_tracked", {
        search_id: params.searchId,
        case_id: caseId,
        firm_name: firmName,
      });
      await refreshEngagements();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not track this firm");
    } finally {
      setTracking(null);
    }
  }

  async function trackTopN(n: number, firms: { firm: string }[]) {
    if (!caseId) return;
    setBatchTracking(true);
    setError(null);
    try {
      const tracked = new Set(engagements.map((e) => e.firm_name.toLowerCase()));
      const targets = firms
        .filter((f) => !tracked.has(f.firm.toLowerCase()))
        .slice(0, n);
      // Sequential: idempotent + small N. Parallel would race the soft-
      // dedupe in the backend.
      for (const t of targets) {
        try {
          await createEngagement(caseId, {
            firm_name: t.firm,
            search_id: params.searchId,
          });
        } catch (err) {
          setError(err instanceof Error ? err.message : `Could not track ${t.firm}`);
          break;
        }
      }
      trackProfessionalSearchEvent("professional_search_top_n_tracked", {
        search_id: params.searchId,
        case_id: caseId,
        n: targets.length,
        requested: n,
      });
      await refreshEngagements();
    } finally {
      setBatchTracking(false);
    }
  }

  const bgClass =
    "min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(91,141,238,0.18),_transparent_32%),linear-gradient(180deg,#edf3f9_0%,#e6eef6_42%,#f4f7fb_100%)] px-6 py-10";

  if (error && !row) {
    return (
      <div className={bgClass}>
        <div className="mx-auto max-w-3xl">
          <div className="rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!row) {
    return (
      <div className={bgClass}>
        <div className="mx-auto max-w-3xl text-[#7b8ba5]">{t.loading as string}</div>
      </div>
    );
  }

  const personas = Object.entries(row.persona_status);
  const tierRows = row.tier_report ?? [];
  // Pre-payment: show only the top N firms as a free preview. The rest are
  // hidden behind the paywall so users can sample the quality of the
  // shortlist without seeing the full set. Five is enough for a meaningful
  // preview of the tier-pyramid (1 elite + 2-3 strong matches + a back-up)
  // without giving away the long tail.
  const PREVIEW_COUNT = 5;
  const visibleRows = row.is_paid ? tierRows : tierRows.slice(0, PREVIEW_COUNT);
  const hiddenCount = row.is_paid ? 0 : Math.max(0, tierRows.length - PREVIEW_COUNT);

  return (
    <div className={bgClass}>
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => router.push("/find-lawyer")}
              className="rounded-full border border-white/80 bg-white/75 px-4 py-2 text-sm font-medium text-[#52627d] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur transition hover:text-[#1a2036]"
            >
              {t.statusBtnNew as string}
            </button>
            {caseId && (
              <button
                type="button"
                onClick={() => router.push(`/case/${caseId}`)}
                className="rounded-full bg-[#5b8dee] px-4 py-2 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de]"
                title="Back to your case — engagements, Gmail, notes"
              >
                {lang === "zh" ? "← 返回案件" : "← Back to case"}
              </button>
            )}
          </div>
          <div className="flex items-center gap-3">
            <LangToggle
              lang={lang}
              onChange={(next) => {
                if (next !== lang) {
                  trackProfessionalSearchEvent("professional_search_lang_toggled", {
                    surface: "status_page",
                    from: lang,
                    to: next,
                    search_id: row.id,
                  });
                }
                setLang(next);
              }}
            />
            <StatusPill status={row.status} />
          </div>
        </div>

        <header className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
          <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
            {row.vertical.replace(/_/g, " ")}
          </div>
          <h1 className="mt-3 text-[34px] font-extrabold leading-[1.1] tracking-tight text-[#0d1424]">
            {row.purpose}
          </h1>
          <p className="mt-3 text-[14px] text-[#7b8ba5]">
            {t.statusStarted as string} {new Date(row.created_at).toLocaleString()}
            {row.completed_at && (
              <>
                {" · "}{t.statusFinished as string}{" "}
                {new Date(row.completed_at).toLocaleString()}
              </>
            )}
          </p>

          {row.status === "failed" && row.error && (
            <div className="mt-5 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
              <div className="font-semibold">{t.statusFailed as string}</div>
              <div className="mt-1 text-[13px]">{row.error}</div>
            </div>
          )}
          {error ? (
            <div data-testid="find-lawyer-status-error" className="mt-5 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
              {error}
            </div>
          ) : null}
        </header>

        <section className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
          <div className="mb-5 flex items-baseline justify-between">
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
              {t.statusAgents as string}
            </h2>
            {row.status === "running" && (
              <span className="text-[12px] text-[#7b8ba5]">{t.statusPolling as string}</span>
            )}
          </div>
          {personas.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[#c9d7eb] bg-white/70 px-5 py-8 text-center">
              <div className="text-[14px] font-semibold text-[#40536f]">
                {row.status === "queued"
                  ? (t.statusQueued as string)
                  : (t.statusSpinning as string)}
              </div>
              <div className="mt-2 text-[12px] text-[#7b8ba5]">
                {t.statusSpinningSub as string}
              </div>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {personas.map(([name, state]) => (
                <PersonaCard key={name} name={name} state={state} lang={lang} />
              ))}
            </div>
          )}
        </section>

        {tierRows.length > 0 && (
          <section
            id="tier-report-anchor"
            className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur scroll-mt-6"
          >
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-baseline gap-3">
                <h2 className="text-[22px] font-bold tracking-tight text-[#0d1424]">
                  {t.tierTitle as string}
                </h2>
                <span className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">
                  {(t.tierFirms as (n: number) => string)(tierRows.length)}
                </span>
              </div>
              {row.status === "complete" && row.is_paid && (
                <ReportActions searchId={row.id} purpose={row.purpose} lang={lang} />
              )}
            </div>
            <p className="text-[14px] leading-6 text-[#556480]">
              {t.tierBlurb as string}
            </p>

            {caseId && tierRows.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px]">
                <span className="text-[#7b8ba5]">
                  {engagements.length > 0
                    ? `${engagements.length} firm${engagements.length === 1 ? "" : "s"} tracked for this case`
                    : "Track firms to your case to organize outreach"}
                </span>
                <button
                  type="button"
                  onClick={() => trackTopN(3, tierRows)}
                  disabled={batchTracking}
                  data-testid="find-lawyer-track-top-3"
                  className="rounded-full border border-[#dbe5f2] bg-white/80 px-3 py-1 text-[11px] font-semibold text-[#40536f] hover:border-[#5b8dee] hover:text-[#1a2036] disabled:opacity-50"
                >
                  {batchTracking ? "Tracking…" : "Track top 3 →"}
                </button>
                <button
                  type="button"
                  onClick={() => router.push(`/case/${caseId}`)}
                  data-testid="find-lawyer-open-case"
                  className="rounded-full border border-[#dbe5f2] bg-white/80 px-3 py-1 text-[11px] font-semibold text-[#40536f] hover:border-[#5b8dee] hover:text-[#1a2036]"
                >
                  Open case →
                </button>
              </div>
            )}
            {/* Top-of-list Paywall only when there are 5 or fewer firms total
                — in that case the bottom-of-list "N more firms behind the
                paywall" tail card never renders, so we'd otherwise leave the
                user without a CTA. When there ARE more than 5 firms, the
                tail card below carries the unlock CTA and we skip this one
                to avoid double-banner clutter. */}
            {row.status === "complete" && !row.is_paid && tierRows.length <= PREVIEW_COUNT && (
              <div className="mt-4">
                <Paywall searchId={row.id} lang={lang} />
              </div>
            )}

            <div className="mt-6 space-y-3">
              {visibleRows.map((r, idx) => {
                const isTracked = engagements.some(
                  (e) => e.firm_name.toLowerCase() === r.firm.toLowerCase(),
                );
                return (
                <div
                  key={`${r.firm}-${idx}`}
                  className="rounded-2xl border border-[#e4edf7] bg-white/82 p-5 shadow-[0_10px_30px_rgba(61,84,128,0.05)]"
                >
                  <div className="flex items-start gap-5">
                    <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-2xl border border-[#dbe5f2] bg-[#fbfdff]">
                      <div className="text-[20px] font-extrabold leading-none text-[#0d1424]">
                        {r.score ?? "—"}
                      </div>
                      <div className="mt-1 text-[9px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">
                        score
                      </div>
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <div className="text-[17px] font-bold text-[#0d1424]">
                          {r.firm}
                        </div>
                        {r.priority && (
                          <span
                            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${priorityStyle(r.priority)}`}
                          >
                            {r.priority}
                          </span>
                        )}
                        {r.open_risks > 0 && (
                          <span className="inline-flex items-center rounded-full border border-[#ffd6d6] bg-[#fff4f4] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#a33a3a]">
                            {r.open_risks} {r.open_risks === 1 ? "risk" : "risks"}
                          </span>
                        )}
                        {caseId && (
                          isTracked ? (
                            <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em]">
                              tracking
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => trackOne(r.firm)}
                              disabled={tracking === r.firm}
                              data-testid={`find-lawyer-track-${safeName(r.firm).toLowerCase()}`}
                              className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white/80 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#40536f] hover:border-[#5b8dee] hover:text-[#1a2036] disabled:opacity-50"
                            >
                              {tracking === r.firm ? "tracking…" : "+ track"}
                            </button>
                          )
                        )}
                      </div>

                      <dl className="mt-3 grid grid-cols-1 gap-x-8 gap-y-1 text-[13px] sm:grid-cols-2">
                        <div className="flex gap-2">
                          <dt className="text-[#7b8ba5]">{t.rowFee as string}</dt>
                          <dd className="font-medium text-[#40536f]">
                            {r.lowest_quote || r.highest_quote
                              ? `${formatUSD(r.lowest_quote)} – ${formatUSD(r.highest_quote)}`
                              : "—"}
                          </dd>
                        </div>
                        <div className="flex gap-2">
                          <dt className="text-[#7b8ba5]">{t.rowStatus as string}</dt>
                          <dd className="font-medium text-[#40536f]">
                            {r.status}
                          </dd>
                        </div>
                        {r.next_action && (
                          <div className="col-span-2 flex gap-2">
                            <dt className="text-[#7b8ba5]">{t.rowNext as string}</dt>
                            <dd className="font-medium text-[#40536f]">
                              {r.next_action}
                              {r.next_action_date && (
                                <span className="text-[#7b8ba5]">
                                  {" "}
                                  &middot; by {r.next_action_date}
                                </span>
                              )}
                            </dd>
                          </div>
                        )}
                      </dl>
                    </div>
                  </div>
                </div>
                );
              })}

              {hiddenCount > 0 && (
                <div
                  data-testid="find-lawyer-preview-paywall-tail"
                  className="rounded-2xl border border-[#cfe1ff] bg-gradient-to-br from-white via-[#f5faff] to-[#eaf2ff] p-6 shadow-[0_10px_30px_rgba(91,141,238,0.08)]"
                >
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="min-w-0">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5b8dee]">
                        {isZh ? "已隐藏" : "Behind the paywall"}
                      </div>
                      <div className="mt-1 text-[15px] font-semibold text-[#0d1424]">
                        {isZh
                          ? `还有 ${hiddenCount} 家律所等待解锁`
                          : `${hiddenCount} more ${hiddenCount === 1 ? "firm" : "firms"} matched — unlock to compare the full shortlist`}
                      </div>
                      <p className="mt-1 text-[12.5px] leading-5 text-[#556480]">
                        {isZh
                          ? "您看到的是评分最高的前 5 家。$15 解锁完整名单、外部信用资料和联系方式。"
                          : `You're previewing the top ${PREVIEW_COUNT} by score. Unlock for $15 to see the full ranking, outside credentials, and contact info for every firm.`}
                      </p>
                    </div>
                    <div className="shrink-0">
                      <Paywall searchId={row.id} lang={lang} />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <p className="mt-6 text-[12px] leading-5 text-[#7b8ba5]">
              Full credential lists, quotes, sources, and contact info are in
              the diligence database. Call the{" "}
              <code className="rounded bg-white/80 px-1 py-0.5 text-[11px]">
                vendor_detail
              </code>{" "}
              MCP tool or the vendor directory endpoint for any firm above to
              pull the dossier.
            </p>
          </section>
        )}

        {/* End-of-firm-list "human review" CTA. Single tile, TBD pricing —
            differentiates from the firm shortlist (external counsel) by
            offering Guardian-staffed counsel as a hands-on alternative.
            Replaces the prior in-house product upsell that lived above the
            firm list with priced cards. */}
        {tierRows.length > 0 && (
          <section className="rounded-[32px] border border-[#cfe1ff] bg-gradient-to-br from-white via-[#f5faff] to-[#eaf2ff] p-7 shadow-[0_24px_70px_rgba(91,141,238,0.08)] backdrop-blur">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#5b8dee]">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#5b8dee]" />
              {isZh ? "或者由 Guardian 律师为您处理" : "Or have a Guardian attorney handle this"}
            </div>
            <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div className="max-w-2xl">
                <div className="mt-1 text-[20px] font-bold leading-tight text-[#0d1424]">
                  {isZh
                    ? "想让我们的律师亲自跟进?"
                    : "Want hands-on Guardian counsel?"}
                </div>
                <p className="mt-2 text-[13.5px] leading-6 text-[#556480]">
                  {isZh
                    ? "如果上面的律所对比不是您想要的,我们的内部律师可以直接接管整个案件 — 文件准备、提交、与 USCIS 沟通全程负责。请告诉我们您的情况,我们会回复定价方案。"
                    : "If you'd rather skip the shortlist comparison, a Guardian-staffed attorney can take the case end-to-end — drafting, filing, USCIS correspondence. Tell us about your situation and we'll come back with pricing."}
                </p>
              </div>
              <div className="flex flex-col items-start gap-2 md:items-end">
                <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">
                  {isZh ? "价格" : "Pricing"}
                </div>
                <div className="text-[18px] font-bold text-[#0d1424]">TBD</div>
                <a
                  href="mailto:info@yangtze-capital.com?subject=Guardian%20attorney%20engagement%20inquiry"
                  className="mt-1 inline-flex items-center gap-2 rounded-full bg-[#5b8dee] px-5 py-2.5 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de]"
                >
                  {isZh ? "联系我们 →" : "Get in touch →"}
                </a>
              </div>
            </div>
          </section>
        )}

        {row.status === "complete" && tierRows.length === 0 && (
          <section className="rounded-[32px] border border-[#ffe3c9] bg-[#fff6ea]/80 p-6 backdrop-blur">
            <div className="text-[14px] font-semibold text-[#9c5a1c]">
              Search finished but no firms were ingested.
            </div>
            <div className="mt-1 text-[13px] text-[#a06524]">
              Check per-agent errors above.
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
