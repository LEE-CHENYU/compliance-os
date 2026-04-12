"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { uploadDocument, getCheck } from "@/lib/api-v2";
import { trackForm8843FunnelEvent, trackOnboardingEvent } from "@/lib/analytics";

export const dynamic = "force-dynamic";

interface UploadSlot {
  docType: string; label: string; sub: string; required: boolean;
  file: File | null; uploading: boolean; uploaded: boolean;
}

export default function StudentUploadPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-[#8e9ab5]">Loading...</div>}>
      <StudentUpload />
    </Suspense>
  );
}

function StudentUpload() {
  const router = useRouter();
  const params = useSearchParams();
  const checkId = params.get("id") || "";
  const [slots, setSlots] = useState<UploadSlot[]>([]);
  const [isForm8843Flow, setIsForm8843Flow] = useState(false);
  const fileRefs = useRef<(HTMLInputElement | null)[]>([]);
  const uploadViewTrackedRef = useRef(false);

  useEffect(() => {
    if (!checkId) return;
    getCheck(checkId).then((check) => {
      const fromForm8843 = check.answers?.source_form_8843 === "yes";
      const hasCpt = check.answers?.student_status === "enrolled_cpt";
      const s: UploadSlot[] = [
        { docType: "i20", label: "I-20", sub: "Your most recent I-20 — we\u2019ll check your program dates, CPT authorization, and travel signature", required: true, file: null, uploading: false, uploaded: false },
      ];
      if (hasCpt) {
        s.push({ docType: "employment_letter", label: "Employment / Offer Letter", sub: "Your CPT employer\u2019s offer letter — helps us cross-check against your I-20", required: false, file: null, uploading: false, uploaded: false });
      }
      s.push({ docType: "i94", label: "I-94", sub: "Most recent arrival record — download from i94.cbp.dhs.gov", required: false, file: null, uploading: false, uploaded: false });
      setSlots(s);
      setIsForm8843Flow(fromForm8843);
      trackOnboardingEvent("onboarding_upload_viewed", {
        check_id: check.id,
        check_track: "student",
        required_document_count: s.filter((slot) => slot.required).length,
      });
      if (fromForm8843 && !uploadViewTrackedRef.current) {
        uploadViewTrackedRef.current = true;
        trackForm8843FunnelEvent("form_8843_gtm_upload_viewed", {
          check_id: check.id,
          check_track: "student",
          required_document_count: s.filter((slot) => slot.required).length,
        });
      }
    });
  }, [checkId]);

  const requiredUploaded = slots.filter((s) => s.required).every((s) => s.uploaded);

  const handleFile = useCallback(async (index: number, file: File) => {
    const slot = slots[index];
    setSlots((prev) => prev.map((s, i) => i === index ? { ...s, file, uploading: true } : s));
    await uploadDocument(checkId, file, slot.docType);
    setSlots((prev) => prev.map((s, i) => i === index ? { ...s, uploading: false, uploaded: true } : s));
    trackOnboardingEvent("onboarding_document_uploaded", {
      check_id: checkId,
      check_track: "student",
      doc_type: slot.docType,
      required: slot.required,
    });
    if (isForm8843Flow) {
      trackForm8843FunnelEvent("form_8843_gtm_document_uploaded", {
        check_id: checkId,
        check_track: "student",
        doc_type: slot.docType,
        required: slot.required,
      });
    }
  }, [checkId, isForm8843Flow, slots]);

  if (!slots.length) return <div className="min-h-screen flex items-center justify-center text-[#8e9ab5]">Loading...</div>;

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg py-20">
        <button onClick={() => router.back()} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">&larr; Back</button>
        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">Upload your documents</h1>
        <p className="text-[15px] text-[#556480] mb-8">We&apos;ll check your I-20 authorization against your employment records.</p>

        <div className="flex flex-col gap-4 mb-4">
          {slots.filter(s => s.required).map((slot) => {
            const gi = slots.indexOf(slot);
            return (
              <div key={slot.docType} onClick={() => { if (!slot.uploading && !slot.uploaded) fileRefs.current[gi]?.click(); }}
                className={`relative flex flex-col items-center px-6 py-8 rounded-xl border-2 border-dashed transition-all cursor-pointer ${slot.uploaded ? "border-green-300 bg-green-50/50" : "border-blue-200/40 bg-white/60 hover:border-blue-300/60 hover:bg-white/80"}`}>
                <input ref={(el) => { fileRefs.current[gi] = el; }} type="file" accept=".pdf,.jpg,.jpeg,.png" style={{position:'absolute',width:1,height:1,opacity:0,overflow:'hidden'}} onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(gi, f); }} disabled={slot.uploading || slot.uploaded} />
                {slot.uploaded ? (<><div className="text-green-600 font-semibold text-sm">{slot.file?.name}</div><div className="text-xs text-green-500 mt-1">Uploaded</div></>) : slot.uploading ? (<div className="text-sm text-[#5b8dee] font-medium">Uploading...</div>) : (<><div className="text-[15px] font-semibold text-[#1a2036] mb-1">{slot.label}</div><div className="text-xs text-[#8e9ab5]">{slot.sub}</div><div className="text-xs text-[#b0bdd0] mt-3">Drop PDF here or click to browse</div></>)}
              </div>
            );
          })}
        </div>

        {slots.filter(s => !s.required).length > 0 && (
          <>
            <div className="text-xs font-semibold text-[#7b8ba5] uppercase tracking-widest mb-3 mt-6">Optional</div>
            <div className="flex flex-col gap-3 mb-6">
              {slots.filter(s => !s.required).map((slot) => {
                const gi = slots.indexOf(slot);
                return (
                  <div key={slot.docType} onClick={() => { if (!slot.uploading && !slot.uploaded) fileRefs.current[gi]?.click(); }}
                    className={`relative flex flex-col items-center px-5 py-5 rounded-xl border border-dashed transition-all cursor-pointer ${slot.uploaded ? "border-green-300 bg-green-50/50" : "border-blue-100/30 bg-white/40 hover:border-blue-200/40 hover:bg-white/60"}`}>
                    <input ref={(el) => { fileRefs.current[gi] = el; }} type="file" accept=".pdf,.jpg,.jpeg,.png" style={{position:'absolute',width:1,height:1,opacity:0,overflow:'hidden'}} onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(gi, f); }} disabled={slot.uploading || slot.uploaded} />
                    {slot.uploaded ? (<div className="text-green-600 font-semibold text-sm">{slot.file?.name}</div>) : (<><div className="text-[13px] font-medium text-[#556480]">{slot.label}</div><div className="text-[11px] text-[#8e9ab5] mt-0.5">{slot.sub}</div></>)}
                  </div>
                );
              })}
            </div>
          </>
        )}

        <div className="px-4 py-3 rounded-xl bg-white/40 backdrop-blur border border-white/60 text-xs text-[#556480] mb-8">Your documents are stored securely and used only for compliance checking.</div>

        <button onClick={() => {
          trackOnboardingEvent("onboarding_review_phase_viewed", {
            check_id: checkId,
            check_track: "student",
            phase: "review_continue_clicked",
          });
          if (isForm8843Flow) {
            trackForm8843FunnelEvent("form_8843_gtm_review_continued", {
              check_id: checkId,
              check_track: "student",
            });
          }
          router.push(`/check/student/review?id=${checkId}`);
        }} disabled={!requiredUploaded}
          className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all ${requiredUploaded ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_4px_16px_rgba(74,116,212,0.3)]" : "bg-gray-200 text-gray-400 cursor-not-allowed"}`}>
          Continue to review
        </button>
      </div>
    </div>
  );
}
