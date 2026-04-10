"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import FilingChecklistCard from "@/components/form8843/FilingChecklistCard";
import { getForm8843Order, resolveForm8843PdfUrl, type Form8843OrderResponse } from "@/lib/marketplace";


export default function SuccessContent({ orderId }: { orderId: string }) {
  const [order, setOrder] = useState<Form8843OrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) {
      setError("Missing order ID");
      return;
    }

    let cancelled = false;
    getForm8843Order(orderId)
      .then((result) => {
        if (!cancelled) {
          setOrder(result);
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load order");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  const pdfUrl = resolveForm8843PdfUrl(order?.pdf_url || null);

  return (
    <div className="mx-auto max-w-5xl rounded-[32px] border border-white/80 bg-white/82 p-8 shadow-[0_28px_80px_rgba(61,84,128,0.08)] backdrop-blur md:p-12">
      <div className="mb-6 inline-flex rounded-full border border-[#dce6f3] bg-[#eef5ff] px-4 py-2 text-[12px] font-semibold uppercase tracking-[0.18em] text-[#5f78a8]">
        Form 8843 generated
      </div>
      <h1 className="text-[34px] font-extrabold tracking-tight text-[#0d1424]">Your form is ready. The filing step is next.</h1>
      <p className="mt-4 max-w-3xl text-[16px] leading-7 text-[#556480]">
        Guardian finished the PDF and stored the marketplace order. This page now focuses on the part users usually get stuck on: what to do after the file is generated.
      </p>

      <div className="mt-8 grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Order</div>
          <div className="mt-2 break-all text-[14px] font-medium text-[#1a2942]">{orderId || "Not provided"}</div>
        </div>
        <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Status</div>
          <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{order?.status || (error ? "Unavailable" : "Loading")}</div>
        </div>
        <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Mailing state</div>
          <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{order?.mailing_status || "Loading"}</div>
        </div>
        <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Email handoff</div>
          <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{order?.email_status || "Pending or skipped"}</div>
        </div>
      </div>

      {error ? (
        <div className="mt-8 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
          {error}
        </div>
      ) : null}

      <div className="mt-8 flex flex-col gap-3 md:flex-row">
        <a
          href={pdfUrl || "#"}
          target="_blank"
          rel="noreferrer"
          className={`inline-flex items-center justify-center rounded-full px-6 py-3 text-[15px] font-semibold transition ${
            pdfUrl
              ? "bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] hover:bg-[#4f82de]"
              : "pointer-events-none bg-[#d9e3f0] text-[#90a0bb]"
          }`}
        >
          Download PDF
        </a>
        <Link
          href="/form-8843"
          className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-6 py-3 text-[15px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
        >
          Start another draft
        </Link>
        <Link
          href="/account/orders"
          className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-6 py-3 text-[15px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
        >
          View account orders
        </Link>
      </div>

      {order ? <FilingChecklistCard order={order} onOrderChange={setOrder} /> : null}

      <div className="mt-8 rounded-[24px] border border-dashed border-[#c9d7eb] bg-[#fbfdff] p-5">
        <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">Operational note</div>
        <p className="mt-3 text-[14px] leading-6 text-[#5f6f88]">
          The reminder state is already tracked on the backend. Once a user marks the order as mailed, Guardian can stop nagging them and move on to the next obligation.
        </p>
      </div>
    </div>
  );
}
