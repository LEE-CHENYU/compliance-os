"use client";

import { type Lang } from "@/lib/i18n";

/** Glassmorphic two-state pill — matches the rest of the find-lawyer chrome. */
export default function LangToggle({
  lang,
  onChange,
}: {
  lang: Lang;
  onChange: (l: Lang) => void;
}) {
  const isZh = lang === "zh";
  return (
    <div
      role="group"
      aria-label="Language"
      className="inline-flex items-center rounded-full border border-white/80 bg-white/75 p-1 text-[12px] font-semibold shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur"
    >
      <button
        type="button"
        onClick={() => onChange("en")}
        aria-pressed={!isZh}
        className={`rounded-full px-3 py-1 transition ${
          !isZh
            ? "bg-[#5b8dee] text-white shadow-[0_4px_12px_rgba(91,141,238,0.3)]"
            : "text-[#52627d] hover:text-[#1a2036]"
        }`}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => onChange("zh")}
        aria-pressed={isZh}
        className={`rounded-full px-3 py-1 transition ${
          isZh
            ? "bg-[#5b8dee] text-white shadow-[0_4px_12px_rgba(91,141,238,0.3)]"
            : "text-[#52627d] hover:text-[#1a2036]"
        }`}
      >
        中文
      </button>
    </div>
  );
}
