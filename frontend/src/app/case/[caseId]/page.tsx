"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Case,
  createEngagement,
  deleteEngagement,
  Engagement,
  ENGAGEMENT_STATUSES,
  EngagementStatus,
  getCase,
  getEngagementDraftEmail,
  listCaseEngagements,
  listCaseSearches,
  ProfessionalSearchSummary,
  updateEngagement,
} from "@/lib/api";

export default function CaseOverview() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [searches, setSearches] = useState<ProfessionalSearchSummary[] | null>(null);
  const [engagements, setEngagements] = useState<Engagement[] | null>(null);

  useEffect(() => {
    getCase(caseId).then(setCaseData);
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

  if (!caseData) return <p className="text-stone-400">Loading...</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Case Overview</h2>
      <div className="rounded-lg border border-stone-200 bg-white p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-stone-500">Status:</span> <span className="capitalize">{caseData.status}</span></div>
          <div><span className="text-stone-500">Type:</span> <span className="capitalize">{caseData.workflow_type || "General"}</span></div>
          <div><span className="text-stone-500">Answers:</span> {caseData.answer_count}</div>
          <div><span className="text-stone-500">Documents:</span> {caseData.document_count}</div>
        </div>
        <div className="flex gap-3 pt-2">
          <button
            onClick={() => router.push(`/case/${caseId}/discovery`)}
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm hover:bg-stone-50"
          >
            Discovery
          </button>
          <button
            onClick={() => router.push(`/case/${caseId}/documents`)}
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm hover:bg-stone-50"
          >
            Documents
          </button>
        </div>
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
      />

      <p className="text-sm text-stone-400 text-center">Review dashboard coming soon.</p>
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
    <div className="rounded-lg border border-stone-200 bg-white p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-stone-800">Lawyers</h3>
          <p className="text-xs text-stone-500 mt-0.5">
            Search results stay attached to this case so you can come back to them.
          </p>
        </div>
        {searches && searches.length > 0 && (
          <button
            onClick={launch}
            className="rounded-lg border border-stone-300 px-3 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50"
          >
            New search
          </button>
        )}
      </div>

      {searches === null ? (
        <p className="text-sm text-stone-400">Loading searches…</p>
      ) : searches.length === 0 ? (
        <div className="rounded-md border border-dashed border-stone-300 bg-stone-50 p-5 text-center">
          <p className="text-sm text-stone-600">
            No professional searches yet for this case.
          </p>
          <button
            onClick={launch}
            className="mt-3 rounded-lg bg-stone-800 px-5 py-2 text-sm font-medium text-white hover:bg-stone-700"
          >
            Find a specialist for this case
          </button>
          <p className="mt-2 text-[11px] text-stone-400">
            Pre-filled from your discovery answers — you can edit before submitting.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-stone-100">
          {searches.map((s) => (
            <li key={s.id} className="py-3">
              <button
                onClick={() => router.push(`/find-lawyer/${s.id}`)}
                className="w-full text-left hover:bg-stone-50 px-2 -mx-2 rounded-md transition-colors"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-stone-800 truncate">
                        {s.purpose}
                      </span>
                      <StatusPill status={s.status} paid={!!s.paid_at} />
                    </div>
                    <div className="text-xs text-stone-500 mt-0.5">
                      {s.vertical.replace(/_/g, " ")} · {fmtDate(s.created_at)}
                      {s.firm_count > 0 && ` · ${s.firm_count} firm${s.firm_count === 1 ? "" : "s"}`}
                    </div>
                  </div>
                  <span className="text-stone-300 text-sm">→</span>
                </div>
              </button>
              {s.top_firms.length > 0 && (
                <ul className="mt-2 ml-2 space-y-1">
                  {s.top_firms.map((f) => {
                    const isTracked = trackedNames.has(f.name.toLowerCase());
                    return (
                      <li
                        key={f.name}
                        className="flex items-center justify-between gap-2 text-xs text-stone-600"
                      >
                        <span className="truncate">
                          {f.name}
                          {f.confidence != null && (
                            <span className="text-stone-400"> ({f.confidence})</span>
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
                            className="shrink-0 rounded-full border border-stone-300 px-2 py-0.5 text-[10px] font-medium text-stone-600 hover:bg-stone-100 hover:text-stone-800"
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
}: {
  caseId: string;
  engagements: Engagement[] | null;
  onChange: () => void | Promise<void>;
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
    <div className="rounded-lg border border-stone-200 bg-white p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-stone-800">Engagements</h3>
          <p className="text-xs text-stone-500 mt-0.5">
            Track your outreach, status, and notes for each firm you&apos;re working with.
          </p>
        </div>
        {!adding && (
          <button
            onClick={() => setAdding(true)}
            className="rounded-lg border border-stone-300 px-3 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50"
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
            className="flex-1 rounded-md border border-stone-300 px-3 py-1.5 text-sm focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
          />
          <button
            onClick={handleAdd}
            className="rounded-md bg-stone-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-700"
          >
            Add
          </button>
          <button
            onClick={() => {
              setAdding(false);
              setNewName("");
            }}
            className="text-sm text-stone-500 hover:text-stone-700"
          >
            Cancel
          </button>
        </div>
      )}

      {engagements === null ? (
        <p className="text-sm text-stone-400">Loading…</p>
      ) : engagements.length === 0 ? (
        <p className="text-sm text-stone-400 text-center py-4">
          No firms tracked yet. Click <span className="font-mono">+ track</span> on a firm above, or use <span className="font-mono">+ Add firm</span> for one not in your search results.
        </p>
      ) : (
        <ul className="divide-y divide-stone-100">
          {engagements.map((e) => (
            <EngagementRow key={e.id} caseId={caseId} engagement={e} onChange={onChange} />
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
}: {
  caseId: string;
  engagement: Engagement;
  onChange: () => void | Promise<void>;
}) {
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

  return (
    <li className="py-3 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-stone-800 truncate">
              {engagement.firm_name}
            </span>
            <EngagementStatusPill status={engagement.status} />
          </div>
          <div className="text-[11px] text-stone-400 mt-0.5">
            Last activity {fmtDate(engagement.last_activity_at)}
            {engagement.firm_lead_attorney && ` · ${engagement.firm_lead_attorney}`}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={emailFirm}
            disabled={busy || !canEmail}
            title={canEmail ? "Open pre-filled email" : "No email on file for this firm"}
            className="rounded-md border border-stone-300 px-2 py-1 text-xs font-medium text-stone-700 hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            ✉ Email
          </button>
          <select
            disabled={busy}
            value={engagement.status}
            onChange={(e) => setStatus(e.target.value as EngagementStatus)}
            className="text-xs rounded-md border border-stone-300 px-2 py-1 bg-white hover:border-stone-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
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
            className="text-[11px] text-stone-400 hover:text-rose-600 px-1"
            title="Remove from case"
          >
            ✕
          </button>
        </div>
      </div>

      {editingNotes ? (
        <div className="space-y-1">
          <textarea
            autoFocus
            value={notesDraft}
            onChange={(e) => setNotesDraft(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-stone-300 px-3 py-2 text-xs focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
            placeholder="Notes — last contact, key points, next step…"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => {
                setEditingNotes(false);
                setNotesDraft(engagement.notes || "");
              }}
              className="text-xs text-stone-500 hover:text-stone-700"
            >
              Cancel
            </button>
            <button
              onClick={saveNotes}
              disabled={busy}
              className="rounded-md bg-stone-800 px-3 py-1 text-xs font-medium text-white hover:bg-stone-700"
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setEditingNotes(true)}
          className="block w-full text-left text-xs text-stone-500 hover:text-stone-700 italic"
        >
          {engagement.notes || "+ add notes"}
        </button>
      )}
    </li>
  );
}


function StatusPill({ status, paid }: { status: string; paid: boolean }) {
  const map: Record<string, string> = {
    queued: "bg-stone-100 text-stone-600 border-stone-200",
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
    not_contacted: "bg-stone-100 text-stone-600 border-stone-200",
    outreach_sent: "bg-blue-50 text-blue-700 border-blue-200",
    in_discussion: "bg-violet-50 text-violet-700 border-violet-200",
    engaged: "bg-emerald-50 text-emerald-700 border-emerald-200",
    declined: "bg-stone-50 text-stone-400 border-stone-200",
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
