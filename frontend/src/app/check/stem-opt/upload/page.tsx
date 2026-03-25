"use client";

import { Suspense, useCallback, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { uploadDocument } from "@/lib/api-v2";

interface UploadSlot {
  docType: string;
  label: string;
  sub: string;
  file: File | null;
  uploading: boolean;
  uploaded: boolean;
}

export default function StemOptUploadPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-[#8e9ab5]">Loading...</div>}>
      <StemOptUpload />
    </Suspense>
  );
}

function StemOptUpload() {
  const router = useRouter();
  const params = useSearchParams();
  const checkId = params.get("id") || "";

  const [slots, setSlots] = useState<UploadSlot[]>([
    { docType: "i983", label: "Form I-983", sub: "The training plan you signed with your employer and DSO", file: null, uploading: false, uploaded: false },
    { docType: "employment_letter", label: "Employment Letter", sub: "The offer letter or employment verification from your employer", file: null, uploading: false, uploaded: false },
  ]);

  const fileRefs = useRef<(HTMLInputElement | null)[]>([]);

  const allUploaded = slots.every((s) => s.uploaded);

  const handleFile = useCallback(async (index: number, file: File) => {
    setSlots((prev) => prev.map((s, i) => i === index ? { ...s, file, uploading: true } : s));
    await uploadDocument(checkId, file, slots[index].docType);
    setSlots((prev) => prev.map((s, i) => i === index ? { ...s, uploading: false, uploaded: true } : s));
  }, [checkId, slots]);

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg">
        <button onClick={() => router.back()} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">
          ← Back
        </button>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          Upload your two documents
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          We&apos;ll extract key fields from both and compare them.
        </p>

        <div className="flex flex-col gap-4 mb-8">
          {slots.map((slot, i) => (
            <div
              key={slot.docType}
              onClick={() => {
                if (slot.uploading || slot.uploaded) return;
                fileRefs.current[i]?.click();
              }}
              className={`relative flex flex-col items-center px-6 py-8 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
                slot.uploaded
                  ? "border-green-300 bg-green-50/50"
                  : "border-blue-200/40 bg-white/60 hover:border-blue-300/60 hover:bg-white/80"
              }`}
            >
              <input
                ref={(el) => { fileRefs.current[i] = el; }}
                type="file"
                accept=".pdf"
                style={{ position: 'absolute', width: 1, height: 1, opacity: 0, overflow: 'hidden' }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFile(i, f);
                }}
                disabled={slot.uploading || slot.uploaded}
              />
              {slot.uploaded ? (
                <>
                  <div className="text-green-600 font-semibold text-sm">✓ {slot.file?.name}</div>
                  <div className="text-xs text-green-500 mt-1">Uploaded</div>
                </>
              ) : slot.uploading ? (
                <div className="text-sm text-[#5b8dee] font-medium">Uploading...</div>
              ) : (
                <>
                  <div className="text-[15px] font-semibold text-[#1a2036] mb-1">📄 {slot.label}</div>
                  <div className="text-xs text-[#8e9ab5]">{slot.sub}</div>
                  <div className="text-xs text-[#b0bdd0] mt-3">Drop PDF here or click to browse</div>
                </>
              )}
            </div>
          ))}
        </div>

        <div className="px-4 py-3 rounded-xl bg-green-50/60 border border-green-200/30 text-xs text-green-700 mb-8">
          🔒 Documents sent to OpenAI for field extraction only. Never stored or shared beyond that.
        </div>

        <button
          onClick={() => router.push(`/check/stem-opt/review?id=${checkId}`)}
          disabled={!allUploaded}
          className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all ${
            allUploaded
              ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_4px_16px_rgba(74,116,212,0.3)] hover:shadow-[0_8px_28px_rgba(74,116,212,0.4)]"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          Continue to review
        </button>
      </div>
    </div>
  );
}
