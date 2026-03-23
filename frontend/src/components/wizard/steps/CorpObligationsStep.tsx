import WizardStep from "../WizardStep";

const OBLIGATIONS = [
  { key: "Annual report", label: "Annual Report Filing" },
  { key: "Registered agent", label: "Registered Agent Maintenance" },
  { key: "Corporate minutes", label: "Corporate Minutes / Resolutions" },
  { key: "EIN application", label: "EIN Application or Correction" },
  { key: "Dissolution", label: "Entity Dissolution" },
  { key: "New formation", label: "New Entity Formation" },
  { key: "Other", label: "Other" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function CorpObligationsStep({ value, onChange }: Props) {
  const toggle = (key: string) => {
    onChange(value.includes(key) ? value.filter((v) => v !== key) : [...value, key]);
  };

  return (
    <WizardStep title="What corporate obligations apply?" subtitle="Select all that apply.">
      <div className="space-y-2">
        {OBLIGATIONS.map((o) => (
          <label key={o.key} className="flex items-center gap-3 rounded-lg border border-stone-200 p-3 cursor-pointer hover:bg-stone-50">
            <input
              type="checkbox"
              checked={value.includes(o.key)}
              onChange={() => toggle(o.key)}
              className="h-4 w-4 rounded border-stone-300"
            />
            <span className="text-sm">{o.label}</span>
          </label>
        ))}
      </div>
    </WizardStep>
  );
}
