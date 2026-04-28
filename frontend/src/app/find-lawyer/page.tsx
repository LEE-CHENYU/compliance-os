"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getCaseDraftBrief, startProfessionalSearch } from "@/lib/api";
import {
  FIND_LAWYER_STRINGS,
  VERTICAL_LABELS,
  personaPreviewsFor,
  useLang,
} from "@/lib/i18n";
import LangToggle from "@/components/LangToggle";
import { trackProfessionalSearchEvent } from "@/lib/analytics";
import { professionalSearchVocabulary } from "@/lib/professionalSearchCopy";

const VERTICAL_KEYS = [
  "immigration_attorney",
  "immigration_eb5",
  "tax_attorney",
  "corporate_attorney",
  "cpa",
  "bank",
  "caa",
] as const;

const PRIMARY_BTN =
  "rounded-full px-6 py-3 text-[14px] font-semibold transition bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] hover:bg-[#4f82de]";
const DISABLED_BTN =
  "rounded-full px-6 py-3 text-[14px] font-semibold bg-[#d9e3f0] text-[#90a0bb]";
const LABEL =
  "mb-2 text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]";
const INPUT =
  "w-full rounded-2xl border border-[#dbe5f2] bg-white/90 px-4 py-3 text-[15px] text-[#0d1424] shadow-[0_8px_28px_rgba(61,84,128,0.06)] outline-none transition focus:border-[#5b8dee] focus:ring-4 focus:ring-[#5b8dee]/10";

// Next.js 14 requires `useSearchParams()` in a client component to be
// wrapped in <Suspense> so static prerendering doesn't bail. The wrapper
// below is a no-op at runtime; it just satisfies the framework's
// build-time invariant.
export default function FindLawyerPage() {
  return (
    <Suspense fallback={null}>
      <FindLawyer />
    </Suspense>
  );
}

function FindLawyer() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const caseId = searchParams.get("case_id");
  const { lang, setLang } = useLang();
  const t = FIND_LAWYER_STRINGS[lang];
  const verticalsLocalized = VERTICAL_LABELS[lang];

  const [caseBrief, setCaseBrief] = useState("");
  const [purpose, setPurpose] = useState("");
  const [vertical, setVertical] = useState("immigration_attorney");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const vocab = professionalSearchVocabulary(vertical, lang);
  const [prefillState, setPrefillState] = useState<"idle" | "loading" | "ready" | "error">(
    caseId ? "loading" : "idle",
  );

  // Fire intake_viewed once per page load. Tracks the top of the funnel and
  // captures whether the user arrived with a pre-existing case context.
  useEffect(() => {
    trackProfessionalSearchEvent("professional_search_intake_viewed", {
      lang,
      has_case_id: Boolean(caseId),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    setPrefillState("loading");
    getCaseDraftBrief(caseId)
      .then((draft) => {
        if (cancelled) return;
        // Only fill if the field is still untouched — never clobber a user
        // who started typing before the pre-fill returned.
        setCaseBrief((current) => current || draft.brief);
        setPurpose((current) => current || draft.suggested_purpose);
        setVertical((current) =>
          current === "immigration_attorney" ? draft.suggested_vertical : current,
        );
        setPrefillState("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setPrefillState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  // Each search costs ~$2-3 in API + web_search calls, so we gate on a
  // meaningful brief — 200 chars (~30-40 words) is roughly the floor for
  // an agent to do useful research. Below that we'd waste compute on
  // searches that can't be tailored.
  const MIN_BRIEF_CHARS = 200;
  const briefLen = caseBrief.trim().length;
  const purposeOk = purpose.trim().length >= 4;
  const briefOk = briefLen >= MIN_BRIEF_CHARS;
  const canSubmit = purposeOk && briefOk && !submitting;

  // Quality indicator: encourage longer briefs without blocking once the
  // minimum is met. Above 500 chars the agents have lots to work with.
  const briefQuality: "weak" | "okay" | "strong" =
    briefLen < MIN_BRIEF_CHARS ? "weak" : briefLen < 500 ? "okay" : "strong";

  // Emit a brief-quality event only on transition (not every keystroke), so
  // the funnel shows users moving from weak → okay → strong rather than a
  // noisy stream of keystrokes. Skip the very first render's "weak" state
  // for users who haven't typed anything — that's just the initial load.
  const lastQualityRef = useRef<"weak" | "okay" | "strong" | null>(null);
  useEffect(() => {
    if (briefLen === 0) {
      lastQualityRef.current = null;
      return;
    }
    if (lastQualityRef.current === briefQuality) return;
    lastQualityRef.current = briefQuality;
    trackProfessionalSearchEvent("professional_search_brief_quality_changed", {
      quality: briefQuality,
      brief_chars: briefLen,
      lang,
    });
  }, [briefQuality, briefLen, lang]);

  const blockers: string[] = [];
  if (!purposeOk) blockers.push(t.blockerPurpose as string);
  if (!briefOk) {
    const remaining = Math.max(0, MIN_BRIEF_CHARS - briefLen);
    blockers.push((t.blockerBrief as (n: number) => string)(remaining));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    trackProfessionalSearchEvent("professional_search_submitted", {
      vertical,
      brief_chars: briefLen,
      brief_quality: briefQuality,
      file_count: files.length,
      has_case_id: Boolean(caseId),
      lang,
    });
    try {
      const row = await startProfessionalSearch({
        case_brief: caseBrief,
        purpose,
        vertical,
        files,
        case_id: caseId,
      });
      router.replace(`/find-lawyer/${row.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      trackProfessionalSearchEvent("professional_search_submission_failed", {
        vertical,
        brief_chars: briefLen,
        message,
        lang,
      });
      setError(message);
      setSubmitting(false);
    }
  }

  const selectedHelper = verticalsLocalized[vertical]?.helper;
  const pageTitle = vocab.isAttorney
    ? (t.pageTitle as string)
    : lang === "zh"
      ? `告诉我们您的情况，我们帮您找到合适的${vocab.orgSingular}。`
      : `Tell us about your needs. We'll find the right ${vocab.orgSingular}.`;
  const pageBlurb = vocab.isAttorney
    ? (t.pageBlurb as string)
    : lang === "zh"
      ? "描述您的情况，并可选择上传相关文件。研究代理将根据所选专业类别并行搜索不同角度，并基于可外部验证的资质与适配度返回排名列表。"
      : `Describe your situation and optionally upload relevant documents. Research agents will search category-specific angles and return a ranked list of ${vocab.orgPlural} scored against externally-verifiable credentials and fit.`;
  const briefHelp = vocab.isAttorney
    ? (t.fieldBriefHelp as string)
    : lang === "zh"
      ? "越具体越好 — 代理会据此判断服务方是否真正适合您的问题。"
      : `The more specific, the better — agents use this to judge whether a ${vocab.orgSingular} fits your exact needs.`;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(91,141,238,0.18),_transparent_32%),linear-gradient(180deg,#edf3f9_0%,#e6eef6_42%,#f4f7fb_100%)] px-4 py-6 sm:px-6 sm:py-10">
      <div className="mx-auto max-w-5xl">
        {/* Mobile: flex-wrap so back + lang + sample-report don't overflow
            on a 390px-wide viewport. Status pill hides below sm — it's
            purely decorative ("Professional search" label) and was the
            element that pushed the row to wrap awkwardly across 3 lines
            with broken-up labels on iOS Safari. */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-2 sm:mb-8 sm:gap-3">
          <button
            type="button"
            onClick={() => router.push("/")}
            className="rounded-full border border-white/80 bg-white/75 px-3 py-1.5 text-[13px] font-medium text-[#52627d] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur transition hover:text-[#1a2036] sm:px-4 sm:py-2 sm:text-sm"
          >
            {t.btnBack as string}
          </button>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <LangToggle
              lang={lang}
              onChange={(next) => {
                if (next !== lang) {
                  trackProfessionalSearchEvent("professional_search_lang_toggled", {
                    surface: "intake",
                    from: lang,
                    to: next,
                  });
                }
                setLang(next);
              }}
            />
            {vocab.isAttorney && (
              <a
                href="/samples/lawyer-search-eb5-sample.pdf"
                target="_blank"
                rel="noopener noreferrer"
                data-testid="find-lawyer-sample-report"
                data-graph-edge="find-lawyer:sample-report"
                className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-[#cfe1ff] bg-[#eaf2ff]/90 px-3 py-1.5 text-[12px] font-semibold text-[#2f5bae] shadow-[0_8px_24px_rgba(91,141,238,0.18)] transition hover:bg-[#dde9fb] hover:text-[#1a2036] sm:px-4 sm:py-2"
                title={lang === "zh" ? "查看示例 PDF 报告" : "Preview a sample PDF report"}
              >
                <svg
                  aria-hidden="true"
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="9" y1="15" x2="15" y2="15" />
                </svg>
                <span className="sm:inline">{lang === "zh" ? "示例报告" : "Sample"}</span>
                <span className="hidden sm:inline">{lang === "zh" ? "" : " report"}</span>
              </a>
            )}
            <div className="hidden rounded-full border border-[#dce6f3] bg-white/80 px-4 py-2 text-[12px] font-semibold uppercase tracking-[0.18em] text-[#6d7c95] shadow-[0_8px_24px_rgba(42,64,102,0.08)] sm:inline-flex">
              {t.statusPagePill as string}
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.15fr,0.85fr]">
          <section className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
            <div className="mb-8 max-w-xl">
              <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
                {t.eyebrow as string}
              </div>
              <h1 className="mt-3 text-[40px] font-extrabold leading-[1.05] tracking-tight text-[#0d1424]">
                {pageTitle}
              </h1>
              <p className="mt-4 text-[16px] leading-7 text-[#556480]">
                {pageBlurb}
              </p>
              {caseId && (
                <div className="mt-5 flex items-start gap-3 rounded-2xl border border-[#dbe5f2] bg-[#eef4fd]/80 px-4 py-3">
                  <div className="mt-0.5 text-[16px]">📎</div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px] font-semibold text-[#0d1424]">
                      {prefillState === "loading"
                        ? "Pre-filling from your case…"
                        : prefillState === "error"
                          ? "Attached to your case"
                          : "Pre-filled from your case"}
                    </div>
                    <div className="mt-0.5 text-[12px] text-[#556480]">
                      Case <span className="font-mono">{caseId.slice(0, 8)}</span>.
                      {prefillState === "ready" && (
                        <> Edit anything below before submitting — the search will save back to this case.</>
                      )}
                      {prefillState === "error" && (
                        <> Couldn&apos;t load your discovery answers, but the search will still attach to the case.</>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => router.push(`/case/${caseId}`)}
                    className="shrink-0 rounded-full border border-white/70 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-[#52627d] hover:text-[#1a2036]"
                  >
                    Back to case
                  </button>
                </div>
              )}
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <label className="block">
                <div className={LABEL}>{t.fieldVertical as string}</div>
                <select
                  value={vertical}
                  onChange={(e) => setVertical(e.target.value)}
                  data-testid="find-lawyer-vertical"
                  className={INPUT}
                >
                  {VERTICAL_KEYS.map((key) => (
                    <option key={key} value={key}>
                      {verticalsLocalized[key].label}
                    </option>
                  ))}
                </select>
                {selectedHelper && (
                  <div className="mt-2 text-[13px] text-[#7b8ba5]">{selectedHelper}</div>
                )}
              </label>

              <label className="block">
                <div className={LABEL}>{t.fieldPurpose as string}</div>
                <input
                  type="text"
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder={t.fieldPurposePlaceholder as string}
                  data-testid="find-lawyer-purpose"
                  className={INPUT}
                />
                <div className="mt-2 text-[13px] text-[#7b8ba5]">
                  {t.fieldPurposeHelp as string}
                </div>
              </label>

              <label className="block">
                <div className={LABEL}>{t.fieldBrief as string}</div>
                <textarea
                  value={caseBrief}
                  onChange={(e) => setCaseBrief(e.target.value)}
                  rows={10}
                  placeholder={t.fieldBriefPlaceholder as string}
                  data-testid="find-lawyer-brief"
                  className={`${INPUT} font-mono leading-relaxed`}
                />
                <div className="mt-2 flex items-baseline justify-between gap-3 text-[13px] text-[#7b8ba5]">
                  <span>{briefHelp}</span>
                  <span
                    className={`shrink-0 font-medium tabular-nums ${
                      briefQuality === "weak"
                        ? "text-[#9c5a1c]"
                        : briefQuality === "okay"
                          ? "text-[#5b8dee]"
                          : "text-[#2f7a45]"
                    }`}
                  >
                    {briefLen} / {MIN_BRIEF_CHARS}
                    {briefQuality === "weak" &&
                      ` · ${(t.briefWeak as string) ?? "needs more detail"}`}
                    {briefQuality === "okay" &&
                      ` · ${(t.briefOkay as string) ?? "okay — more detail = better matches"}`}
                    {briefQuality === "strong" &&
                      ` · ${(t.briefStrong as string) ?? "strong context"}`}
                  </span>
                </div>
              </label>

              <div>
                <div className={LABEL}>{t.fieldFiles as string}</div>
                <label className="block cursor-pointer rounded-2xl border border-dashed border-[#c9d7eb] bg-white/70 px-5 py-6 text-center transition hover:border-[#5b8dee] hover:bg-white/90">
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.md"
                    onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
                    data-testid="find-lawyer-files"
                    className="sr-only"
                  />
                  <div className="text-[14px] font-semibold text-[#40536f]">
                    {files.length > 0
                      ? (t.fieldFilesSelected as (n: number) => string)(files.length)
                      : (t.fieldFilesEmpty as string)}
                  </div>
                  <div className="mt-1 text-[12px] text-[#7b8ba5]">
                    {t.fieldFilesHelp as string}
                  </div>
                </label>
                {files.length > 0 && (
                  <ul className="mt-3 space-y-1 text-[13px] text-[#556480]">
                    {files.map((f) => (
                      <li key={f.name} className="flex justify-between">
                        <span>{f.name}</span>
                        <span className="text-[#7b8ba5]">
                          {Math.round(f.size / 1024)} KB
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {error && (
                <div className="rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
                  {error}
                </div>
              )}

              <div className="flex items-center justify-between gap-4 pt-2">
                <div className="text-[12px] leading-5 text-[#7b8ba5]">
                  {blockers.length > 0 ? (
                    <>
                      <span className="font-semibold text-[#9c5a1c]">
                        {t.blockerLead as string}
                      </span>{" "}
                      {blockers.join(" · ")}
                    </>
                  ) : (
                    <span className="text-[#2f7a45]">
                      {vocab.isAttorney
                        ? (t.ready as string)
                        : lang === "zh"
                          ? "准备就绪，将并行调度研究代理。"
                          : "Ready to dispatch research agents in parallel."}
                    </span>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={!canSubmit}
                  data-testid="find-lawyer-submit"
                  className={canSubmit ? PRIMARY_BTN : DISABLED_BTN}
                >
                  {submitting ? (t.btnStarting as string) : (t.btnStart as string)}
                </button>
              </div>
            </form>
          </section>

          <aside className="space-y-6">
            <div className="rounded-[32px] border border-white/70 bg-[#f8fbff]/78 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
              <div className="rounded-[28px] bg-[#0f1728] p-6 text-white shadow-[0_22px_50px_rgba(9,18,36,0.24)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8ca2cc]">
                  {t.asideHowTitle as string}
                </div>
                <div className="mt-3 text-[22px] font-bold leading-tight">
                  {t.asideHowSub as string}
                </div>
                <p className="mt-3 text-[14px] leading-6 text-[#b8c5de]">
                  {t.asideHowBlurb as string}
                </p>
              </div>

              <div className="mt-6 space-y-4">
                {personaPreviewsFor(lang, vertical).map((item, i) => (
                  <div
                    key={`${vertical}-${i}-${item.title}`}
                    className="rounded-2xl border border-[#e4edf7] bg-white/82 p-4 shadow-[0_10px_30px_rgba(61,84,128,0.05)]"
                  >
                    <div className="flex items-baseline gap-3">
                      <span className="text-[12px] font-semibold text-[#5b8dee]">
                        0{i + 1}
                      </span>
                      <span className="text-[15px] font-semibold text-[#0d1424]">
                        {item.title}
                      </span>
                    </div>
                    <p className="mt-1 text-[13px] leading-6 text-[#556480]">
                      {item.body}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-6 rounded-[20px] border border-dashed border-[#c9d7eb] bg-white/70 p-4">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">
                  {t.asideStdTitle as string}
                </div>
                <p className="mt-2 text-[13px] leading-6 text-[#556480]">
                  {t.asideStdBody as string}
                </p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
