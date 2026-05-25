"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  createEngagement,
  downloadProfessionalSearchUrl,
  Engagement,
  getMarketplaceMatch,
  getProfessionalSearch,
  listCaseEngagements,
  type MarketplaceMatch,
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
import {
  professionalSearchVocabulary,
  type ProfessionalSearchVocabulary,
} from "@/lib/professionalSearchCopy";

const POLL_INTERVAL_MS = 3000;

function formatUSD(n: number | null | undefined): string {
  if (n == null) return "—";
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function safeName(s: unknown): string {
  return String(s ?? "item").replace(/[^a-z0-9-_]+/gi, "-").replace(/-+/g, "-").replace(/^-|-$/g, "").slice(0, 60);
}

function textValue(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "string") return value.trim() || null;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    const joined = value.map(textValue).filter(Boolean).join("; ");
    return joined || null;
  }
  return null;
}

function numberValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const match = value.match(/\d+/);
    return match ? Number(match[0]) : null;
  }
  return null;
}

function booleanValue(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "yes", "y", "1"].includes(normalized)) return true;
    if (["false", "no", "n", "0"].includes(normalized)) return false;
  }
  return null;
}

function alternateContacts(value: unknown): Array<{
  name: string;
  band: number | null;
  fit: string | null;
  takesOutsideConsults: boolean | null;
}> {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    const name = textValue(record.name);
    if (!name) return [];
    return [{
      name,
      band: numberValue(record.band),
      fit: textValue(record.fit_for_case),
      takesOutsideConsults: booleanValue(record.takes_outside_consults),
    }];
  });
}

type TierReportRow = NonNullable<ProfessionalSearch["tier_report"]>[number];

function tierFirmName(row: TierReportRow, fallback = "Unknown firm"): string {
  return (
    textValue(row.firm) ??
    textValue(row.vendor) ??
    textValue(row.name) ??
    fallback
  );
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
      a.download = `professional-search-${safeName(purpose)}-${searchId.slice(0, 8)}.${format}`;
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
  vocab,
}: {
  searchId: string;
  lang: Lang;
  vocab: ProfessionalSearchVocabulary;
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
            {vocab.reportDossierCopy}
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

/** Single flat tile rendered after the visible top-N preview rows.
 *
 *  Replaces the prior nested layout (outer "Behind the paywall" card
 *  wrapping an inner <Paywall> sub-card). The two cards repeated the
 *  same CTA — flattening into one tile keeps the message tight: how
 *  many firms are hidden, what the unlock buys, single button.
 */
function PreviewPaywallTail({
  hiddenCount,
  previewCount,
  searchId,
  lang,
  vocab,
}: {
  hiddenCount: number;
  previewCount: number;
  searchId: string;
  lang: Lang;
  vocab: ProfessionalSearchVocabulary;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isZh = lang === "zh";

  async function go() {
    setBusy(true);
    setError(null);
    trackProfessionalSearchEvent("professional_search_checkout_clicked", {
      search_id: searchId,
      surface: "preview_paywall_tail",
      lang,
    });
    try {
      const { url } = await startCheckout(searchId);
      window.location.href = url;
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      trackProfessionalSearchEvent("professional_search_checkout_failed", {
        search_id: searchId,
        surface: "preview_paywall_tail",
        message,
        lang,
      });
      setError(message);
      setBusy(false);
    }
  }

  return (
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
            {vocab.hiddenPreviewCopy(hiddenCount)}
          </div>
          <p className="mt-1 text-[12.5px] leading-5 text-[#556480]">
            {isZh
              ? `您看到的是评分最高的前 ${previewCount} 家。一次性 $15 解锁完整名单与可验证资质来源,永久访问。`
              : `Previewing top ${previewCount} by score. One-time $15 unlocks the full ranking, verified sources, and PDF + HTML report. Permanent access.`}
          </p>
        </div>
        <button
          type="button"
          onClick={go}
          disabled={busy}
          data-testid="find-lawyer-checkout"
          className="inline-flex shrink-0 items-center gap-2 rounded-full bg-[#5b8dee] px-5 py-2.5 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de] disabled:cursor-wait disabled:bg-[#a8bce8]"
        >
          {busy
            ? isZh ? "正在跳转到支付…" : "Redirecting…"
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
        <div className="mt-3 rounded-xl border border-[#ffd6d6] bg-[#fff4f4] px-3 py-2 text-[12px] text-[#a33a3a]">
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
  vocab,
}: {
  name: string;
  state: ProfessionalSearch["persona_status"][string];
  lang: Lang;
  vocab: ProfessionalSearchVocabulary;
}) {
  const t = FIND_LAWYER_STRINGS[lang];
  const status = state?.status ?? "running";
  const statusColors = {
    complete: "text-[#2f7a45]",
    failed: "text-[#a33a3a]",
    running: "text-[#2f5bae]",
    skipped: "text-[#7b8ba5]",
  };
  const dotColors = {
    complete: "bg-[#5ab474]",
    failed: "bg-[#d46b6b]",
    running: "bg-[#5b8dee]",
    skipped: "bg-[#b8c3d3]",
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
            ? vocab.resultCount(state.firm_count ?? 0)
            : status === "failed"
            ? (t.personaFailed as string)
            : status === "skipped"
            ? (t.personaSkipped as string)
            : (t.personaSearching as string)}
        </div>
      </div>
      {state?.status === "skipped" && state.reason && (
        <div className="mt-2 text-[12px] leading-5 text-[#7b8ba5]">
          {state.reason}
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
  const [marketplaceMatches, setMarketplaceMatches] = useState<MarketplaceMatch[]>([]);
  const stopped = useRef(false);
  const viewedRef = useRef(false);
  const completedSeenRef = useRef(false);
  const previewPaywallTailEmittedRef = useRef(false);

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

  async function trackTopN(n: number, firms: TierReportRow[]) {
    if (!caseId) return;
    setBatchTracking(true);
    setError(null);
    try {
      const tracked = new Set(engagements.map((e) => e.firm_name.toLowerCase()));
      const targets = firms
        .map((f) => tierFirmName(f))
        .filter((firmName) => firmName !== "Unknown firm")
        .filter((firmName) => !tracked.has(firmName.toLowerCase()))
        .slice(0, n);
      // Sequential: idempotent + small N. Parallel would race the soft-
      // dedupe in the backend.
      for (const firmName of targets) {
        try {
          await createEngagement(caseId, {
            firm_name: firmName,
            search_id: params.searchId,
          });
        } catch (err) {
          setError(err instanceof Error ? err.message : `Could not track ${firmName}`);
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

  // Fire once when the "N more firms behind the paywall" tile first
  // shows. Distinct from professional_search_paywall_viewed (top-of-list
  // banner) so we can measure preview-tail conversion separately. Lives
  // up here (above the early returns) so React's rules-of-hooks are
  // satisfied even when row is still loading.
  const tailHiddenCount = row && !row.is_paid
    ? Math.max(0, (row.tier_report?.length ?? 0) - 5)
    : 0;
  useEffect(() => {
    if (tailHiddenCount > 0 && !previewPaywallTailEmittedRef.current && row) {
      previewPaywallTailEmittedRef.current = true;
      trackProfessionalSearchEvent("professional_search_preview_paywall_shown", {
        search_id: row.id,
        hidden_count: tailHiddenCount,
        preview_count: 5,
        total_firms: row.tier_report?.length ?? 0,
        lang,
      });
    }
  }, [tailHiddenCount, row, lang]);

  const rowId = row?.id ?? null;
  const rowStatus = row?.status ?? null;

  useEffect(() => {
    let cancelled = false;
    if (!rowId || rowStatus !== "complete") {
      setMarketplaceMatches([]);
      return;
    }
    getMarketplaceMatch(rowId)
      .then((matches) => {
        if (!cancelled) setMarketplaceMatches(matches);
      })
      .catch(() => {
        if (!cancelled) setMarketplaceMatches([]);
      });
    return () => {
      cancelled = true;
    };
  }, [rowId, rowStatus]);

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
  const vocab = professionalSearchVocabulary(row.vertical, lang);
  // Pre-payment: show only the top N firms as a free preview. The rest are
  // hidden behind the paywall so users can sample the quality of the
  // shortlist without seeing the full set. Five is enough for a meaningful
  // preview of the tier-pyramid (1 elite + 2-3 strong matches + a back-up)
  // without giving away the long tail.
  const PREVIEW_COUNT = 5;
  const visibleRows = row.is_paid ? tierRows : tierRows.slice(0, PREVIEW_COUNT);
  const hiddenCount = row.is_paid ? 0 : Math.max(0, tierRows.length - PREVIEW_COUNT);

  // Build a lookup table from firm name → firms_data entry so tier rows
  // (which come from the diligence DB query) can pick up Stage-2 enrichment
  // fields stored on firms_data. Lower-cased keys to dodge minor
  // capitalization drift between persona output and diligence ingestion.
  const firmsDataByName = new Map<string, Record<string, unknown>>();
  for (const f of row.firms_data ?? []) {
    const name = String((f?.name as string) || "").trim().toLowerCase();
    if (name) firmsDataByName.set(name, f);
  }

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
              <div className="mt-1 text-[13px]">
                {isZh
                  ? "本次搜索未能完成。请重试,或在面板中联系 Guardian 支持。"
                  : "This search did not complete. Please retry or contact Guardian support from your dashboard."}
              </div>
              <div className="mt-2 text-[12px] leading-5">
                {row.error}
              </div>
            </div>
          )}
          {error ? (
            <div data-testid="find-lawyer-status-error" className="mt-5 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
              {error}
            </div>
          ) : null}
        </header>

        {marketplaceMatches.length > 0 && (
          <section className="rounded-[32px] border border-white/70 bg-white/72 p-6 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
              {isZh ? "下一步服务" : "Next step services"}
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {marketplaceMatches.slice(0, 4).map((match) => {
                const href = match.path || `/services/${match.sku}`;
                return (
                  <button
                    key={match.sku}
                    type="button"
                    onClick={() => router.push(href)}
                    data-testid={`find-lawyer-marketplace-${safeName(match.sku).toLowerCase()}`}
                    className="rounded-2xl border border-[#dbe5f2] bg-white/82 p-4 text-left shadow-[0_10px_30px_rgba(61,84,128,0.05)] transition hover:border-[#5b8dee] hover:shadow-[0_14px_34px_rgba(91,141,238,0.12)]"
                  >
                    <div className="text-[14px] font-semibold text-[#0d1424]">
                      {match.public_name || match.name}
                    </div>
                    <p className="mt-1 text-[12px] leading-5 text-[#556480]">
                      {match.match_reason || match.public_headline || match.headline || match.public_description || match.description}
                    </p>
                    <div className="mt-3 text-[11px] font-semibold text-[#5b8dee]">
                      {match.public_cta_label || match.cta_label || (isZh ? "查看服务" : "Open service")}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        )}

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
                <PersonaCard key={name} name={name} state={state} lang={lang} vocab={vocab} />
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
                  {vocab.resultCount(tierRows.length)}
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
                    ? vocab.trackingCount(engagements.length)
                    : vocab.trackingPrompt}
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
                <Paywall searchId={row.id} lang={lang} vocab={vocab} />
              </div>
            )}

            {/* Stage-2 enrichment banner. Only renders for paid users while
                Stage 2 is in flight. Pre-payment users see the preview-tail
                paywall instead, which serves the same "you'll get more after
                payment" message. */}
            {row.is_paid && row.enrichment_status === "enriching" && (
              <div className="mt-4 rounded-2xl border border-[#cfe1ff] bg-gradient-to-br from-white via-[#f5faff] to-[#eaf2ff] p-4">
                <div className="flex items-start gap-3">
                  <span
                    aria-hidden="true"
                    className="mt-0.5 inline-block h-2 w-2 shrink-0 animate-pulse rounded-full bg-[#5b8dee]"
                  />
                  <div>
                    <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-[#5b8dee]">
                      {isZh ? "正在深度核实" : vocab.enrichmentTitle}
                    </div>
                    <p className="mt-1 text-[13px] leading-5 text-[#556480]">
                      {vocab.enrichmentBody}
                    </p>
                  </div>
                </div>
              </div>
            )}
            {row.is_paid && row.enrichment_status === "failed" && (
              <div className="mt-4 rounded-2xl border border-[#ffe3c9] bg-[#fff6ea] px-4 py-3">
                <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-[#9c5a1c]">
                  {isZh ? "深度核实失败" : "Enrichment failed"}
                </div>
                <p className="mt-1 text-[13px] leading-5 text-[#a06524]">
                  {isZh
                    ? vocab.enrichmentFailedBody
                    : vocab.enrichmentFailedBody}
                </p>
              </div>
            )}

            <div className="mt-6 space-y-3">
              {visibleRows.map((r, idx) => {
                const firmName = tierFirmName(r, vocab.unknownOrg);
                const priority = textValue(r.priority);
                const status = textValue(r.status) ?? "prospective";
                const nextAction = textValue(r.next_action);
                const nextActionDate = textValue(r.next_action_date);
                const score = numberValue(r.score);
                const openRisks = numberValue(r.open_risks) ?? 0;
                const lowestQuote = numberValue(r.lowest_quote);
                const highestQuote = numberValue(r.highest_quote);
                const isTracked = engagements.some(
                  (e) => e.firm_name.toLowerCase() === firmName.toLowerCase(),
                );
                return (
                <div
                  key={`${firmName}-${idx}`}
                  className="rounded-2xl border border-[#e4edf7] bg-white/82 p-5 shadow-[0_10px_30px_rgba(61,84,128,0.05)]"
                >
                  <div className="flex items-start gap-5">
                    <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-2xl border border-[#dbe5f2] bg-[#fbfdff]">
                      <div className="text-[20px] font-extrabold leading-none text-[#0d1424]">
                        {score ?? "—"}
                      </div>
                      <div className="mt-1 text-[9px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">
                        score
                      </div>
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <div className="text-[17px] font-bold text-[#0d1424]">
                          {firmName}
                        </div>
                        {priority && (
                          <span
                            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${priorityStyle(priority)}`}
                          >
                            {priority}
                          </span>
                        )}
                        {openRisks > 0 && (
                          <span className="inline-flex items-center rounded-full border border-[#ffd6d6] bg-[#fff4f4] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#a33a3a]">
                            {openRisks} {openRisks === 1 ? "risk" : "risks"}
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
                              onClick={() => trackOne(firmName)}
                              disabled={tracking === firmName}
                              data-testid={`find-lawyer-track-${safeName(firmName).toLowerCase()}`}
                              className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white/80 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#40536f] hover:border-[#5b8dee] hover:text-[#1a2036] disabled:opacity-50"
                            >
                              {tracking === firmName ? "tracking…" : "+ track"}
                            </button>
                          )
                        )}
                      </div>

                      <dl className="mt-3 grid grid-cols-1 gap-x-8 gap-y-1 text-[13px] sm:grid-cols-2">
                        <div className="flex gap-2">
                          <dt className="text-[#7b8ba5]">{t.rowFee as string}</dt>
                          <dd className="font-medium text-[#40536f]">
                            {lowestQuote != null || highestQuote != null
                              ? `${formatUSD(lowestQuote)} – ${formatUSD(highestQuote)}`
                              : "—"}
                          </dd>
                        </div>
                        <div className="flex gap-2">
                          <dt className="text-[#7b8ba5]">{t.rowStatus as string}</dt>
                          <dd className="font-medium text-[#40536f]">
                            {status}
                          </dd>
                        </div>
                        {nextAction && (
                          <div className="col-span-2 flex gap-2">
                            <dt className="text-[#7b8ba5]">{t.rowNext as string}</dt>
                            <dd className="font-medium text-[#40536f]">
                              {nextAction}
                              {nextActionDate && (
                                <span className="text-[#7b8ba5]">
                                  {" "}
                                  &middot; by {nextActionDate}
                                </span>
                              )}
                            </dd>
                          </div>
                        )}
                      </dl>

                      {/* Stage-2 enrichment block. Renders only when this
                          firm has at least one enrichment field set —
                          gracefully degrades for legacy paid searches that
                          haven't been backfilled. Three sub-elements: the
                          firm-vs-individual band-gap warning, the lead
                          attorney's individual band/focus, and the alternate-
                          attorney suggestions list. Hidden for unpaid views
                          since we paywall this whole layer. */}
                      {row.is_paid && (() => {
                        const enriched = firmsDataByName.get(firmName.toLowerCase());
                        if (!enriched || !enriched._enriched_at) return null;
                        const gapWarning = textValue(enriched._individual_vs_firm_band_gap_warning);
                        const attorneyBand = numberValue(enriched._lead_attorney_band);
                        const bandSource = textValue(enriched._lead_attorney_band_source);
                        const bandYear = numberValue(enriched._lead_attorney_band_year);
                        const practiceFocus = textValue(enriched._lead_attorney_practice_focus);
                        const takesConsults = booleanValue(enriched._lead_attorney_takes_outside_consults);
                        const alternates = alternateContacts(enriched._alternate_attorneys);
                        const leadName = textValue(enriched.lead_attorney) ?? textValue(enriched.lead_contact) ?? vocab.leadLabel;
                        return (
                          <div className="mt-4 rounded-xl border border-[#e4edf7] bg-[#f9fbfe] p-3">
                            {gapWarning && (
                              <div className="mb-2 inline-flex items-start gap-2 rounded-lg border border-[#ffe3c9] bg-[#fff6ea] px-2.5 py-1.5">
                                <span aria-hidden="true" className="mt-0.5">⚠️</span>
                                <span className="text-[12px] font-medium text-[#9c5a1c]">
                                  {gapWarning}
                                </span>
                              </div>
                            )}
                            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[12.5px]">
                              <span className="font-semibold text-[#0d1424]">
                                {leadName}
                              </span>
                              {attorneyBand != null && (
                                <span className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white px-2 py-0.5 text-[10px] font-semibold text-[#40536f]">
                                  {bandSource ? `${bandSource} ` : ""}Band {attorneyBand}
                                  {bandYear ? ` (${bandYear})` : ""}
                                </span>
                              )}
                              {takesConsults === false && (
                                <span className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-stone-50 px-2 py-0.5 text-[10px] font-semibold text-[#7b8ba5]">
                                  may not take outside consults
                                </span>
                              )}
                            </div>
                            {practiceFocus && (
                              <p className="mt-1 text-[12px] leading-5 text-[#556480]">
                                <span className="text-[#7b8ba5]">Practice focus: </span>
                                {practiceFocus}
                              </p>
                            )}
                            {alternates.length > 0 && (
                              <div className="mt-3 border-t border-[#e4edf7] pt-3">
                                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">
                                  {vocab.alternateHeader}
                                </div>
                                <ul className="mt-2 space-y-1.5">
                                  {alternates.slice(0, 3).map((a, ai) => {
                                    return (
                                      <li
                                        key={`${a.name}-${ai}`}
                                        className="text-[12px]"
                                        onClick={() => {
                                          trackProfessionalSearchEvent("professional_search_alternate_attorney_clicked", {
                                            search_id: row.id,
                                            firm: firmName,
                                            alternate_name: a.name,
                                            alternate_band: a.band,
                                            takes_consults: a.takesOutsideConsults,
                                            lang,
                                          });
                                        }}
                                      >
                                        <div className="flex flex-wrap items-baseline gap-x-2">
                                          <span className="font-semibold text-[#0d1424]">{a.name}</span>
                                          {a.band != null && (
                                            <span className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white px-1.5 py-0.5 text-[10px] font-semibold text-[#40536f]">
                                              Band {a.band}
                                            </span>
                                          )}
                                          {a.takesOutsideConsults === false && (
                                            <span className="text-[10px] text-[#9aa9c2]">(retained only)</span>
                                          )}
                                        </div>
                                        {a.fit && (
                                          <div className="mt-0.5 text-[11.5px] text-[#556480]">
                                            {a.fit}
                                          </div>
                                        )}
                                      </li>
                                    );
                                  })}
                                </ul>
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {/* Pre-payment caveat: be honest about why the
                          credentials shown here are firm-level only. The
                          $15 unlock buys per-attorney verification (which
                          firms_data._lead_attorney_* fields populate after
                          Stage 2). */}
                      {!row.is_paid && (
                        <p className="mt-3 text-[11px] italic leading-4 text-[#9aa9c2]">
                          {isZh
                            ? vocab.credentialCaveat
                            : vocab.credentialCaveat}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
                );
              })}

              {hiddenCount > 0 && (
                <PreviewPaywallTail
                  hiddenCount={hiddenCount}
                  previewCount={PREVIEW_COUNT}
                  searchId={row.id}
                  lang={lang}
                  vocab={vocab}
                />
              )}
            </div>

            <p className="mt-6 text-[12px] leading-5 text-[#7b8ba5]">
              Full credential lists, quotes, sources, and contact info are in
              the diligence database. Call the{" "}
              <code className="rounded bg-white/80 px-1 py-0.5 text-[11px]">
                vendor_detail
              </code>{" "}
              MCP tool or the vendor directory endpoint for any {vocab.orgSingular} above to
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
              {vocab.guardianCtaEyebrow}
            </div>
            <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div className="max-w-2xl">
                <div className="mt-1 text-[20px] font-bold leading-tight text-[#0d1424]">
                  {vocab.guardianCtaTitle}
                </div>
                <p className="mt-2 text-[13.5px] leading-6 text-[#556480]">
                  {vocab.guardianCtaBody}
                </p>
              </div>
              <div className="flex flex-col items-start gap-2 md:items-end">
                <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">
                  {isZh ? "价格" : "Pricing"}
                </div>
                <div className="text-[18px] font-bold text-[#0d1424]">TBD</div>
                <a
                  href={`mailto:info@yangtze-capital.com?subject=${encodeURIComponent(vocab.guardianCtaSubject)}`}
                  onClick={() => {
                    trackProfessionalSearchEvent("professional_search_attorney_inquiry_clicked", {
                      search_id: row.id,
                      vertical: row.vertical,
                      is_paid: Boolean(row.is_paid),
                      firms_count: tierRows.length,
                      lang,
                    });
                  }}
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
              Search finished but no {vocab.orgPlural} were ingested.
            </div>
            <div className="mt-1 text-[13px] text-[#a06524]">
              Please rerun the search or contact Guardian support from your dashboard.
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
