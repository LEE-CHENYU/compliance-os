import WizardStep from "../WizardStep";

const SOURCES = [
  { key: "W-2 employment", label: "W-2 Employment (wages)" },
  { key: "1099 contractor", label: "1099 Contractor / Self-Employment" },
  { key: "Investment income", label: "Investment Income (dividends, interest, capital gains)" },
  { key: "Scholarship/fellowship", label: "Scholarship / Fellowship" },
  { key: "Foreign income", label: "Foreign-Source Income" },
  { key: "Rental income", label: "Rental Income" },
  { key: "Other", label: "Other" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function TaxIncomeSourcesStep({ value, onChange }: Props) {
  const toggle = (key: string) => {
    onChange(value.includes(key) ? value.filter((v) => v !== key) : [...value, key]);
  };

  return (
    <WizardStep title="What income sources do you have?" subtitle="Check all that apply.">
      <div className="space-y-2">
        {SOURCES.map((s) => (
          <label key={s.key} className="flex items-center gap-3 rounded-lg border border-stone-200 p-3 cursor-pointer hover:bg-stone-50">
            <input
              type="checkbox"
              checked={value.includes(s.key)}
              onChange={() => toggle(s.key)}
              className="h-4 w-4 rounded border-stone-300"
            />
            <span className="text-sm">{s.label}</span>
          </label>
        ))}
      </div>
    </WizardStep>
  );
}
