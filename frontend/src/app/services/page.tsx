"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listMarketplaceProducts, type MarketplaceProduct } from "@/lib/marketplace";


function ProductCard({ product }: { product: MarketplaceProduct }) {
  const price = product.price_cents === 0 ? "Free" : `$${(product.price_cents / 100).toFixed(0)}`;
  const href = product.path || `/services/${product.sku}`;
  const categoryLabel = (product.category || "service").replace(/_/g, " ");
  const name = product.public_name || product.name;
  const headline = product.public_headline || product.headline;
  const description = product.public_description || product.description;
  const highlights = product.public_highlights?.length ? product.public_highlights : product.highlights;
  const ctaLabel = product.public_cta_label || product.cta_label || (product.active ? "View service" : "Coming soon");

  return (
    <article className={`rounded-[28px] border p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)] ${
      product.active ? "border-white/80 bg-white/88" : "border-[#dbe5f2] bg-[#f7faff]"
    }`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">
            {categoryLabel}
          </div>
          <h2 className="mt-3 text-[26px] font-bold tracking-tight text-[#0d1424]">{name}</h2>
        </div>
        <div className="rounded-2xl border border-[#dbe5f2] bg-[#eef5ff] px-4 py-2 text-[14px] font-bold text-[#315aa5]">
          {price}
        </div>
      </div>

      {headline ? <p className="mt-4 text-[15px] leading-7 text-[#435774]">{headline}</p> : null}
      <p className="mt-4 text-[14px] leading-6 text-[#5f6f88]">{description}</p>

      <div className="mt-5 flex flex-wrap gap-2">
        {product.filing_method ? (
          <span className="rounded-full border border-[#dbe5f2] bg-white px-3 py-1.5 text-[12px] font-medium text-[#55708f]">
            {product.filing_method}
          </span>
        ) : null}
      </div>

      <ul className="mt-6 space-y-3">
        {highlights.map((highlight) => (
          <li key={highlight} className="flex gap-3 text-[14px] leading-6 text-[#435774]">
            <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-[#5b8dee]" />
            <span>{highlight}</span>
          </li>
        ))}
      </ul>

      <div className="mt-8">
        <Link
          href={href}
          className={`inline-flex rounded-full px-5 py-3 text-[14px] font-semibold transition ${
            product.active
              ? "bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] hover:bg-[#4f82de]"
              : "border border-[#dbe5f2] bg-white text-[#40536f] hover:border-[#c4d4ea]"
          }`}
        >
          {ctaLabel}
        </Link>
      </div>
    </article>
  );
}

export default function ServicesPage() {
  const [products, setProducts] = useState<MarketplaceProduct[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listMarketplaceProducts()
      .then((items) => {
        if (!cancelled) {
          setProducts(items);
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load services");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(91,141,238,0.14),_transparent_30%),linear-gradient(180deg,#edf3f9_0%,#f6f9fd_100%)] px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="rounded-[32px] border border-white/80 bg-white/78 p-8 shadow-[0_28px_80px_rgba(61,84,128,0.08)] backdrop-blur md:p-10">
          <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">Services</div>
          <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h1 className="text-[40px] font-extrabold tracking-tight text-[#0d1424]">Get help with filings and document review</h1>
              <p className="mt-4 max-w-3xl text-[16px] leading-7 text-[#556480]">
                Choose the service you need. Guardian can help with tax filing, immigration document review, startup paperwork, and attorney-supported OPT applications.
              </p>
            </div>
            <Link
              href="/form-8843"
              className="inline-flex rounded-full bg-[#5b8dee] px-5 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de]"
            >
              Start with Form 8843
            </Link>
          </div>
        </div>

        {error ? (
          <div className="mt-6 rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
            {error}
          </div>
        ) : null}

        <section className="mt-8">
          <div className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-[#6d7c95]">Available now</div>
          <div className="grid gap-6 lg:grid-cols-2">
            {products.map((product) => (
              <ProductCard key={product.sku} product={product} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
