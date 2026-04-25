"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Case,
  getCase,
  listCaseSearches,
  ProfessionalSearchSummary,
} from "@/lib/api";

export default function CaseOverview() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [searches, setSearches] = useState<ProfessionalSearchSummary[] | null>(null);

  useEffect(() => {
    getCase(caseId).then(setCaseData);
    listCaseSearches(caseId)
      .then(setSearches)
      .catch(() => setSearches([]));
  }, [caseId]);

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

      <LawyersSection caseId={caseId} searches={searches} router={router} />

      <p className="text-sm text-stone-400 text-center">Review dashboard coming soon.</p>
    </div>
  );
}


function LawyersSection({
  caseId,
  searches,
  router,
}: {
  caseId: string;
  searches: ProfessionalSearchSummary[] | null;
  router: ReturnType<typeof useRouter>;
}) {
  const launch = () => router.push(`/find-lawyer?case_id=${caseId}`);

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
            <li key={s.id}>
              <button
                onClick={() => router.push(`/find-lawyer/${s.id}`)}
                className="w-full text-left py-3 hover:bg-stone-50 px-2 -mx-2 rounded-md transition-colors"
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
                    {s.top_firms.length > 0 && (
                      <div className="text-xs text-stone-600 mt-1 truncate">
                        Top:{" "}
                        {s.top_firms
                          .map((f) =>
                            f.confidence != null ? `${f.name} (${f.confidence})` : f.name,
                          )
                          .join(" · ")}
                      </div>
                    )}
                  </div>
                  <span className="text-stone-300 text-sm">→</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
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


function fmtDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
