"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getCheck, uploadDocument } from "@/lib/api-v2";
import { trackOnboardingEvent } from "@/lib/analytics";
import { markOnboardingSkipped, ONBOARDING_SKIP_DASHBOARD_HREF } from "@/lib/onboarding-skip";
import { useEgressConsent } from "@/lib/useEgressConsent";

export const dynamic = "force-dynamic";

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
  const [error, setError] = useState<string | null>(null);
  const { ensure: ensureConsent, modal: consentModal } = useEgressConsent({
    egressType: "web_doc_upload",
    purpose: "extraction",
    destination: "Guardian's server",
    dataCategories: ["documents"],
  });

  useEffect(() => {
    if (!checkId) {
      return;
    }
    setError(null);
    getCheck(checkId)
      .then((check) => {
        trackOnboardingEvent("onboarding_upload_viewed", {
          check_id: check.id,
          check_track: "entity",
          required_document_count: 1,
        });
      })
      .catch((nextError) => {
        setError(nextError instanceof Error ? nextError.message : "Could not load this check");
      });
  }, [checkId]);

  const handleFile = useCallback(async (f: File) => {
    if (!(await ensureConsent())) return; // <-- gate: no upload without approval
    setFile(f);
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(checkId, f, "tax_return");
      setUploaded(true);
      trackOnboardingEvent("onboarding_document_uploaded", {
        check_id: checkId,
        check_track: "entity",
        doc_type: "tax_return",
        required: true,
      });
    } catch (nextError) {
      setUploaded(false);
      setError(nextError instanceof Error ? nextError.message : "Could not upload this document");
    } finally {
      setUploading(false);
    }
  }, [checkId, ensureConsent]);

  function handleSkipToDashboard() {
    markOnboardingSkipped();
    router.push(ONBOARDING_SKIP_DASHBOARD_HREF);
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      {consentModal}
      <div className="w-full max-w-lg">
        <div className="flex items-center justify-between mb-8">
          <button onClick={() => router.back()} className="text-sm text-[#7b8ba5] hover:text-[#1a2036]">
            &larr; Back
          </button>
          <button onClick={handleSkipToDashboard} className="text-sm text-[#7b8ba5] hover:text-[#1a2036]">
            Skip &rarr; Dashboard
          </button>
        </div>

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
            data-testid="entity-upload-input-tax-return"
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
              <div className="text-[15px] font-semibold text-[#1a2036] mb-2">Most Recent Tax Return</div>
              <div className="text-xs text-[#8e9ab5] leading-relaxed">1120, 1065, 5472 + pro forma 1120, or 1040 with Schedule C</div>
              <div className="text-xs text-[#b0bdd0] mt-3">Drop PDF here or click to browse</div>
              <div className="text-[10px] text-[#b0bdd0] mt-2">Don&apos;t have these? Upload whatever tax-related document you have — we&apos;ll work with it.</div>
            </>
          )}
        </div>

        <div className="px-4 py-3 rounded-xl bg-green-50/60 border border-green-200/30 text-xs text-green-700 mb-8">
          Your documents are stored securely and used only for compliance checking.
        </div>

        {error ? (
          <div data-testid="entity-upload-error" className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
            {error}
          </div>
        ) : null}

        <button
          onClick={() => {
            trackOnboardingEvent("onboarding_review_phase_viewed", {
              check_id: checkId,
              check_track: "entity",
              phase: "review_continue_clicked",
            });
            router.push(`/check/entity/review?id=${checkId}`);
          }}
          disabled={!uploaded}
          data-testid="entity-upload-continue"
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
