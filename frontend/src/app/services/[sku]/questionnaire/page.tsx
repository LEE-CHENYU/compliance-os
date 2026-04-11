"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { isLoggedIn } from "@/lib/auth";
import {
  createMarketplaceOrder,
  getMarketplaceProduct,
  getMarketplaceQuestionnaire,
  submitMarketplaceQuestionnaire,
  type MarketplaceProduct,
  type MarketplaceQuestionnaireConfig,
  type MarketplaceQuestionnaireResult,
} from "@/lib/marketplace";


export const dynamic = "force-dynamic";

function formatPrice(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

export default function MarketplaceQuestionnairePage() {
  const router = useRouter();
  const params = useParams<{ sku: string }>();
  const sku = typeof params?.sku === "string" ? params.sku : "";
  const [product, setProduct] = useState<MarketplaceProduct | null>(null);
  const [config, setConfig] = useState<MarketplaceQuestionnaireConfig | null>(null);
  const [responses, setResponses] = useState<Record<string, boolean>>({});
  const [result, setResult] = useState<MarketplaceQuestionnaireResult | null>(null);
  const [selectedMode, setSelectedMode] = useState<"execution" | "advisory" | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [creatingOrder, setCreatingOrder] = useState(false);

  useEffect(() => {
    if (!sku) {
      setError("Missing product SKU");
      setLoading(false);
      return;
    }

    if (!isLoggedIn()) {
      router.replace(`/login?next=${encodeURIComponent(`/services/${sku}/questionnaire`)}`);
      return;
    }

    let cancelled = false;
    Promise.all([
      getMarketplaceProduct(sku, true),
      getMarketplaceQuestionnaire(sku),
    ])
      .then(([nextProduct, nextConfig]) => {
        if (cancelled) {
          return;
        }
        setProduct(nextProduct);
        setConfig(nextConfig);
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load questionnaire");
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
  }, [router, sku]);

  const recommendedSku = useMemo(() => (
    selectedMode === "advisory" ? "opt_advisory" : "opt_execution"
  ), [selectedMode]);

  async function handleEvaluate() {
    if (!config) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const questionnaireResult = await submitMarketplaceQuestionnaire(
        sku,
        config.sections.flatMap((section) => section.items.map((item) => ({
          item_id: item.id,
          checked: Boolean(responses[item.id]),
        }))),
      );
      setResult(questionnaireResult);
      setSelectedMode(questionnaireResult.recommendation === "advisory" ? "advisory" : "execution");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not evaluate questionnaire");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleContinue() {
    if (!result || !selectedMode) {
      return;
    }
    setCreatingOrder(true);
    setError(null);
    try {
      const order = await createMarketplaceOrder(recommendedSku, {
        questionnaire_response_id: result.questionnaire_response_id,
        chosen_mode: selectedMode,
      });
      router.push(`/account/orders/${order.order_id}${!order.intake_complete ? "?task=intake" : ""}`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not create order");
      setCreatingOrder(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#eef4fb] px-6 py-16">
        <div className="mx-auto max-w-5xl rounded-[28px] border border-white/80 bg-white/82 p-8 text-[#556480] shadow-[0_24px_70px_rgba(61,84,128,0.06)]">
          Loading questionnaire...
        </div>
      </div>
    );
  }

  if (error && !product && !config) {
    return (
      <div className="min-h-screen bg-[#eef4fb] px-6 py-16">
        <div className="mx-auto max-w-5xl rounded-[28px] border border-[#ffd6d6] bg-white p-8 text-[#a33a3a] shadow-[0_24px_70px_rgba(61,84,128,0.06)]">
          {error}
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#edf3f9_0%,#f7faff_100%)] px-6 py-12">
      <div className="mx-auto max-w-5xl">
        <Link
          href={product?.path || "/services"}
          className="inline-flex rounded-full border border-white/80 bg-white/75 px-4 py-2 text-sm font-medium text-[#52627d] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur hover:text-[#1a2036]"
        >
          ← Back to service
        </Link>

        <section className="mt-6 rounded-[32px] border border-white/80 bg-white/84 p-8 shadow-[0_28px_80px_rgba(61,84,128,0.08)] md:p-10">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">OPT qualification</div>
              <h1 className="mt-3 text-[40px] font-extrabold tracking-tight text-[#0d1424]">
                {config?.title || "Find the right OPT lane"}
              </h1>
              <p className="mt-4 max-w-3xl text-[16px] leading-7 text-[#556480]">
                {config?.description || "Guardian uses this checklist to route the case toward the right attorney-backed workflow."}
              </p>
            </div>
            {product ? (
              <div className="rounded-[24px] border border-[#dbe5f2] bg-[#f8fbff] px-5 py-4 text-right">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Starting from</div>
                <div className="mt-2 text-[26px] font-bold text-[#0d1424]">{formatPrice(product.price_cents)}</div>
              </div>
            ) : null}
          </div>

          {error ? (
            <div className="mt-6 rounded-[24px] border border-[#ffd6d6] bg-[#fff4f4] px-5 py-4 text-[14px] text-[#a33a3a]">
              {error}
            </div>
          ) : null}

          <div className="mt-8 space-y-6">
            {config?.sections.map((section) => (
              <section key={section.id} className="rounded-[26px] border border-[#dbe5f2] bg-[#fbfdff] p-6">
                <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">
                  {section.required_for_execution === "all_unchecked" ? "Should be clear before filing" : "Needed for streamlined filing"}
                </div>
                <h2 className="mt-2 text-[24px] font-bold tracking-tight text-[#0d1424]">{section.title}</h2>
                <div className="mt-5 space-y-4">
                  {section.items.map((item) => (
                    <label
                      key={item.id}
                      className="flex items-start gap-4 rounded-[22px] border border-[#dbe5f2] bg-white px-4 py-4 text-[15px] leading-6 text-[#435774]"
                    >
                      <input
                        type="checkbox"
                        checked={Boolean(responses[item.id])}
                        onChange={(event) => setResponses((current) => ({ ...current, [item.id]: event.target.checked }))}
                        className="mt-1 h-5 w-5 rounded border-[#b8c8df] text-[#5b8dee] focus:ring-[#5b8dee]"
                      />
                      <span>{item.label}</span>
                    </label>
                  ))}
                </div>
              </section>
            ))}
          </div>

          {!result ? (
            <button
              type="button"
              onClick={() => void handleEvaluate()}
              disabled={submitting}
              className="mt-8 inline-flex rounded-full bg-[#0f1728] px-6 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a] disabled:cursor-not-allowed disabled:bg-[#8b97ad]"
            >
              {submitting ? "Evaluating..." : "See recommendation"}
            </button>
          ) : (
            <section className="mt-8 rounded-[28px] border border-[#dbe5f2] bg-[#0f1728] p-6 text-white">
              <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#8ca2cc]">Recommended plan</div>
              <h2 className="mt-3 text-[28px] font-bold">
                {result.recommendation === "execution"
                  ? "You can continue with filing support"
                  : "You should start with strategy review"}
              </h2>
              <p className="mt-4 max-w-3xl text-[15px] leading-7 text-[#cad6ec]">
                {result.execution_reason || result.advisory_reason}
              </p>

              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setSelectedMode("execution")}
                  className={`rounded-[24px] border px-5 py-5 text-left transition ${
                    selectedMode === "execution"
                      ? "border-white bg-white text-[#10203d]"
                      : "border-white/20 bg-transparent text-white"
                  }`}
                >
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-70">Filing support</div>
                  <div className="mt-2 text-[22px] font-bold">$199</div>
                  <p className="mt-3 text-[14px] leading-6 opacity-90">
                    For straightforward OPT cases where the attorney can verify, file, and confirm receipt.
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedMode("advisory")}
                  className={`rounded-[24px] border px-5 py-5 text-left transition ${
                    selectedMode === "advisory"
                      ? "border-white bg-white text-[#10203d]"
                      : "border-white/20 bg-transparent text-white"
                  }`}
                >
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-70">Strategy review</div>
                  <div className="mt-2 text-[22px] font-bold">$499</div>
                  <p className="mt-3 text-[14px] leading-6 opacity-90">
                    For cases with complexity flags, timing questions, or facts that should be reviewed strategically.
                  </p>
                </button>
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => void handleContinue()}
                  disabled={!selectedMode || creatingOrder}
                  className="inline-flex rounded-full bg-[#5b8dee] px-6 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de] disabled:cursor-not-allowed disabled:bg-[#7ea7ef]"
                >
                  {creatingOrder ? "Creating order..." : `Continue with ${selectedMode === "advisory" ? "strategy review" : "filing support"}`}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setResult(null);
                    setSelectedMode(null);
                  }}
                  className="inline-flex rounded-full border border-white/20 bg-transparent px-6 py-3 text-[14px] font-semibold text-white"
                >
                  Re-run checklist
                </button>
              </div>
            </section>
          )}
        </section>
      </div>
    </main>
  );
}
