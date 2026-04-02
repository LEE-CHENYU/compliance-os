"use client";

export type ChatMode = "guardian" | "form-filler";

interface ModeOption {
  id: ChatMode;
  label: string;
}

const MODES: ModeOption[] = [
  { id: "guardian", label: "Guardian" },
  { id: "form-filler", label: "Form Filler" },
];

interface Props {
  active: ChatMode;
  onChange: (mode: ChatMode) => void;
}

export default function ModeBar({ active, onChange }: Props) {
  return (
    <div className="flex gap-1.5 px-5 py-3 border-b border-blue-50/40 flex-shrink-0">
      {MODES.map((mode) => (
        <button
          key={mode.id}
          onClick={() => onChange(mode.id)}
          className={`px-3.5 py-1.5 rounded-xl text-[12px] font-medium transition-all ${
            active === mode.id
              ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-sm"
              : "bg-white/50 text-[#556480] border border-white/60 hover:bg-white/70 hover:text-[#3a5a8c]"
          }`}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}
