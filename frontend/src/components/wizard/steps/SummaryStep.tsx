import WizardStep from "../WizardStep";

interface Props {
  answers: Record<string, unknown>;
}

const TRACK_CONFIG: { prefix: string; title: string; fields: Record<string, string> }[] = [
  {
    prefix: "",
    title: "General",
    fields: {
      concern_area: "Concern Areas",
      existing_help: "Working With",
      timeline_urgency: "Upcoming Deadline",
    },
  },
  {
    prefix: "tax_",
    title: "Tax Filing",
    fields: {
      tax_residency_status: "Tax Residency",
      tax_filing_stage: "Filing Stage",
      tax_prior_filings: "Prior Filings",
      tax_income_sources: "Income Sources",
      tax_entities: "Business Entities",
    },
  },
  {
    prefix: "imm_",
    title: "Immigration",
    fields: {
      imm_visa_category: "Visa Status",
      imm_subdomain: "Immigration Need",
      imm_stage: "Case Stage",
    },
  },
  {
    prefix: "corp_",
    title: "Corporate Compliance",
    fields: {
      corp_entities: "Entities",
      corp_obligations: "Obligations",
    },
  },
];

function formatValue(value: unknown): string | null {
  if (value === undefined || value === null) return null;
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    if (typeof value[0] === "object") {
      return (value as { name: string }[]).map((e) => e.name).join(", ");
    }
    return value.join(", ");
  }
  if (typeof value === "object") {
    const obj = value as Record<string, string>;
    return [obj.date, obj.description].filter(Boolean).join(" — ");
  }
  return String(value);
}

export default function SummaryStep({ answers }: Props) {
  const concerns = (answers.concern_area as string[]) || [];

  const visibleTracks = TRACK_CONFIG.filter((track) => {
    if (track.prefix === "") return true;
    if (track.prefix === "tax_") return concerns.includes("Tax Filing");
    if (track.prefix === "imm_") return concerns.includes("Immigration");
    if (track.prefix === "corp_") return concerns.includes("Corporate Compliance");
    return false;
  });

  return (
    <WizardStep title="Review your information" subtitle="Please confirm before proceeding, or go back to edit.">
      <div className="space-y-6">
        {visibleTracks.map((track) => {
          const entries = Object.entries(track.fields)
            .map(([key, label]) => ({ key, label, display: formatValue(answers[key]) }))
            .filter((e) => e.display);

          if (entries.length === 0) return null;

          return (
            <div key={track.prefix || "general"}>
              <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide mb-2">
                {track.title}
              </h3>
              <div className="space-y-2">
                {entries.map((e) => (
                  <div key={e.key} className="flex justify-between rounded-lg border border-stone-200 bg-white p-3">
                    <span className="text-sm text-stone-500">{e.label}</span>
                    <span className="text-sm font-medium text-right max-w-[60%]">{e.display}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </WizardStep>
  );
}
