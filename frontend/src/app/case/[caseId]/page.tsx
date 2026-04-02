"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Case, getCase } from "@/lib/api";

export default function CaseOverview() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const [caseData, setCaseData] = useState<Case | null>(null);

  useEffect(() => {
    getCase(caseId).then(setCaseData);
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
      <p className="text-sm text-stone-400 text-center">Review dashboard coming soon.</p>
    </div>
  );
}
