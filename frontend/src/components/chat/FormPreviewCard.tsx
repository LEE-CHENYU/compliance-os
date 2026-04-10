"use client";

import { useState } from "react";

export interface FieldProposal {
  field_name: string;
  field_type: string;
  field_label?: string;
  field_context?: string;
  page?: number | null;
  proposed_value: string;
  confidence: string;
  source: string;
}

interface Props {
  fields: FieldProposal[];
  formFieldCount: number;
  filledCount: number;
  unfilledCount: number;
  onGenerate: (values: Record<string, string>) => void;
  onCancel: () => void;
  disabled?: boolean;
}

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-red-100 text-red-700",
};

export default function FormPreviewCard({
  fields,
  formFieldCount,
  filledCount,
  unfilledCount,
  onGenerate,
  onCancel,
  disabled,
}: Props) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const f of fields) {
      initial[f.field_name] = f.proposed_value || "";
    }
    return initial;
  });

  const handleGenerate = () => {
    onGenerate(values);
  };

  const sorted = [...fields].sort((a, b) => {
    const aFilled = values[a.field_name] ? 0 : 1;
    const bFilled = values[b.field_name] ? 0 : 1;
    return aFilled - bFilled;
  });

  return (
    <div className="bg-white/60 backdrop-blur rounded-2xl border border-white/60 overflow-hidden">
      <div className="px-4 py-3 border-b border-blue-50/40">
        <div className="text-[13px] font-semibold text-[#0d1424]">Form Preview</div>
        <div className="text-[11px] text-[#7b8ba5] mt-0.5">
          {filledCount} of {formFieldCount} fields filled
          {unfilledCount > 0 && ` \u00b7 ${unfilledCount} need your input`}
        </div>
      </div>

      <div className="max-h-80 overflow-y-auto divide-y divide-blue-50/30">
        {sorted.map((field) => {
          const displayLabel = field.field_label?.trim() || field.field_name;
          const showTechnicalName = Boolean(field.field_name && field.field_name !== displayLabel);
          const showContext = Boolean(field.field_context && field.field_context !== displayLabel);

          return (
            <div key={field.field_name} className="px-4 py-2.5">
              <div className="flex items-start gap-2 mb-1">
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-medium text-[#556480] truncate">
                    {displayLabel}
                  </div>
                  {(showTechnicalName || field.field_type) && (
                    <div className="text-[10px] text-[#7b8ba5] mt-0.5 truncate">
                      {showTechnicalName && (
                        <span className="font-mono">PDF field: {field.field_name}</span>
                      )}
                      {showTechnicalName && field.field_type && " \u00b7 "}
                      {field.field_type && <span>{field.field_type}</span>}
                    </div>
                  )}
                </div>
                {field.confidence && (
                  <span
                    className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md ${
                      CONFIDENCE_STYLES[field.confidence] || "bg-gray-100 text-gray-600"
                    }`}
                    title={field.source}
                  >
                    {field.confidence}
                  </span>
                )}
              </div>
              {showContext && (
                <p className="text-[10px] text-[#7b8ba5] mb-1.5 leading-4">
                  {field.field_context}
                </p>
              )}
              <input
                value={values[field.field_name] || ""}
                onChange={(e) =>
                  setValues((prev) => ({ ...prev, [field.field_name]: e.target.value }))
                }
                placeholder="Enter value..."
                className="w-full px-2.5 py-1.5 rounded-lg border border-white/70 bg-white/60 text-[12px] text-[#0d1424] focus:border-[#5b8dee] focus:outline-none focus:ring-1 focus:ring-blue-200/30"
              />
              {field.source && (
                <p className="text-[10px] text-[#7b8ba5] mt-0.5 truncate" title={field.source}>
                  Source: {field.source}
                </p>
              )}
            </div>
          );
        })}
      </div>

      <div className="px-4 py-3 border-t border-blue-50/40 flex gap-2 justify-end">
        <button
          onClick={onCancel}
          disabled={disabled}
          className="px-3.5 py-2 rounded-xl text-[12px] font-medium bg-white/70 border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={handleGenerate}
          disabled={disabled}
          className="px-3.5 py-2 rounded-xl text-[12px] font-medium bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white disabled:opacity-50"
        >
          {disabled ? "Generating..." : "Generate PDF"}
        </button>
      </div>
    </div>
  );
}
