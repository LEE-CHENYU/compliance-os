import WizardStep from "../WizardStep";

const FORMS = [
  { key: "1040", label: "Form 1040 (Resident)" },
  { key: "1040-NR", label: "Form 1040-NR (Nonresident)" },
  { key: "FBAR", label: "FBAR (FinCEN 114)" },
  { key: "Form 8938", label: "Form 8938 (FATCA)" },
  { key: "Form 3520", label: "Form 3520 (Foreign Gifts)" },
  { key: "Form 5472", label: "Form 5472 (Foreign-Owned LLC)" },
  { key: "State returns", label: "State tax returns" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function PriorFilingsStep({ value, onChange }: Props) {
  const toggle = (key: string) => {
    onChange(value.includes(key) ? value.filter((v) => v !== key) : [...value, key]);
  };

  return (
    <WizardStep title="Have you filed any of the following before?" subtitle="Check all that apply.">
      <div className="space-y-2">
        {FORMS.map((f) => (
          <label key={f.key} className="flex items-center gap-3 rounded-lg border border-stone-200 p-3 cursor-pointer hover:bg-stone-50">
            <input
              type="checkbox"
              checked={value.includes(f.key)}
              onChange={() => toggle(f.key)}
              className="h-4 w-4 rounded border-stone-300"
            />
            <span className="text-sm">{f.label}</span>
          </label>
        ))}
      </div>
    </WizardStep>
  );
}
