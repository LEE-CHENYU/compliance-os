"use client";

import { useCallback, useRef, useState } from "react";

const MAX_SIZE = 20 * 1024 * 1024;
const ALLOWED = ["application/pdf", "image/png", "image/jpeg", "text/csv", "text/plain"];

interface Props {
  onDrop: (file: File) => void;
  disabled?: boolean;
  children?: React.ReactNode;
  className?: string;
  testId?: string;
}

export default function FileDropZone({ onDrop, disabled, children, className, testId }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const validate = (file: File): string | null => {
    if (!ALLOWED.includes(file.type)) return `File type ${file.type} not allowed`;
    if (file.size > MAX_SIZE) return "File exceeds 20MB limit";
    return null;
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const file = e.dataTransfer.files[0];
      if (!file) return;
      const err = validate(file);
      if (err) { setError(err); return; }
      setError(null);
      onDrop(file);
    },
    [onDrop, disabled]
  );

  const handleClick = () => {
    if (disabled) return;
    inputRef.current?.click();
  };

  return (
    <div
      data-testid={testId}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={handleClick}
      className={`cursor-pointer rounded-lg border-2 border-dashed transition-colors ${
        dragOver ? "border-stone-500 bg-stone-100" : "border-stone-300 hover:border-stone-400"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className || ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED.join(",")}
        data-testid={testId ? `${testId}-input` : undefined}
        className="sr-only"
        disabled={disabled}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (!file) return;
          const err = validate(file);
          if (err) { setError(err); return; }
          setError(null);
          onDrop(file);
          event.target.value = "";
        }}
      />
      {children}
      {error && <p className="text-xs text-red-500 mt-1 px-3 pb-2">{error}</p>}
    </div>
  );
}
