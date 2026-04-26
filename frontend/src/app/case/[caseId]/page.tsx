"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Case,
  createEngagement,
  deleteEngagement,
  disconnectGmail,
  EmailThread,
  Engagement,
  ENGAGEMENT_STATUSES,
  EngagementStatus,
  getCase,
  getEngagementDraftEmail,
  getGmailConnectUrl,
  getGmailStatus,
  GmailStatus,
  listCaseEngagements,
  listCaseSearches,
  listEngagementThreads,
  ProfessionalSearchSummary,
  syncGmail,
  updateEngagement,
} from "@/lib/api";

export default function CaseOverview() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [caseError, setCaseError] = useState<string | null>(null);
  const [searches, setSearches] = useState<ProfessionalSearchSummary[] | null>(null);
  const [engagements, setEngagements] = useState<Engagement[] | null>(null);
  // Bumped after every successful Gmail sync — child components watch
  // it to refresh their thread lists. Avoids lifting per-engagement
  // thread state into the parent.
  const [syncTick, setSyncTick] = useState(0);

  useEffect(() => {
    setCaseError(null);
    getCase(caseId)
      .then(setCaseData)
      .catch((err) => {
        // Most common failure: case is owned by another user (404 to
        // avoid leaking existence). Without this catch the page sits
        // on "Loading..." forever.
        setCaseError(err instanceof Error ? err.message : String(err));
      });
    listCaseSearches(caseId)
      .then(setSearches)
      .catch(() => setSearches([]));
    listCaseEngagements(caseId)
      .then(setEngagements)
      .catch(() => setEngagements([]));
  }, [caseId]);

  async function refreshEngagements() {
    const fresh = await listCaseEngagements(caseId).catch(() => []);
    setEngagements(fresh);
  }

  async function handleSynced() {
    // After Gmail sync, engagement.last_activity_at may have moved; refresh.
    await refreshEngagements();
    setSyncTick((t) => t + 1);
  }

  if (caseError) {
    return (
      <div className="mx-auto max-w-md px-4 md:px-8 py-16 text-center space-y-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
          404
        </div>
        <h2 className="text-[24px] font-bold tracking-tight text-[#0d1424]">
          Case not available
        </h2>
        <p className="text-[14px] leading-7 text-[#556480]">
          This case either doesn&apos;t exist or belongs to a different account.
          If you signed up with a different email, sign in there to access it.
        </p>
        <p className="text-[12px] text-[#7b8ba5] font-mono">case {caseId.slice(0, 8)}</p>
        <div className="flex justify-center gap-3 pt-2">
          <button
            onClick={() => router.push("/dashboard")}
            className="rounded-full bg-[#5b8dee] px-5 py-2.5 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de]"
          >
            Go to dashboard
          </button>
          <button
            onClick={() => router.push("/")}
            className="rounded-full border border-[#dbe5f2] px-5 py-2.5 text-[13px] font-semibold text-[#40536f] hover:bg-[#f7f9fd]"
          >
            Home
          </button>
        </div>
      </div>
    );
  }
  if (!caseData) return <p className="text-[12px] text-[#7b8ba5] text-center py-16 px-4">Loading…</p>;

  const workflowLabel = caseData.workflow_type
    ? caseData.workflow_type.charAt(0).toUpperCase() + caseData.workflow_type.slice(1)
    : "Case";

  return (
    <div className="mx-auto max-w-[900px] px-4 md:px-8 py-6 md:py-8 space-y-6">
      {/* Minimal header — case page is tracking-focused; full case
          metrics live on the dashboard. Just a breadcrumb for
          orientation + a back-to-dashboard link. */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <span className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#40536f]">
            {workflowLabel}
          </span>
          <span className="text-[12px] font-mono text-[#9ba8c4]">
            case {caseId.slice(0, 8)}
          </span>
        </div>
        <button
          onClick={() => router.push("/dashboard")}
          className="text-[12px] font-medium text-[#5b8dee] hover:text-[#2f5bae]"
        >
          ← Dashboard
        </button>
      </div>

      <LawyersSection
        caseId={caseId}
        searches={searches}
        engagements={engagements ?? []}
        router={router}
        onTracked={refreshEngagements}
      />

      <EngagementsSection
        caseId={caseId}
        engagements={engagements}
        onChange={refreshEngagements}
        syncTick={syncTick}
      />

      <GmailConnectionSection caseId={caseId} onSynced={handleSynced} />
    </div>
  );
}


function LawyersSection({
  caseId,
  searches,
  engagements,
  router,
  onTracked,
}: {
  caseId: string;
  searches: ProfessionalSearchSummary[] | null;
  engagements: Engagement[];
  router: ReturnType<typeof useRouter>;
  onTracked: () => void | Promise<void>;
}) {
  const launch = () => router.push(`/find-lawyer?case_id=${caseId}`);
  const trackedNames = new Set(engagements.map((e) => e.firm_name.toLowerCase()));

  async function trackFirm(searchId: string, firmName: string) {
    try {
      await createEngagement(caseId, {
        firm_name: firmName,
        search_id: searchId,
      });
      await onTracked();
    } catch (err) {
      console.error("track failed", err);
    }
  }

  return (
    <div className="overflow-hidden rounded-[28px] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.78),rgba(234,241,251,0.92))] backdrop-blur-xl shadow-[0_10px_36px_rgba(91,141,238,0.08)] p-5 md:p-7 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[16px] font-bold text-[#0d1424] tracking-tight">Lawyers</h3>
          <p className="text-xs text-[#556480] mt-0.5">
            Search results stay attached to this case so you can come back to them.
          </p>
        </div>
        {searches && searches.length > 0 && (
          <button
            onClick={launch}
            className="rounded-lg border border-[#dbe5f2] px-3 py-1.5 text-xs font-medium text-[#1a2036] hover:bg-[#f7f9fd]"
          >
            New search
          </button>
        )}
      </div>

      {searches === null ? (
        <p className="text-sm text-[#7b8ba5]">Loading searches…</p>
      ) : searches.length === 0 ? (
        <div className="rounded-md border border-dashed border-[#dbe5f2] bg-[#f7f9fd] p-5 text-center">
          <p className="text-sm text-[#40536f]">
            No professional searches yet for this case.
          </p>
          <button
            onClick={launch}
            className="mt-3 rounded-lg bg-[#0d1424] px-5 py-2 text-sm font-medium text-white hover:bg-[#1a2036]"
          >
            Find a specialist for this case
          </button>
          <p className="mt-2 text-[11px] text-[#7b8ba5]">
            Pre-filled from your discovery answers — you can edit before submitting.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-[#eef2f8]">
          {searches.map((s) => (
            <li key={s.id} className="py-3">
              <button
                onClick={() => router.push(`/find-lawyer/${s.id}`)}
                className="w-full text-left hover:bg-[#f7f9fd] px-2 -mx-2 rounded-md transition-colors"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-[#0d1424] truncate">
                        {s.purpose}
                      </span>
                      <StatusPill status={s.status} paid={!!s.paid_at} />
                    </div>
                    <div className="text-xs text-[#556480] mt-0.5">
                      {s.vertical.replace(/_/g, " ")} · {fmtDate(s.created_at)}
                      {s.firm_count > 0 && ` · ${s.firm_count} firm${s.firm_count === 1 ? "" : "s"}`}
                    </div>
                  </div>
                  <span className="text-[#9ba8c4] text-sm">→</span>
                </div>
              </button>
              {s.top_firms.length > 0 && (
                <ul className="mt-2 ml-2 space-y-1">
                  {s.top_firms.map((f) => {
                    const isTracked = trackedNames.has(f.name.toLowerCase());
                    return (
                      <li
                        key={f.name}
                        className="flex items-center justify-between gap-2 text-xs text-[#40536f]"
                      >
                        <span className="truncate">
                          {f.name}
                          {f.confidence != null && (
                            <span className="text-[#7b8ba5]"> ({f.confidence})</span>
                          )}
                        </span>
                        {isTracked ? (
                          <span className="shrink-0 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
                            tracking
                          </span>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              trackFirm(s.id, f.name);
                            }}
                            className="shrink-0 rounded-full border border-[#dbe5f2] px-2 py-0.5 text-[10px] font-medium text-[#40536f] hover:bg-[#eef2f8] hover:text-[#0d1424]"
                          >
                            + track
                          </button>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


function EngagementsSection({
  caseId,
  engagements,
  onChange,
  syncTick,
}: {
  caseId: string;
  engagements: Engagement[] | null;
  onChange: () => void | Promise<void>;
  syncTick: number;
}) {
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");

  async function handleAdd() {
    const name = newName.trim();
    if (!name) return;
    try {
      await createEngagement(caseId, { firm_name: name });
      setNewName("");
      setAdding(false);
      await onChange();
    } catch (err) {
      console.error("add engagement failed", err);
    }
  }

  return (
    <div className="overflow-hidden rounded-[28px] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.78),rgba(234,241,251,0.92))] backdrop-blur-xl shadow-[0_10px_36px_rgba(91,141,238,0.08)] p-5 md:p-7 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[16px] font-bold text-[#0d1424] tracking-tight">Engagements</h3>
          <p className="text-xs text-[#556480] mt-0.5">
            Track your outreach, status, and notes for each firm you&apos;re working with.
          </p>
        </div>
        {!adding && (
          <button
            onClick={() => setAdding(true)}
            className="rounded-lg border border-[#dbe5f2] px-3 py-1.5 text-xs font-medium text-[#1a2036] hover:bg-[#f7f9fd]"
          >
            + Add firm
          </button>
        )}
      </div>

      {adding && (
        <div className="flex items-center gap-2">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAdd();
              if (e.key === "Escape") {
                setAdding(false);
                setNewName("");
              }
            }}
            placeholder="Firm name"
            className="flex-1 rounded-md border border-[#dbe5f2] px-3 py-1.5 text-sm focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
          />
          <button
            onClick={handleAdd}
            className="rounded-md bg-[#0d1424] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#1a2036]"
          >
            Add
          </button>
          <button
            onClick={() => {
              setAdding(false);
              setNewName("");
            }}
            className="text-sm text-[#556480] hover:text-[#1a2036]"
          >
            Cancel
          </button>
        </div>
      )}

      {engagements === null ? (
        <p className="text-sm text-[#7b8ba5]">Loading…</p>
      ) : engagements.length === 0 ? (
        <p className="text-sm text-[#7b8ba5] text-center py-4">
          No firms tracked yet. Click <span className="font-mono">+ track</span> on a firm above, or use <span className="font-mono">+ Add firm</span> for one not in your search results.
        </p>
      ) : (
        <ul className="divide-y divide-[#eef2f8]">
          {engagements.map((e) => (
            <EngagementRow
              key={e.id}
              caseId={caseId}
              engagement={e}
              onChange={onChange}
              syncTick={syncTick}
            />
          ))}
        </ul>
      )}
    </div>
  );
}


function EngagementRow({
  caseId,
  engagement,
  onChange,
  syncTick,
}: {
  caseId: string;
  engagement: Engagement;
  onChange: () => void | Promise<void>;
  syncTick: number;
}) {
  const [threads, setThreads] = useState<EmailThread[]>([]);
  const [emailsDraft, setEmailsDraft] = useState(engagement.firm_emails.join(", "));
  const [editingEmails, setEditingEmails] = useState(false);

  useEffect(() => {
    listEngagementThreads(caseId, engagement.id)
      .then(setThreads)
      .catch(() => setThreads([]));
  }, [caseId, engagement.id, syncTick]);

  async function saveEmails() {
    const list = emailsDraft
      .split(/[,;\n]/)
      .map((s) => s.trim())
      .filter(Boolean);
    setBusy(true);
    try {
      await updateEngagement(caseId, engagement.id, { firm_emails: list });
      setEditingEmails(false);
      await onChange();
    } finally {
      setBusy(false);
    }
  }

  const [notesDraft, setNotesDraft] = useState(engagement.notes || "");
  const [editingNotes, setEditingNotes] = useState(false);
  const [busy, setBusy] = useState(false);

  async function setStatus(status: EngagementStatus) {
    setBusy(true);
    try {
      await updateEngagement(caseId, engagement.id, { status });
      await onChange();
    } finally {
      setBusy(false);
    }
  }

  async function saveNotes() {
    setBusy(true);
    try {
      await updateEngagement(caseId, engagement.id, { notes: notesDraft });
      setEditingNotes(false);
      await onChange();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`Remove ${engagement.firm_name} from this case?`)) return;
    setBusy(true);
    try {
      await deleteEngagement(caseId, engagement.id);
      await onChange();
    } finally {
      setBusy(false);
    }
  }

  async function emailFirm() {
    setBusy(true);
    try {
      const draft = await getEngagementDraftEmail(caseId, engagement.id);
      // mailto: requires URI-encoded params; multiple "to" addrs joined by comma.
      const to = draft.to.length > 0 ? draft.to.join(",") : "";
      const url = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(
        draft.subject,
      )}&body=${encodeURIComponent(draft.body)}`;
      // Open in a new tab so the page state is preserved if the mail client
      // hijacks the navigation.
      window.open(url, "_blank");
      // Auto-bump status to outreach_sent on first contact (don't downgrade
      // if user already moved further along the funnel).
      if (engagement.status === "not_contacted") {
        await updateEngagement(caseId, engagement.id, { status: "outreach_sent" });
        await onChange();
      }
    } catch (err) {
      console.error("draft email failed", err);
      alert("Couldn't draft the email — see console for details.");
    } finally {
      setBusy(false);
    }
  }

  const canEmail = engagement.firm_emails.length > 0;

  const fmtThreadDate = (iso: string) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };

  return (
    <li className="py-3 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-[#0d1424] truncate">
              {engagement.firm_name}
            </span>
            <EngagementStatusPill status={engagement.status} />
          </div>
          <div className="text-[11px] text-[#7b8ba5] mt-0.5">
            Last activity {fmtDate(engagement.last_activity_at)}
            {engagement.firm_lead_attorney && ` · ${engagement.firm_lead_attorney}`}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={emailFirm}
            disabled={busy || !canEmail}
            title={canEmail ? "Open pre-filled email" : "No email on file for this firm"}
            className="rounded-md border border-[#dbe5f2] px-2 py-1 text-xs font-medium text-[#1a2036] hover:bg-[#f7f9fd] disabled:cursor-not-allowed disabled:opacity-50"
          >
            ✉ Email
          </button>
          <select
            disabled={busy}
            value={engagement.status}
            onChange={(e) => setStatus(e.target.value as EngagementStatus)}
            className="text-xs rounded-md border border-[#dbe5f2] px-2 py-1 bg-white hover:border-[#7b8ba5] focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            {ENGAGEMENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
          <button
            onClick={remove}
            disabled={busy}
            className="text-[11px] text-[#7b8ba5] hover:text-rose-600 px-1"
            title="Remove from case"
          >
            ✕
          </button>
        </div>
      </div>

      {/* firm emails (used by Gmail sync to match threads) */}
      {editingEmails ? (
        <div className="flex items-center gap-2">
          <input
            autoFocus
            value={emailsDraft}
            onChange={(e) => setEmailsDraft(e.target.value)}
            placeholder="email1@firm.com, email2@firm.com"
            className="flex-1 rounded-md border border-[#dbe5f2] px-2 py-1 text-xs focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
          />
          <button
            onClick={saveEmails}
            disabled={busy}
            className="rounded-md bg-[#0d1424] px-2 py-1 text-[11px] font-medium text-white hover:bg-[#1a2036]"
          >
            Save
          </button>
          <button
            onClick={() => {
              setEditingEmails(false);
              setEmailsDraft(engagement.firm_emails.join(", "));
            }}
            className="text-[11px] text-[#556480] hover:text-[#1a2036]"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setEditingEmails(true)}
          className="block text-[11px] text-[#556480] hover:text-[#1a2036]"
        >
          {engagement.firm_emails.length > 0
            ? `📧 ${engagement.firm_emails.join(", ")}`
            : "+ add firm emails (for Gmail matching)"}
        </button>
      )}

      {editingNotes ? (
        <div className="space-y-1">
          <textarea
            autoFocus
            value={notesDraft}
            onChange={(e) => setNotesDraft(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-[#dbe5f2] px-3 py-2 text-xs focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
            placeholder="Notes — last contact, key points, next step…"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => {
                setEditingNotes(false);
                setNotesDraft(engagement.notes || "");
              }}
              className="text-xs text-[#556480] hover:text-[#1a2036]"
            >
              Cancel
            </button>
            <button
              onClick={saveNotes}
              disabled={busy}
              className="rounded-md bg-[#0d1424] px-3 py-1 text-xs font-medium text-white hover:bg-[#1a2036]"
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setEditingNotes(true)}
          className="block w-full text-left text-xs text-[#556480] hover:text-[#1a2036] italic"
        >
          {engagement.notes || "+ add notes"}
        </button>
      )}

      {threads.length > 0 && (
        <div className="mt-2 space-y-1.5 border-l-2 border-blue-100 pl-3">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-[#7b8ba5]">
            {threads.length} email thread{threads.length === 1 ? "" : "s"}
          </div>
          {threads.slice(0, 5).map((t) => (
            <a
              key={t.id}
              href={`https://mail.google.com/mail/u/0/#all/${t.gmail_thread_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-xs hover:bg-[#f7f9fd] -mx-1 px-1 py-0.5 rounded transition-colors"
              title="Open thread in Gmail"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-medium text-[#1a2036] truncate">
                  {t.subject || "(no subject)"}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span
                    className={`inline-block rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${
                      t.last_message_direction === "inbound"
                        ? "bg-blue-50 text-blue-600 border border-blue-200"
                        : "bg-[#f7f9fd] text-[#556480] border border-[#e4edf7]"
                    }`}
                  >
                    {t.last_message_direction === "inbound" ? "← in" : "out →"}
                  </span>
                  <span className="text-[10px] text-[#7b8ba5]">
                    {t.message_count > 1 && `${t.message_count} · `}
                    {fmtThreadDate(t.last_message_at)}
                  </span>
                  <span className="text-[10px] text-[#9ba8c4]">↗</span>
                </div>
              </div>
              <div className="text-[11px] text-[#556480] line-clamp-1">
                {t.last_message_snippet}
              </div>
            </a>
          ))}
          {threads.length > 5 && (
            <div className="text-[10px] text-[#7b8ba5]">
              + {threads.length - 5} more
            </div>
          )}
        </div>
      )}
    </li>
  );
}


function GmailConnectionSection({
  caseId,
  onSynced,
}: {
  caseId: string;
  onSynced: () => void | Promise<void>;
}) {
  const [status, setStatus] = useState<GmailStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  useEffect(() => {
    getGmailStatus().then(setStatus).catch(() => setStatus({ connected: false }));
  }, []);

  // On case page load, trigger a debounced sync if Gmail is connected.
  // The backend skips if synced within the last 2 min, so this is cheap.
  useEffect(() => {
    if (status?.connected) {
      void doSync(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.connected]);

  // Surface OAuth callback result (?gmail=connected | error_code) as a one-time pill.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const gmail = params.get("gmail");
    if (!gmail) return;
    if (gmail === "connected") {
      getGmailStatus().then(setStatus);
    } else {
      setError(`Gmail connection failed: ${gmail.replace(/_/g, " ")}`);
    }
    params.delete("gmail");
    const newSearch = params.toString();
    window.history.replaceState(
      {},
      "",
      window.location.pathname + (newSearch ? `?${newSearch}` : ""),
    );
  }, []);

  async function doSync(force: boolean) {
    setSyncing(true);
    setError(null);
    try {
      const result = await syncGmail(force);
      if (result.skipped) {
        setLastResult(`Synced recently — skipped (last: ${fmtRel(result.last_synced_at)})`);
      } else {
        const matched = result.threads_matched ?? 0;
        const newish = result.threads_new ?? 0;
        setLastResult(
          newish > 0
            ? `Synced — ${newish} new thread${newish === 1 ? "" : "s"}, ${matched} matched`
            : matched > 0
              ? `Synced — ${matched} thread${matched === 1 ? "" : "s"} updated`
              : `Synced — no new email matches`,
        );
        await onSynced();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSyncing(false);
    }
  }

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const { url } = await getGmailConnectUrl(`/case/${caseId}`);
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  async function disconnect() {
    if (!confirm("Disconnect Gmail? Synced threads will stop updating.")) return;
    setBusy(true);
    setError(null);
    try {
      await disconnectGmail();
      setStatus({ connected: false });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (status === null) return null;

  return (
    <div className="overflow-hidden rounded-[28px] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.78),rgba(234,241,251,0.92))] backdrop-blur-xl shadow-[0_10px_36px_rgba(91,141,238,0.08)] p-5 md:p-7 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[16px] font-bold text-[#0d1424] tracking-tight">Gmail</span>
            {status.connected ? (
              <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
                connected
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full border border-[#e4edf7] bg-[#f7f9fd] text-[#556480] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
                not connected
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-[#556480]">
            {status.connected
              ? "We'll match incoming and outgoing emails to firms in your engagements list."
              : "Connect Gmail to automatically track email threads with each firm. Read-only — we never send on your behalf."}
          </p>
          {status.connected && status.granted_at && (
            <p className="mt-0.5 text-[11px] text-[#7b8ba5]">
              Granted {new Date(status.granted_at).toLocaleDateString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {status.connected && (
            <button
              onClick={() => doSync(true)}
              disabled={syncing || busy}
              className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
            >
              {syncing ? "Syncing…" : "Sync now"}
            </button>
          )}
          {status.connected ? (
            <button
              onClick={disconnect}
              disabled={busy}
              className="rounded-lg border border-[#dbe5f2] px-3 py-1.5 text-xs font-medium text-[#40536f] hover:bg-[#f7f9fd] hover:text-rose-600"
            >
              Disconnect
            </button>
          ) : (
            <button
              onClick={connect}
              disabled={busy}
              className="rounded-lg bg-[#0d1424] px-4 py-1.5 text-xs font-medium text-white hover:bg-[#1a2036] disabled:opacity-50"
            >
              {busy ? "…" : "Connect Gmail"}
            </button>
          )}
        </div>
      </div>
      {lastResult && (
        <div className="text-[11px] text-[#556480]">{lastResult}</div>
      )}
      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {error}
        </div>
      )}
    </div>
  );
}


function fmtRel(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const ms = Date.now() - d.getTime();
  const min = Math.round(ms / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return d.toLocaleDateString();
}


function StatusPill({ status, paid }: { status: string; paid: boolean }) {
  const map: Record<string, string> = {
    queued: "bg-[#eef2f8] text-[#40536f] border-[#e4edf7]",
    running: "bg-blue-50 text-blue-700 border-blue-200",
    complete: paid
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : "bg-amber-50 text-amber-700 border-amber-200",
    failed: "bg-rose-50 text-rose-700 border-rose-200",
  };
  const label =
    status === "complete" && !paid ? "ready · unlock" : status;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
        map[status] || map.queued
      }`}
    >
      {label}
    </span>
  );
}


function EngagementStatusPill({ status }: { status: EngagementStatus }) {
  const map: Record<EngagementStatus, string> = {
    not_contacted: "bg-[#eef2f8] text-[#40536f] border-[#e4edf7]",
    outreach_sent: "bg-blue-50 text-blue-700 border-blue-200",
    in_discussion: "bg-violet-50 text-violet-700 border-violet-200",
    engaged: "bg-emerald-50 text-emerald-700 border-emerald-200",
    declined: "bg-[#f7f9fd] text-[#7b8ba5] border-[#e4edf7]",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${map[status]}`}
    >
      {statusLabel(status)}
    </span>
  );
}


function statusLabel(status: EngagementStatus): string {
  return {
    not_contacted: "not contacted",
    outreach_sent: "outreach sent",
    in_discussion: "in discussion",
    engaged: "engaged",
    declined: "declined",
  }[status];
}


function fmtDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
