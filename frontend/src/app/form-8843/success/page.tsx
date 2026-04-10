import { Suspense } from "react";

import SuccessContent from "./SuccessContent";

export default function Form8843SuccessPage({
  searchParams,
}: {
  searchParams: { orderId?: string };
}) {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#eef5fb_0%,#f8fbff_100%)] px-6 py-16">
      <Suspense
        fallback={
          <div className="mx-auto max-w-3xl rounded-[32px] border border-white/80 bg-white/82 p-8 text-[16px] text-[#556480] shadow-[0_28px_80px_rgba(61,84,128,0.08)] backdrop-blur md:p-12">
            Loading order...
          </div>
        }
      >
        <SuccessContent orderId={searchParams.orderId || ""} />
      </Suspense>
    </div>
  );
}
