import WizardStep from "../WizardStep";

interface Props {
  answers: Record<string, unknown>;
}

const LABELS: Record<string, string> = {
  concern_area: "Concerns",
  current_stage: "Current Stage",
  existing_help: "Working With",
  residency_status: "Residency Status",
  timeline_urgency: "Upcoming Deadline",
  prior_filings: "Prior Filings",
  entities: "Business Entities",
};

export default function SummaryStep({ answers }: Props) {
  return (
    <WizardStep title="Here's what I understand about your situation" subtitle="Please review and confirm, or go back to edit.">
      <div className="space-y-3">
        {Object.entries(answers).map(([key, value]) => {
          if (value === undefined || value === null) return null;
          const label = LABELS[key] || key;
          let display: string;
          if (Array.isArray(value)) {
            if (value.length === 0) return null;
            if (typeof value[0] === "object") {
              display = (value as { name: string }[]).map((e) => e.name).join(", ");
            } else {
              display = value.join(", ");
            }
          } else if (typeof value === "object") {
            const obj = value as Record<string, string>;
            display = [obj.date, obj.description].filter(Boolean).join(" — ");
          } else {
            display = String(value);
          }
          if (!display) return null;
          return (
            <div key={key} className="flex justify-between rounded-lg border border-stone-200 bg-white p-3">
              <span className="text-sm text-stone-500">{label}</span>
              <span className="text-sm font-medium text-right max-w-[60%]">{display}</span>
            </div>
          );
        })}
      </div>
    </WizardStep>
  );
}
