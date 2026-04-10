"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import FilingChecklistCard from "@/components/form8843/FilingChecklistCard";
import { isLoggedIn } from "@/lib/auth";
import {
  getMarketplaceOrder,
  resolveForm8843PdfUrl,
  type Form8843OrderResponse,
  type MarketplaceOrder,
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

function toForm8843Order(order: MarketplaceOrder | null): Form8843OrderResponse | null {
  if (!order?.filing_instructions) {
    return null;
  }

  return {
    order_id: order.order_id,
    status: order.status,
    pdf_url: order.pdf_url ?? null,
    email_status: order.email_status ?? null,
    delivery_method: order.delivery_method,
    filing_deadline: order.filing_deadline,
    mailing_status: order.mailing_status,
    mailed_at: order.mailed_at,
    tracking_number: order.tracking_number,
    filing_instructions: order.filing_instructions,
    mailing_service_available: Boolean(order.mailing_service_available),
  };
}

export default function AccountOrderDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const orderId = typeof params?.id === "string" ? params.id : "";
  const [order, setOrder] = useState<MarketplaceOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) {
      setError("Missing order ID");
      setLoading(false);
      return;
    }

    if (!isLoggedIn()) {
      router.replace(`/login?next=${encodeURIComponent(`/account/orders/${orderId}`)}`);
      return;
    }

    let cancelled = false;
    getMarketplaceOrder(orderId)
      .then((nextOrder) => {
        if (!cancelled) {
          setOrder(nextOrder);
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load order");
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

  const form8843Order = useMemo(() => toForm8843Order(order), [order]);
  const pdfUrl = resolveForm8843PdfUrl(order?.pdf_url ?? null);

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f5f8fd_0%,#eef4fb_100%)] px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/account/orders"
          className="inline-flex items-center text-[14px] font-semibold text-[#5b76a2] transition hover:text-[#243958]"
        >
          &larr; Back to orders
        </Link>

        {loading ? (
          <div className="mt-6 rounded-[32px] border border-[#dbe5f2] bg-white/82 px-6 py-8 text-[15px] text-[#6e7f9a] shadow-[0_22px_70px_rgba(61,84,128,0.08)]">
            Loading order details...
          </div>
        ) : null}

        {error ? (
          <div className="mt-6 rounded-[32px] border border-[#ffd6d6] bg-[#fff4f4] px-6 py-4 text-[14px] text-[#a33a3a]">
            {error}
          </div>
        ) : null}

        {order ? (
          <>
            <section className="mt-6 rounded-[32px] border border-[#dbe5f2] bg-white/86 p-8 shadow-[0_26px_80px_rgba(61,84,128,0.08)]">
              <div className="flex flex-wrap items-start justify-between gap-5">
                <div>
                  <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-[#71829f]">
                    {order.product.category || "Marketplace order"}
                  </div>
                  <h1 className="mt-3 text-[34px] font-bold tracking-tight text-[#0d1424]">
                    {order.product.name}
                  </h1>
                  <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
                    {order.product.headline || order.product.description}
                  </p>
                </div>
                <div className="rounded-3xl border border-[#dbe5f2] bg-[#f8fbff] px-5 py-4 text-right">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Status</div>
                  <div className="mt-1 text-[18px] font-semibold capitalize text-[#1a2942]">
                    {order.status.replace(/_/g, " ")}
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-4">
                <div className="rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Order</div>
                  <div className="mt-2 break-all text-[14px] font-medium text-[#1a2942]">{order.order_id}</div>
                </div>
                <div className="rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Ordered</div>
                  <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{formatDate(order.created_at)}</div>
                </div>
                <div className="rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Deadline</div>
                  <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{formatDate(order.filing_deadline)}</div>
                </div>
                <div className="rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Mailing</div>
                  <div className="mt-2 text-[14px] font-medium capitalize text-[#1a2942]">
                    {order.mailing_status.replace(/_/g, " ")}
                  </div>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                {pdfUrl ? (
                  <a
                    href={pdfUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center justify-center rounded-full bg-[#5b8dee] px-5 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de]"
                  >
                    Download PDF
                  </a>
                ) : null}
                {order.product.path ? (
                  <Link
                    href={order.product.path}
                    className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-5 py-3 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
                  >
                    Reopen service
                  </Link>
                ) : null}
              </div>
            </section>

            {!!order.product.highlights.length ? (
              <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Included</div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {order.product.highlights.map((highlight) => (
                    <div
                      key={highlight}
                      className="rounded-2xl border border-[#e4edf7] bg-[#fbfdff] px-4 py-3 text-[14px] text-[#435774]"
                    >
                      {highlight}
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {form8843Order ? (
              <FilingChecklistCard
                order={form8843Order}
                onOrderChange={(nextOrder) => {
                  setOrder((current) => {
                    if (!current) {
                      return current;
                    }
                    return {
                      ...current,
                      ...nextOrder,
                    };
                  });
                }}
              />
            ) : null}
          </>
        ) : null}
      </div>
    </main>
  );
}
