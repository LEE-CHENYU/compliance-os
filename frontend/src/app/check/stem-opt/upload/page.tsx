"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { uploadDocument, getCheck } from "@/lib/api-v2";

export const dynamic = "force-dynamic";

interface UploadSlot {
  docType: string;
  label: string;
  sub: string;
  required: boolean;
  file: File | null;
  uploading: boolean;
  uploaded: boolean;
}

// Stage-specific document slots
const STAGE_SLOTS: Record<string, UploadSlot[]> = {
  pre_completion: [
    { docType: "employment_letter", label: "Employment Letter", sub: "Offer letter or CPT authorization from employer", required: true, file: null, uploading: false, uploaded: false },
    { docType: "i20", label: "I-20 with CPT Authorization", sub: "I-20 showing CPT endorsement from your DSO", required: true, file: null, uploading: false, uploaded: false },
  ],
  opt: [
    { docType: "employment_letter", label: "Employment Letter", sub: "Offer letter, verification letter, or employment contract", required: true, file: null, uploading: false, uploaded: false },
    { docType: "ead", label: "EAD Card (I-766)", sub: "Your Employment Authorization Document — front and back", required: true, file: null, uploading: false, uploaded: false },
    { docType: "i20", label: "I-20", sub: "Your most recent I-20 with OPT recommendation", required: false, file: null, uploading: false, uploaded: false },
  ],
  stem_opt: [
    { docType: "employment_letter", label: "Employment Letter", sub: "Offer letter, verification letter, or employment contract", required: true, file: null, uploading: false, uploaded: false },
    { docType: "i983", label: "Form I-983", sub: "Training Plan for STEM OPT — signed by you, your employer, and your DSO", required: true, file: null, uploading: false, uploaded: false },
    { docType: "ead", label: "EAD Card (I-766)", sub: "Your Employment Authorization Document — front and back", required: false, file: null, uploading: false, uploaded: false },
  ],
  h1b: [
    { docType: "employment_letter", label: "Employment Letter", sub: "Current offer letter or employment verification", required: true, file: null, uploading: false, uploaded: false },
    { docType: "i797", label: "I-797 (Approval Notice)", sub: "H-1B approval notice or receipt notice from USCIS", required: true, file: null, uploading: false, uploaded: false },
    { docType: "i94", label: "I-94", sub: "Most recent arrival/departure record — download from i94.cbp.dhs.gov", required: false, file: null, uploading: false, uploaded: false },
  ],
  i140: [
    { docType: "employment_letter", label: "Employment Letter", sub: "Current employment verification from sponsoring employer", required: true, file: null, uploading: false, uploaded: false },
    { docType: "i797", label: "I-797 (I-140 Approval)", sub: "I-140 approval or receipt notice", required: true, file: null, uploading: false, uploaded: false },
    { docType: "i94", label: "I-94", sub: "Most recent arrival/departure record", required: false, file: null, uploading: false, uploaded: false },
    { docType: "i140_supplement", label: "Priority Date Evidence", sub: "Any document showing your priority date — I-140 receipt, employer letter", required: false, file: null, uploading: false, uploaded: false },
  ],
  not_sure: [
    { docType: "employment_letter", label: "Employment Letter", sub: "Offer letter, verification letter, or employment contract", required: true, file: null, uploading: false, uploaded: false },
    { docType: "i983", label: "Form I-983 (if you have one)", sub: "Training Plan for STEM OPT students", required: false, file: null, uploading: false, uploaded: false },
    { docType: "ead", label: "EAD Card (if you have one)", sub: "Employment Authorization Document", required: false, file: null, uploading: false, uploaded: false },
    { docType: "i20", label: "I-20 (if you have one)", sub: "Your most recent I-20", required: false, file: null, uploading: false, uploaded: false },
    { docType: "i797", label: "I-797 (if you have one)", sub: "Any USCIS approval or receipt notice", required: false, file: null, uploading: false, uploaded: false },
  ],
};

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

  const [slots, setSlots] = useState<UploadSlot[]>([]);
  const [stage, setStage] = useState<string>("");
  const fileRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Load the check to get the stage, then set appropriate slots
  useEffect(() => {
    if (!checkId) return;
    getCheck(checkId).then((check) => {
      const s = check.answers?.stage as string || "not_sure";
      setStage(s);
      setSlots(STAGE_SLOTS[s] || STAGE_SLOTS.not_sure);
    });
  }, [checkId]);

  const requiredUploaded = slots.filter((s) => s.required).every((s) => s.uploaded);

  const handleFile = useCallback(async (index: number, file: File) => {
    setSlots((prev) => prev.map((s, i) => i === index ? { ...s, file, uploading: true } : s));
    await uploadDocument(checkId, file, slots[index].docType);
    setSlots((prev) => prev.map((s, i) => i === index ? { ...s, uploading: false, uploaded: true } : s));
  }, [checkId, slots]);

  const STAGE_LABELS: Record<string, string> = {
    stem_opt: "STEM OPT",
    opt: "Post-completion OPT",
    applying_stem: "Applying for STEM extension",
    pre_completion: "Pre-completion (CPT)",
    not_sure: "your situation",
  };

  if (!slots.length) {
    return <div className="min-h-screen flex items-center justify-center text-[#8e9ab5]">Loading...</div>;
  }

  const requiredSlots = slots.filter((s) => s.required);
  const optionalSlots = slots.filter((s) => !s.required);

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg py-20">
        <button onClick={() => router.back()} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">
          &larr; Back
        </button>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          Upload your documents
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          We&apos;ll extract key fields and check for {STAGE_LABELS[stage] || "compliance"} issues.
        </p>

        {/* Required uploads */}
        <div className="flex flex-col gap-4 mb-4">
          {requiredSlots.map((slot) => {
            const globalIndex = slots.indexOf(slot);
            return (
              <div
                key={slot.docType}
                onClick={() => {
                  if (slot.uploading || slot.uploaded) return;
                  fileRefs.current[globalIndex]?.click();
                }}
                className={`relative flex flex-col items-center px-6 py-8 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
                  slot.uploaded
                    ? "border-green-300 bg-green-50/50"
                    : "border-blue-200/40 bg-white/60 hover:border-blue-300/60 hover:bg-white/80"
                }`}
              >
                <input
                  ref={(el) => { fileRefs.current[globalIndex] = el; }}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  style={{ position: 'absolute', width: 1, height: 1, opacity: 0, overflow: 'hidden' }}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(globalIndex, f);
                  }}
                  disabled={slot.uploading || slot.uploaded}
                />
                {slot.uploaded ? (
                  <>
                    <div className="text-green-600 font-semibold text-sm">{slot.file?.name}</div>
                    <div className="text-xs text-green-500 mt-1">Uploaded</div>
                  </>
                ) : slot.uploading ? (
                  <div className="text-sm text-[#5b8dee] font-medium">Uploading...</div>
                ) : (
                  <>
                    <div className="text-[15px] font-semibold text-[#1a2036] mb-1">{slot.label}</div>
                    <div className="text-xs text-[#8e9ab5]">{slot.sub}</div>
                    <div className="text-xs text-[#b0bdd0] mt-3">Drop PDF here or click to browse</div>
                  </>
                )}
              </div>
            );
          })}
        </div>

        {/* Optional uploads */}
        {optionalSlots.length > 0 && (
          <>
            <div className="text-xs font-semibold text-[#7b8ba5] uppercase tracking-widest mb-3 mt-6">
              Optional — improves accuracy
            </div>
            <div className="flex flex-col gap-3 mb-6">
              {optionalSlots.map((slot) => {
                const globalIndex = slots.indexOf(slot);
                return (
                  <div
                    key={slot.docType}
                    onClick={() => {
                      if (slot.uploading || slot.uploaded) return;
                      fileRefs.current[globalIndex]?.click();
                    }}
                    className={`relative flex flex-col items-center px-5 py-5 rounded-xl border border-dashed transition-all cursor-pointer ${
                      slot.uploaded
                        ? "border-green-300 bg-green-50/50"
                        : "border-blue-100/30 bg-white/40 hover:border-blue-200/40 hover:bg-white/60"
                    }`}
                  >
                    <input
                      ref={(el) => { fileRefs.current[globalIndex] = el; }}
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      style={{ position: 'absolute', width: 1, height: 1, opacity: 0, overflow: 'hidden' }}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFile(globalIndex, f);
                      }}
                      disabled={slot.uploading || slot.uploaded}
                    />
                    {slot.uploaded ? (
                      <div className="text-green-600 font-semibold text-sm">{slot.file?.name}</div>
                    ) : slot.uploading ? (
                      <div className="text-sm text-[#5b8dee] font-medium">Uploading...</div>
                    ) : (
                      <>
                        <div className="text-[13px] font-medium text-[#556480]">{slot.label}</div>
                        <div className="text-[11px] text-[#8e9ab5] mt-0.5">{slot.sub}</div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}

        <div className="px-4 py-3 rounded-xl bg-white/40 backdrop-blur border border-white/60 text-xs text-[#556480] mb-8">
          Your documents are stored securely and used only for compliance checking.
        </div>

        <button
          onClick={() => router.push(`/check/stem-opt/review?id=${checkId}`)}
          disabled={!requiredUploaded}
          className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all ${
            requiredUploaded
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
