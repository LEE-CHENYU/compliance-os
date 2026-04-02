"use client";

import { useParams, useRouter } from "next/navigation";
import { useUpload } from "@/components/upload/useUpload";
import DocumentChecklist from "@/components/upload/DocumentChecklist";
import GeneralUploadZone from "@/components/upload/GeneralUploadZone";
import DocumentRow from "@/components/upload/DocumentRow";

export default function DocumentsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const upload = useUpload(caseId);

  if (upload.loading) return <p className="text-stone-400 text-center py-20">Loading...</p>;

  const unslottedDocs = upload.documents.filter((d) => !d.slot_key);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Document Data Room</h2>
          <p className="text-sm text-stone-500 mt-1">
            Upload the documents needed for your review.
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium">
            {upload.completionCount} of {upload.totalRequired} required
          </p>
          <div className="w-32 h-2 bg-stone-200 rounded-full mt-1">
            <div
              className="h-2 bg-stone-800 rounded-full transition-all"
              style={{ width: `${upload.totalRequired ? (upload.completionCount / upload.totalRequired) * 100 : 0}%` }}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Checklist — left 60% */}
        <div className="lg:col-span-3">
          <DocumentChecklist
            slots={upload.slots}
            filled={upload.filled}
            documents={upload.documents}
            uploading={upload.uploading}
            onUpload={upload.upload}
            onRemove={upload.remove}
          />
        </div>

        {/* Uploads — right 40% */}
        <div className="lg:col-span-2 space-y-6">
          <GeneralUploadZone
            uploading={upload.uploading === "general"}
            onDrop={(file) => upload.upload(file)}
          />

          {unslottedDocs.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide">Unassigned Files</h3>
              <div className="space-y-2">
                {unslottedDocs.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    doc={doc}
                    slots={upload.slots}
                    onAssignSlot={(slotKey) => upload.assignSlot(doc.id, slotKey)}
                    onRemove={() => upload.remove(doc.id)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-center pt-4">
        <button
          onClick={() => router.push(`/case/${caseId}`)}
          disabled={!upload.isComplete}
          className="rounded-lg bg-stone-800 px-6 py-3 text-white font-medium disabled:opacity-50 hover:bg-stone-700 transition-colors"
        >
          {upload.isComplete ? "Continue to Review" : `${upload.totalRequired - upload.completionCount} required documents remaining`}
        </button>
      </div>
    </div>
  );
}
