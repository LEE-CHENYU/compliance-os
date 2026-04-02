"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createCase } from "@/lib/api";

export default function NewCase() {
  const router = useRouter();

  useEffect(() => {
    createCase("")
      .then((c) => router.replace(`/case/${c.id}/discovery`));
  }, [router]);

  return (
    <div className="flex items-center justify-center py-20">
      <p className="text-stone-400">Creating your review...</p>
    </div>
  );
}
