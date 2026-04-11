"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { isLoggedIn } from "@/lib/auth";
import { listMarketplaceOrders, type MarketplaceOrder } from "@/lib/marketplace";


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

function formatPrice(cents: number): string {
  if (!cents) {
    return "Free";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

function displayProductName(order: MarketplaceOrder): string {
  return order.product.public_name || order.product.name;
}

function displayProductSummary(order: MarketplaceOrder): string {
  return order.product.public_headline || order.product.headline || order.product.public_description || order.product.description;
}

function orderPrimaryAction(order: MarketplaceOrder): { label: string; href: string } {
  if (order.product_sku === "student_tax_1040nr") {
    if (!order.intake_complete) {
      return { label: "Continue tax intake", href: `/account/orders/${order.order_id}?task=intake` };
    }
    if (!order.result_ready) {
      return { label: "Generate tax package", href: `/account/orders/${order.order_id}` };
    }
    return { label: "Review tax package", href: `/account/orders/${order.order_id}` };
  }
  if (order.product_sku === "h1b_doc_check") {
    if (!order.intake_complete) {
      return { label: "Continue document intake", href: `/account/orders/${order.order_id}?task=intake` };
    }
    if (!order.result_ready) {
      return { label: "Run document review", href: `/account/orders/${order.order_id}` };
    }
    return { label: "Review H-1B findings", href: `/account/orders/${order.order_id}` };
  }
  if (order.product_sku === "fbar_check") {
    if (!order.intake_complete) {
      return { label: "Continue FBAR intake", href: `/account/orders/${order.order_id}?task=intake` };
    }
    if (!order.result_ready) {
      return { label: "Run FBAR check", href: `/account/orders/${order.order_id}` };
    }
    return { label: "Review FBAR guidance", href: `/account/orders/${order.order_id}` };
  }
  if (order.product_sku === "election_83b") {
    if (!order.intake_complete) {
      return { label: "Continue 83(b) intake", href: `/account/orders/${order.order_id}?task=intake` };
    }
    if (!order.result_ready) {
      return { label: "Generate 83(b) packet", href: `/account/orders/${order.order_id}` };
    }
    return { label: "Review 83(b) packet", href: `/account/orders/${order.order_id}` };
  }
  if (order.product_sku === "opt_execution" || order.product_sku === "opt_advisory") {
    if (!order.intake_complete) {
      return { label: "Continue OPT intake", href: `/account/orders/${order.order_id}?task=intake` };
    }
    if (!order.agreement_signed) {
      return { label: "Review agreement", href: `/account/orders/${order.order_id}` };
    }
    return { label: "Review filing status", href: `/account/orders/${order.order_id}` };
  }
  if (order.product_sku === "form_8843_free") {
    return { label: "Review filing checklist", href: `/account/orders/${order.order_id}` };
  }
  return { label: "Open workspace", href: `/account/orders/${order.order_id}` };
}

export default function AccountOrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<MarketplaceOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace(`/login?next=${encodeURIComponent("/account/orders")}`);
      return;
    }

    let cancelled = false;
    listMarketplaceOrders()
      .then((nextOrders) => {
        if (!cancelled) {
          setOrders(nextOrders);
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load orders");
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
  }, [router]);

  const completedOrders = useMemo(
    () => orders.filter((order) => order.status === "completed").length,
    [orders],
  );

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f5f8fd_0%,#eef4fb_100%)] px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white/84 px-4 py-2 text-[13px] font-semibold text-[#40536f] shadow-[0_10px_24px_rgba(61,84,128,0.06)] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
          >
            &larr; Back to dashboard
          </Link>
          <Link
            href="/services"
            className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white/70 px-4 py-2 text-[13px] font-semibold text-[#5b76a2] transition hover:border-[#c4d4ea] hover:text-[#243958]"
          >
            Browse services
          </Link>
        </div>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mt-6 text-[12px] font-semibold uppercase tracking-[0.18em] text-[#70819e]">Account</div>
            <h1 className="mt-3 text-[38px] font-bold tracking-tight text-[#0d1424]">Orders</h1>
            <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#556480]">
              Use this page to reopen completed filings, keep track of mailing status, and return to any service you already started.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-3xl border border-[#dbe5f2] bg-white/88 px-5 py-4 shadow-[0_18px_45px_rgba(61,84,128,0.06)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Total orders</div>
              <div className="mt-2 text-[26px] font-bold text-[#12213a]">{orders.length}</div>
            </div>
            <div className="rounded-3xl border border-[#dbe5f2] bg-white/88 px-5 py-4 shadow-[0_18px_45px_rgba(61,84,128,0.06)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Completed</div>
              <div className="mt-2 text-[26px] font-bold text-[#12213a]">{completedOrders}</div>
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-8 rounded-3xl border border-[#ffd6d6] bg-[#fff4f4] px-5 py-4 text-[14px] text-[#a33a3a]">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="mt-8 rounded-[32px] border border-[#dbe5f2] bg-white/82 px-6 py-8 text-[15px] text-[#6e7f9a] shadow-[0_22px_70px_rgba(61,84,128,0.08)]">
            Loading your orders...
          </div>
        ) : null}

        {!loading && !orders.length ? (
          <div className="mt-8 rounded-[32px] border border-dashed border-[#c8d6ea] bg-white/76 px-6 py-10 shadow-[0_22px_70px_rgba(61,84,128,0.06)]">
            <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-[#74839b]">No orders yet</div>
            <h2 className="mt-3 text-[28px] font-bold tracking-tight text-[#0d1424]">Your account is ready for marketplace services.</h2>
            <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#556480]">
              Once you start a filing or buy a paid service, it will show up here with the next action and any delivery steps.
            </p>
            <Link
              href="/services"
              className="mt-6 inline-flex items-center justify-center rounded-full bg-[#5b8dee] px-5 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de]"
            >
              Browse services
            </Link>
          </div>
        ) : null}

        {!!orders.length ? (
          <div className="mt-8 grid gap-5 lg:grid-cols-2">
            {orders.map((order) => {
              const primaryAction = orderPrimaryAction(order);
              return (
                <article
                  key={order.order_id}
                  className="rounded-[28px] border border-[#dbe5f2] bg-white/88 p-6 shadow-[0_18px_60px_rgba(61,84,128,0.08)]"
                >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">
                      {order.product.category || "Marketplace"}
                    </div>
                    <h2 className="mt-2 text-[24px] font-bold tracking-tight text-[#0d1424]">
                      {displayProductName(order)}
                    </h2>
                    <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                      {displayProductSummary(order)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] px-4 py-3 text-right">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Status</div>
                    <div className="mt-1 text-[15px] font-semibold capitalize text-[#1a2942]">
                      {order.status.replace(/_/g, " ")}
                    </div>
                  </div>
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-[#e4edf7] bg-[#fbfdff] px-4 py-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Ordered</div>
                    <div className="mt-2 text-[14px] font-medium text-[#23344f]">{formatDate(order.created_at)}</div>
                  </div>
                  <div className="rounded-2xl border border-[#e4edf7] bg-[#fbfdff] px-4 py-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Price</div>
                    <div className="mt-2 text-[14px] font-medium text-[#23344f]">{formatPrice(order.amount_cents)}</div>
                  </div>
                  <div className="rounded-2xl border border-[#e4edf7] bg-[#fbfdff] px-4 py-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Mailing</div>
                    <div className="mt-2 text-[14px] font-medium text-[#23344f]">
                      {order.mailing_status.replace(/_/g, " ")}
                    </div>
                  </div>
                </div>

                {order.filing_deadline ? (
                  <div className="mt-5 rounded-2xl border border-[#f1e3b4] bg-[#fff9eb] px-4 py-3 text-[13px] text-[#775a13]">
                    Filing deadline: {formatDate(order.filing_deadline)}
                  </div>
                ) : null}

                <div className="mt-6 flex flex-wrap gap-3">
                  <Link
                    href={primaryAction.href}
                    className="inline-flex items-center justify-center rounded-full bg-[#0f1728] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a]"
                  >
                    {primaryAction.label}
                  </Link>
                  {order.product.path ? (
                    <Link
                      href={order.product.path}
                      className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-5 py-3 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
                    >
                      {order.product.public_cta_label || order.product.cta_label || "View service"}
                    </Link>
                  ) : null}
                </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </div>
    </main>
  );
}
