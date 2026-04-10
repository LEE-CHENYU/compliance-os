"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getMarketplaceProduct, type MarketplaceProduct } from "@/lib/marketplace";


export default function ServiceDetailPage() {
  const params = useParams<{ sku: string }>();
  const sku = typeof params?.sku === "string" ? params.sku : "";
  const [product, setProduct] = useState<MarketplaceProduct | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sku) {
      setError("Missing service SKU");
      return;
    }

    let cancelled = false;
    getMarketplaceProduct(sku, true)
      .then((nextProduct) => {
        if (!cancelled) {
          setProduct(nextProduct);
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load service");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [sku]);

  if (error) {
    return (
      <div className="min-h-screen bg-[#eef4fb] px-6 py-16">
        <div className="mx-auto max-w-4xl rounded-[28px] border border-[#ffd6d6] bg-white p-8 text-[#a33a3a] shadow-[0_24px_70px_rgba(61,84,128,0.06)]">
          {error}
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-[#eef4fb] px-6 py-16">
        <div className="mx-auto max-w-4xl rounded-[28px] border border-white/80 bg-white/82 p-8 text-[#556480] shadow-[0_24px_70px_rgba(61,84,128,0.06)]">
          Loading service...
        </div>
      </div>
    );
  }

  const price = product.price_cents === 0 ? "Free" : `$${(product.price_cents / 100).toFixed(0)}`;
  const primaryHref = product.path || (product.active ? `/services/${product.sku}` : "/services");

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#edf3f9_0%,#f7faff_100%)] px-6 py-12">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/services"
          className="inline-flex rounded-full border border-white/80 bg-white/75 px-4 py-2 text-sm font-medium text-[#52627d] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur hover:text-[#1a2036]"
        >
          ← Back to services
        </Link>

        <div className="mt-6 rounded-[32px] border border-white/80 bg-white/84 p-8 shadow-[0_28px_80px_rgba(61,84,128,0.08)] backdrop-blur md:p-10">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
                {(product.category || "service").replace(/_/g, " ")} · {product.tier.replace(/_/g, ".")}
              </div>
              <h1 className="mt-3 text-[42px] font-extrabold tracking-tight text-[#0d1424]">{product.name}</h1>
              {product.headline ? <p className="mt-4 max-w-3xl text-[18px] leading-8 text-[#435774]">{product.headline}</p> : null}
            </div>
            <div className="rounded-[24px] border border-[#dbe5f2] bg-[#f8fbff] px-5 py-4 text-right">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Price</div>
              <div className="mt-2 text-[26px] font-bold text-[#0d1424]">{price}</div>
            </div>
          </div>

          <div className="mt-8 grid gap-8 lg:grid-cols-[1.1fr,0.9fr]">
            <div>
              <p className="text-[15px] leading-7 text-[#5f6f88]">{product.description}</p>
              <div className="mt-6 flex flex-wrap gap-2">
                {product.filing_method ? (
                  <span className="rounded-full border border-[#dbe5f2] bg-white px-3 py-1.5 text-[12px] font-medium text-[#55708f]">
                    Filing: {product.filing_method}
                  </span>
                ) : null}
                {product.fulfillment_mode ? (
                  <span className="rounded-full border border-[#dbe5f2] bg-white px-3 py-1.5 text-[12px] font-medium text-[#55708f]">
                    Mode: {product.fulfillment_mode}
                  </span>
                ) : null}
              </div>

              <div className="mt-8 rounded-[24px] border border-[#dbe5f2] bg-[#fbfdff] p-5">
                <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">What this product is for</div>
                <ul className="mt-4 space-y-3">
                  {product.highlights.map((highlight) => (
                    <li key={highlight} className="flex gap-3 text-[14px] leading-6 text-[#435774]">
                      <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-[#5b8dee]" />
                      <span>{highlight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <aside className="rounded-[24px] border border-[#dbe5f2] bg-[#0f1728] p-6 text-white shadow-[0_24px_60px_rgba(9,18,36,0.2)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ca2cc]">
                {product.active ? "Availability" : "Upcoming"}
              </div>
              <div className="mt-3 text-[24px] font-bold">
                {product.active ? "Ready for the next implementation slice" : "Configured but not launched yet"}
              </div>
              <p className="mt-4 text-[14px] leading-7 text-[#cad6ec]">
                {product.active
                  ? "The catalog entry is live now. Checkout and intake will layer on top of this SKU instead of inventing one-off flows per product."
                  : "This SKU is intentionally visible in the config-backed catalog so the storefront and roadmap stay aligned before checkout goes live."}
              </p>
              <Link
                href={primaryHref}
                className={`mt-6 inline-flex rounded-full px-5 py-3 text-[14px] font-semibold transition ${
                  product.active
                    ? "bg-white text-[#10203d] hover:bg-[#eef4ff]"
                    : "border border-white/20 bg-transparent text-white hover:border-white/35"
                }`}
              >
                {product.cta_label || (product.active ? "View workflow" : "Back to catalog")}
              </Link>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
