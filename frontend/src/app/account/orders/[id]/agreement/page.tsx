"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { isLoggedIn } from "@/lib/auth";
import {
  getMarketplaceAgreement,
  getMarketplaceOrder,
  signMarketplaceAgreement,
  type MarketplaceAgreementResponse,
  type MarketplaceOrder,
} from "@/lib/marketplace";


export const dynamic = "force-dynamic";

export default function OrderAgreementPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const orderId = typeof params?.id === "string" ? params.id : "";
  const agreementRef = useRef<HTMLDivElement | null>(null);
  const [order, setOrder] = useState<MarketplaceOrder | null>(null);
  const [agreement, setAgreement] = useState<MarketplaceAgreementResponse | null>(null);
  const [signature, setSignature] = useState("");
  const [scrolledToBottom, setScrolledToBottom] = useState(false);
  const [loading, setLoading] = useState(true);
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) {
      setError("Missing order ID");
      setLoading(false);
      return;
    }

    if (!isLoggedIn()) {
      router.replace(`/login?next=${encodeURIComponent(`/account/orders/${orderId}/agreement`)}`);
      return;
    }

    let cancelled = false;
    Promise.all([
      getMarketplaceOrder(orderId),
      getMarketplaceAgreement(orderId),
    ])
      .then(([nextOrder, nextAgreement]) => {
        if (cancelled) {
          return;
        }
        setOrder(nextOrder);
        setAgreement(nextAgreement);
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load agreement");
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

  async function handleSign() {
    if (!agreement || !signature.trim()) {
      return;
    }
    setSigning(true);
    setError(null);
    try {
      await signMarketplaceAgreement(orderId, {
        signature: signature.trim(),
        agreement_text_snapshot: agreement.agreement_text,
      });
      router.push(`/account/orders/${orderId}`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not sign agreement");
      setSigning(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#eef4fb] px-6 py-16">
        <div className="mx-auto max-w-5xl rounded-[28px] border border-white/80 bg-white/82 p-8 text-[#556480] shadow-[0_24px_70px_rgba(61,84,128,0.06)]">
          Loading agreement...
        </div>
      </div>
    );
  }

  if (error || !order || !agreement) {
    return (
      <div className="min-h-screen bg-[#eef4fb] px-6 py-16">
        <div className="mx-auto max-w-5xl rounded-[28px] border border-[#ffd6d6] bg-white p-8 text-[#a33a3a] shadow-[0_24px_70px_rgba(61,84,128,0.06)]">
          {error || "Could not load this agreement"}
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#edf3f9_0%,#f7faff_100%)] px-6 py-12">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex rounded-full border border-white/80 bg-white/80 px-4 py-2 text-sm font-medium text-[#40536f] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur hover:text-[#1a2036]"
          >
            ← Back to dashboard
          </Link>
          <Link
            href={`/account/orders/${orderId}`}
            className="inline-flex rounded-full border border-white/80 bg-white/75 px-4 py-2 text-sm font-medium text-[#52627d] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur hover:text-[#1a2036]"
          >
            Back to order
          </Link>
        </div>

        <section className="mt-6 rounded-[32px] border border-white/80 bg-white/84 p-8 shadow-[0_28px_80px_rgba(61,84,128,0.08)] md:p-10">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">Limited scope agreement</div>
              <h1 className="mt-3 text-[38px] font-extrabold tracking-tight text-[#0d1424]">{order.product.name}</h1>
              <p className="mt-4 max-w-3xl text-[16px] leading-7 text-[#556480]">
                Review the engagement carefully. The signature field only unlocks after you reach the bottom of the agreement text.
              </p>
            </div>
            <div className="rounded-[24px] border border-[#dbe5f2] bg-[#f8fbff] px-5 py-4 text-right">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Order status</div>
              <div className="mt-2 text-[20px] font-bold text-[#0d1424]">{order.status.replace(/_/g, " ")}</div>
            </div>
          </div>

          <div
            ref={agreementRef}
            onScroll={(event) => {
              const target = event.currentTarget;
              const remaining = target.scrollHeight - target.scrollTop - target.clientHeight;
              if (remaining <= 12) {
                setScrolledToBottom(true);
              }
            }}
            className="mt-8 h-[420px] overflow-y-auto rounded-[28px] border border-[#dbe5f2] bg-[#fbfdff] p-6 font-[ui-monospace,SFMono-Regular,Menlo,monospace] text-[14px] leading-7 text-[#364863]"
          >
            <pre className="whitespace-pre-wrap">{agreement.agreement_text}</pre>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-[1fr,auto]">
            <label className="rounded-[24px] border border-[#dbe5f2] bg-white p-4">
              <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Typed signature</div>
              <input
                value={signature}
                onChange={(event) => setSignature(event.target.value)}
                disabled={!order.intake_complete || !scrolledToBottom || agreement.signed}
                className="mt-2 w-full rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] px-4 py-3 text-[15px] text-[#1a2942] outline-none transition focus:border-[#9db8e6] disabled:cursor-not-allowed disabled:bg-[#f2f5fa]"
                placeholder={!order.intake_complete ? "Complete intake on the order page first" : scrolledToBottom ? "Type your full legal name" : "Scroll to the bottom to unlock"}
              />
            </label>
            <button
              type="button"
              onClick={() => void handleSign()}
              disabled={!order.intake_complete || !scrolledToBottom || !signature.trim() || signing || agreement.signed}
              className="self-end inline-flex rounded-full bg-[#0f1728] px-6 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a] disabled:cursor-not-allowed disabled:bg-[#8b97ad]"
            >
              {agreement.signed ? "Already signed" : signing ? "Signing..." : "Sign agreement"}
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
