"use client";

import { Suspense, useCallback, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { uploadDocument } from "@/lib/api-v2";

export default function EntityUploadPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-[#8e9ab5]">Loading...</div>}>
      <EntityUpload />
    </Suspense>
  );
}

function EntityUpload() {
  const router = useRouter();
  const params = useSearchParams();
  const checkId = params.get("id") || "";
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);

  const handleFile = useCallback(async (f: File) => {
    setFile(f);
    setUploading(true);
    await uploadDocument(checkId, f, "tax_return");
    setUploading(false);
    setUploaded(true);
  }, [checkId]);

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg">
        <button onClick={() => router.back()} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">
          &larr; Back
        </button>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          Upload your tax return
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          We&apos;ll check if your entity structure matches what was filed.
        </p>

        <div
          onClick={() => { if (!uploading && !uploaded) fileRef.current?.click(); }}
          className={`relative flex flex-col items-center px-6 py-12 rounded-xl border-2 border-dashed transition-all cursor-pointer mb-8 ${
            uploaded
              ? "border-green-300 bg-green-50/50"
              : "border-blue-200/40 bg-white/60 hover:border-blue-300/60 hover:bg-white/80"
          }`}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            style={{ position: 'absolute', width: 1, height: 1, opacity: 0, overflow: 'hidden' }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
            disabled={uploading || uploaded}
          />
          {uploaded ? (
            <>
              <div className="text-green-600 font-semibold text-sm">&check; {file?.name}</div>
              <div className="text-xs text-green-500 mt-1">Uploaded</div>
            </>
          ) : uploading ? (
            <div className="text-sm text-[#5b8dee] font-medium">Uploading...</div>
          ) : (
            <>
              <div className="text-[15px] font-semibold text-[#1a2036] mb-1">&#128196; Most Recent Tax Return</div>
              <div className="text-xs text-[#8e9ab5]">1120, 1065, 5472 + pro forma 1120, or 1040 with Schedule C</div>
              <div className="text-xs text-[#b0bdd0] mt-3">Drop PDF here or click to browse</div>
            </>
          )}
        </div>

        <div className="px-4 py-3 rounded-xl bg-green-50/60 border border-green-200/30 text-xs text-green-700 mb-8">
          &#128274; Documents sent to OpenAI for field extraction only. Never stored or shared beyond that.
        </div>

        <button
          onClick={() => router.push(`/check/entity/review?id=${checkId}`)}
          disabled={!uploaded}
          className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all ${
            uploaded
              ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_4px_16px_rgba(74,116,212,0.3)]"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          Continue to review
        </button>
      </div>
    </div>
  );
}
