"use client";

import { useState } from "react";

import {
  getForm8843MailingKit,
  markForm8843Mailed,
  type Form8843MailingKitResponse,
  type Form8843OrderResponse,
} from "@/lib/marketplace";


function saveTextFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function FilingChecklistCard({
  order,
  onOrderChange,
}: {
  order: Form8843OrderResponse;
  onOrderChange: (nextOrder: Form8843OrderResponse) => void;
}) {
  const [trackingNumber, setTrackingNumber] = useState(order.tracking_number || "");
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [kitLoading, setKitLoading] = useState(false);
  const [markingMailed, setMarkingMailed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const instructions = order.filing_instructions;

  async function handleCopyAddress() {
    if (!instructions.address_block) {
      return;
    }
    try {
      await navigator.clipboard.writeText(instructions.address_block);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1800);
    } catch {
      setCopyState("error");
    }
  }

  async function handleDownloadKit() {
    setKitLoading(true);
    setError(null);
    try {
      const kit: Form8843MailingKitResponse = await getForm8843MailingKit(order.order_id);
      const content = [
        `Order: ${kit.order_id}`,
        `Deadline: ${kit.filing_deadline || "Not provided"}`,
        "",
        "Mailing address:",
        kit.address_block || "File this with your Form 1040-NR package.",
        "",
        "Filing notes:",
        kit.filing_notes,
        "",
        "Recommended service:",
        kit.recommended_service,
        "",
        "Envelope template:",
        kit.envelope_template_text,
      ].join("\n");
      saveTextFile(`form-8843-mailing-kit-${kit.order_id}.txt`, content);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not download the mailing kit");
    } finally {
      setKitLoading(false);
    }
  }

  async function handleMarkMailed() {
    setMarkingMailed(true);
    setError(null);
    try {
      const nextOrder = await markForm8843Mailed(order.order_id, {
        tracking_number: trackingNumber.trim() || undefined,
      });
      onOrderChange(nextOrder);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not update mailing status");
    } finally {
      setMarkingMailed(false);
    }
  }

  return (
    <section className="mt-8 rounded-[28px] border border-[#dbe5f2] bg-[#fbfdff] p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">Filing checklist</div>
          <h2 className="mt-2 text-[28px] font-bold tracking-tight text-[#0d1424]">{instructions.headline}</h2>
          <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#556480]">{instructions.summary}</p>
        </div>
        <div className="rounded-2xl border border-[#dbe5f2] bg-white px-4 py-3 text-right shadow-[0_10px_26px_rgba(61,84,128,0.05)]">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Deadline</div>
          <div className="mt-1 text-[18px] font-bold text-[#0d1424]">{instructions.deadline_label || "Not provided"}</div>
        </div>
      </div>

      {instructions.address_block ? (
        <div className="mt-6 rounded-2xl border border-[#dbe5f2] bg-white p-5">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">IRS mailing address</div>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-[15px] leading-7 text-[#21324d]">{instructions.address_block}</pre>
        </div>
      ) : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
        <div className="rounded-2xl border border-[#dbe5f2] bg-white p-5">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">What to do next</div>
          <ol className="mt-4 space-y-3">
            {instructions.steps.map((step, index) => (
              <li key={`${index}-${step}`} className="flex gap-3 text-[14px] leading-6 text-[#435774]">
                <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#edf4ff] text-[12px] font-bold text-[#315aa5]">
                  {index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          {instructions.certified_mail_recommended ? (
            <div className="mt-5 rounded-2xl border border-[#f2dfb2] bg-[#fff9eb] px-4 py-3 text-[13px] leading-6 text-[#7a5c10]">
              USPS Certified Mail with Return Receipt is recommended because it gives you proof that the form was actually sent.
            </div>
          ) : null}
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-[#dbe5f2] bg-white p-5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Actions</div>
            <div className="mt-4 flex flex-col gap-3">
              {instructions.address_block ? (
                <button
                  type="button"
                  onClick={handleCopyAddress}
                  className="rounded-full border border-[#dbe5f2] bg-[#f8fbff] px-4 py-3 text-[14px] font-semibold text-[#35527f] transition hover:border-[#c4d4ea] hover:bg-white"
                >
                  {copyState === "copied" ? "Mailing address copied" : copyState === "error" ? "Copy failed" : "Copy mailing address"}
                </button>
              ) : null}
              <button
                type="button"
                onClick={handleDownloadKit}
                disabled={kitLoading}
                className={`rounded-full border px-4 py-3 text-[14px] font-semibold transition ${
                  kitLoading
                    ? "border-[#dbe5f2] bg-[#eef3f8] text-[#93a1b7]"
                    : "border-[#dbe5f2] bg-white text-[#35527f] hover:border-[#c4d4ea]"
                }`}
              >
                {kitLoading ? "Preparing mailing kit..." : "Download mailing kit"}
              </button>
            </div>
          </div>

          {order.mailing_status === "mailed" ? (
            <div className="rounded-2xl border border-[#cfe6d0] bg-[#f4fbf5] p-5 text-[14px] leading-6 text-[#2f5f34]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#65906a]">Filed status</div>
              <div className="mt-2 font-semibold">Marked as mailed</div>
              <div className="mt-2">Guardian has stopped the standalone mailing reminders for this order.</div>
              {order.tracking_number ? <div className="mt-2">Tracking: {order.tracking_number}</div> : null}
            </div>
          ) : instructions.can_mark_mailed ? (
            <div className="rounded-2xl border border-[#dbe5f2] bg-white p-5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Confirm completion</div>
              <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                Once you have physically mailed the signed form, mark this order as mailed so Guardian stops the reminders.
              </p>
              <input
                value={trackingNumber}
                onChange={(event) => setTrackingNumber(event.target.value)}
                placeholder="Optional USPS tracking number"
                className="mt-4 w-full rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] px-4 py-3 text-[14px] text-[#0d1424] outline-none transition focus:border-[#5b8dee] focus:ring-4 focus:ring-[#5b8dee]/10"
              />
              <button
                type="button"
                onClick={handleMarkMailed}
                disabled={markingMailed}
                className={`mt-4 w-full rounded-full px-5 py-3 text-[14px] font-semibold transition ${
                  markingMailed
                    ? "bg-[#d9e3f0] text-[#90a0bb]"
                    : "bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.22)] hover:bg-[#4f82de]"
                }`}
              >
                {markingMailed ? "Saving..." : "Mark as mailed"}
              </button>
            </div>
          ) : null}

          {instructions.mailing_service_available ? (
            <div className="rounded-2xl border border-[#dbe5f2] bg-[#0f1728] p-5 text-white">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8ca2cc]">Optional upsell</div>
              <div className="mt-2 text-[20px] font-bold">Let Guardian handle the mailing</div>
              <p className="mt-3 text-[14px] leading-6 text-[#cad6ec]">
                Assisted mailing is available for this order once the beta is enabled for your account.
              </p>
            </div>
          ) : null}

          {error ? (
            <div className="rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
              {error}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
