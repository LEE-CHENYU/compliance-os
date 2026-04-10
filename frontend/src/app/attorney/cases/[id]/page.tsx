"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import SignOffChecklist from "@/components/attorney/SignOffChecklist";
import { getUser, isLoggedIn } from "@/lib/auth";
import {
  fileAttorneyCase,
  getAttorneyCase,
  reviewAttorneyCase,
  type AttorneyCaseResponse,
} from "@/lib/marketplace";


export const dynamic = "force-dynamic";

function formatDate(value: string | null): string {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function AttorneyCasePage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const orderId = typeof params?.id === "string" ? params.id : "";
  const [data, setData] = useState<AttorneyCaseResponse | null>(null);
  const [checklistResponses, setChecklistResponses] = useState<Record<string, boolean>>({});
  const [notes, setNotes] = useState("");
  const [receiptNumber, setReceiptNumber] = useState("");
  const [filingConfirmation, setFilingConfirmation] = useState("Filed via MyUSCIS");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"review" | "file" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) {
      setError("Missing order ID");
      setLoading(false);
      return;
    }

    if (!isLoggedIn()) {
      router.replace(`/login?next=${encodeURIComponent(`/attorney/cases/${orderId}`)}`);
      return;
    }
    if (getUser()?.role !== "attorney") {
      setError("Attorney access is required for this page.");
      setLoading(false);
      return;
    }

    let cancelled = false;
    getAttorneyCase(orderId)
      .then((nextData) => {
        if (!cancelled) {
          setData(nextData);
          setChecklistResponses(nextData.assignment?.checklist_responses || {});
          setNotes(nextData.assignment?.attorney_notes || "");
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load case");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [orderId, router]);

  async function handleReview(decision: "approve" | "flag_upgrade") {
    if (!data) {
      return;
    }
    setBusy("review");
    setError(null);
    setNotice(null);
    try {
      const response = await reviewAttorneyCase(orderId, {
        decision,
        notes,
        checklist_responses: checklistResponses,
      });
      setData((current) => current ? { ...current, order: response.order, assignment: response.assignment } : current);
      setNotice(decision === "approve" ? "Review recorded. The case is ready for filing." : "Case flagged for upgrade.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not save review");
    } finally {
      setBusy(null);
    }
  }

  async function handleFile() {
    if (!data || !receiptNumber.trim()) {
      return;
    }
    setBusy("file");
    setError(null);
    setNotice(null);
    try {
      const response = await fileAttorneyCase(orderId, {
        receipt_number: receiptNumber.trim(),
        filing_confirmation: filingConfirmation.trim() || undefined,
      });
      setData((current) => current ? { ...current, order: response.order } : current);
      setNotice(`Filing recorded with receipt ${response.receipt_number}.`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not record filing");
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#eef4fb] px-6 py-16">
        <div className="mx-auto max-w-6xl rounded-[28px] border border-white/80 bg-white/82 p-8 text-[#556480] shadow-[0_24px_70px_rgba(61,84,128,0.06)]">
          Loading case...
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-[#eef4fb] px-6 py-16">
        <div className="mx-auto max-w-6xl rounded-[28px] border border-[#ffd6d6] bg-white p-8 text-[#a33a3a] shadow-[0_24px_70px_rgba(61,84,128,0.06)]">
          {error}
        </div>
      </div>
    );
  }

  return data ? (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f5f8fd_0%,#eef4fb_100%)] px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <Link
          href="/attorney/dashboard"
          className="inline-flex items-center text-[14px] font-semibold text-[#5b76a2] transition hover:text-[#243958]"
        >
          &larr; Back to dashboard
        </Link>

        <section className="mt-6 rounded-[32px] border border-[#dbe5f2] bg-white/86 p-8 shadow-[0_26px_80px_rgba(61,84,128,0.08)]">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-[#71829f]">Attorney review</div>
              <h1 className="mt-3 text-[34px] font-bold tracking-tight text-[#0d1424]">{data.order.product.name}</h1>
              <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
                Client {data.order.user_id} · agreement signed {formatDate(data.agreement?.signed_at || null)}
              </p>
            </div>
            <div className="rounded-3xl border border-[#dbe5f2] bg-[#f8fbff] px-5 py-4 text-right">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Status</div>
              <div className="mt-1 text-[18px] font-semibold capitalize text-[#1a2942]">
                {data.order.status.replace(/_/g, " ")}
              </div>
            </div>
          </div>

          {error ? (
            <div className="mt-6 rounded-[24px] border border-[#ffd6d6] bg-[#fff4f4] px-5 py-4 text-[14px] text-[#a33a3a]">
              {error}
            </div>
          ) : null}

          {notice ? (
            <div className="mt-6 rounded-[24px] border border-[#cfe7d3] bg-[#f3fbf4] px-5 py-4 text-[14px] text-[#326247]">
              {notice}
            </div>
          ) : null}

          <div className="mt-6 grid gap-6 lg:grid-cols-[1fr,0.9fr]">
            <div className="space-y-6">
              <section className="rounded-[28px] border border-[#dbe5f2] bg-[#fbfdff] p-6">
                <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Agreement snapshot</div>
                <pre className="mt-4 max-h-[260px] overflow-y-auto whitespace-pre-wrap font-[ui-monospace,SFMono-Regular,Menlo,monospace] text-[13px] leading-6 text-[#364863]">
                  {data.agreement?.agreement_text || "No agreement found"}
                </pre>
              </section>

              <section className="rounded-[28px] border border-[#dbe5f2] bg-[#fbfdff] p-6">
                <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Checklist</div>
                <h2 className="mt-2 text-[24px] font-bold tracking-tight text-[#0d1424]">Execution review</h2>
                <div className="mt-5">
                  <SignOffChecklist
                    items={data.checklist.checklist}
                    responses={checklistResponses}
                    onChange={(itemId, checked) => setChecklistResponses((current) => ({ ...current, [itemId]: checked }))}
                  />
                </div>
                <label className="mt-5 block">
                  <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Notes</div>
                  <textarea
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    className="mt-2 min-h-[140px] w-full rounded-[22px] border border-[#dbe5f2] bg-white px-4 py-3 text-[14px] text-[#1a2942] outline-none transition focus:border-[#9db8e6]"
                    placeholder="Explain any concerns or filing context for the ops team."
                  />
                </label>
                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => void handleReview("approve")}
                    disabled={busy === "review"}
                    className="inline-flex rounded-full bg-[#0f1728] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a] disabled:cursor-not-allowed disabled:bg-[#8b97ad]"
                  >
                    {busy === "review" ? "Saving..." : "Approve review"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleReview("flag_upgrade")}
                    disabled={busy === "review"}
                    className="inline-flex rounded-full border border-[#d8c69a] bg-[#fff9eb] px-5 py-3 text-[14px] font-semibold text-[#8a6a1f] transition hover:border-[#cfb16b] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Flag for upgrade
                  </button>
                </div>
              </section>
            </div>

            <div className="space-y-6">
              <section className="rounded-[28px] border border-[#dbe5f2] bg-[#fbfdff] p-6">
                <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Assignment</div>
                <div className="mt-3 text-[22px] font-bold tracking-tight text-[#0d1424]">
                  {data.assignment?.attorney?.full_name || "Assigned attorney"}
                </div>
                <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                  Decision {data.assignment?.decision.replace(/_/g, " ") || "pending"} · assigned {formatDate(data.assignment?.assigned_at || null)}
                </p>
              </section>

              <section className="rounded-[28px] border border-[#dbe5f2] bg-[#fbfdff] p-6">
                <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Filing confirmation</div>
                <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                  Record the USCIS receipt number once the filing has been submitted externally.
                </p>
                <label className="mt-4 block">
                  <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Receipt number</div>
                  <input
                    value={receiptNumber}
                    onChange={(event) => setReceiptNumber(event.target.value)}
                    className="mt-2 w-full rounded-[22px] border border-[#dbe5f2] bg-white px-4 py-3 text-[14px] text-[#1a2942] outline-none transition focus:border-[#9db8e6]"
                    placeholder="IOE1234567890"
                  />
                </label>
                <label className="mt-4 block">
                  <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Confirmation note</div>
                  <input
                    value={filingConfirmation}
                    onChange={(event) => setFilingConfirmation(event.target.value)}
                    className="mt-2 w-full rounded-[22px] border border-[#dbe5f2] bg-white px-4 py-3 text-[14px] text-[#1a2942] outline-none transition focus:border-[#9db8e6]"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => void handleFile()}
                  disabled={busy === "file" || data.assignment?.decision !== "approve"}
                  className="mt-5 inline-flex rounded-full bg-[#5b8dee] px-5 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de] disabled:cursor-not-allowed disabled:bg-[#9db8e6]"
                >
                  {busy === "file" ? "Saving..." : "Record filing"}
                </button>
              </section>
            </div>
          </div>
        </section>
      </div>
    </main>
  ) : null;
}
