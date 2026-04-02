"use client";

import { useCallback, useState } from "react";

interface Props {
  onSubmit: (file: File, instruction: string) => void;
  disabled?: boolean;
}

export default function FormFillerUpload({ onSubmit, disabled }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [instruction, setInstruction] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validate = (f: File): string | null => {
    if (!f.name.toLowerCase().endsWith(".pdf")) return "Please upload a PDF file";
    if (f.size > 20 * 1024 * 1024) return "File exceeds 20MB limit";
    return null;
  };

  const handleFile = useCallback((f: File) => {
    const err = validate(f);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setFile(f);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [disabled, handleFile]
  );

  const handleClick = () => {
    if (disabled) return;
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,application/pdf";
    input.onchange = () => {
      const f = input.files?.[0];
      if (f) handleFile(f);
    };
    input.click();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || disabled) return;
    onSubmit(file, instruction);
  };

  return (
    <div className="p-4 border-t border-blue-50/40 flex-shrink-0 space-y-3">
      {!file ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={handleClick}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
            dragOver
              ? "border-[#5b8dee] bg-blue-50/30"
              : "border-white/70 hover:border-[#5b8dee]/40 bg-white/30"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <p className="text-[13px] text-[#556480]">
            Drop a fillable PDF form here
          </p>
          <p className="text-[11px] text-[#7b8ba5] mt-1">or click to browse</p>
        </div>
      ) : (
        <div className="flex items-center gap-2 bg-white/50 rounded-xl px-3 py-2 border border-white/60">
          <div className="flex-1 min-w-0">
            <p className="text-[12px] font-medium text-[#0d1424] truncate">{file.name}</p>
            <p className="text-[11px] text-[#7b8ba5]">{(file.size / 1024).toFixed(0)} KB</p>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); setFile(null); setError(null); }}
            className="text-[#7b8ba5] hover:text-[#0d1424] text-sm w-6 h-6 flex items-center justify-center rounded-lg hover:bg-white/50"
          >
            &times;
          </button>
        </div>
      )}
      {error && <p className="text-[11px] text-red-500">{error}</p>}

      {file && (
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="Optional instructions..."
            disabled={disabled}
            className="flex-1 px-3 py-2 rounded-xl border border-white/70 bg-white/60 text-[12px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
          />
          <button
            type="submit"
            disabled={disabled}
            className="px-4 py-2 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-[12px] font-medium flex-shrink-0 disabled:opacity-50"
          >
            {disabled ? "..." : "Fill"}
          </button>
        </form>
      )}
    </div>
  );
}
