"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Case, listCases } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listCases()
      .then((data) => setCases(data.cases))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-semibold">Start a Compliance Review</h2>
        <p className="text-stone-500">
          Get guided through your tax, immigration, or corporate compliance situation.
        </p>
      </div>

      <div className="flex justify-center">
        <button
          onClick={() => router.push("/case/new")}
          className="rounded-lg bg-stone-800 px-6 py-3 text-white font-medium hover:bg-stone-700 transition-colors"
        >
          Start New Review
        </button>
      </div>

      {!loading && cases.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide">
            Previous Reviews
          </h3>
          <div className="space-y-2">
            {cases.map((c) => (
              <button
                key={c.id}
                onClick={() => router.push(`/case/${c.id}`)}
                className="w-full text-left rounded-lg border border-stone-200 bg-white p-4 hover:border-stone-300 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium capitalize">{c.workflow_type || "General"} Review</span>
                    <span className="ml-2 text-xs text-stone-400 capitalize">{c.status}</span>
                  </div>
                  <span className="text-xs text-stone-400">
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
