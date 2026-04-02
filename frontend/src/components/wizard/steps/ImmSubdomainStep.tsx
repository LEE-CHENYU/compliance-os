import WizardStep from "../WizardStep";

// Subdomain options change based on visa category
const SUBDOMAIN_OPTIONS: Record<string, { key: string; label: string; description?: string }[]> = {
  "F-1": [
    { key: "CPT/OPT authorization", label: "CPT or OPT Work Authorization" },
    { key: "STEM OPT extension", label: "STEM OPT Extension" },
    { key: "Status maintenance", label: "Status Maintenance (travel, I-20 updates)" },
    { key: "Program transfer", label: "School or Program Transfer" },
    { key: "Change of status", label: "Change of Status to Another Visa" },
  ],
  "J-1": [
    { key: "Program compliance", label: "Program Compliance" },
    { key: "Waiver of 2-year rule", label: "Waiver of 2-Year Home Residency Requirement" },
    { key: "Change of status", label: "Change of Status" },
  ],
  "H-1B": [
    { key: "Petition filing", label: "New H-1B Petition (Registration / Cap)" },
    { key: "Extension/transfer", label: "Extension or Employer Transfer" },
    { key: "Amendment", label: "Amendment (change in duties or worksite)" },
    { key: "Status maintenance", label: "Status and Travel Questions" },
  ],
  "L-1": [
    { key: "Petition filing", label: "New L-1 Petition" },
    { key: "Extension/transfer", label: "Extension" },
    { key: "Blanket L", label: "Blanket L Petition" },
  ],
  "O-1": [
    { key: "Petition filing", label: "New O-1 Petition" },
    { key: "Extension/transfer", label: "Extension" },
  ],
  "TN": [
    { key: "Petition filing", label: "New TN Application" },
    { key: "Extension/transfer", label: "Extension or Renewal" },
  ],
  "E-2": [
    { key: "Petition filing", label: "New E-2 Petition" },
    { key: "Extension/transfer", label: "Extension" },
  ],
  "Green Card": [
    { key: "Naturalization", label: "Naturalization (Become a U.S. Citizen)", description: "Apply for citizenship via N-400" },
    { key: "Card renewal", label: "Green Card Renewal or Replacement", description: "I-90 filing" },
    { key: "Remove conditions", label: "Remove Conditions on Residence", description: "I-751 for conditional permanent residents" },
    { key: "Travel document", label: "Travel Document / Reentry Permit" },
    { key: "Records request", label: "Records Request (FOIA)" },
  ],
  "U.S. Citizen": [
    { key: "Records request", label: "Records Request (FOIA / Naturalization Certificate)" },
    { key: "Sponsor family member", label: "Sponsor a Family Member (I-130)" },
    { key: "Replace documents", label: "Replace Citizenship Documents (N-565)" },
  ],
  "Other visa": [
    { key: "Status maintenance", label: "Status Maintenance" },
    { key: "Change of status", label: "Change of Status" },
    { key: "Extension/transfer", label: "Extension" },
  ],
};

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
  visaCategory: string;
}

export default function ImmSubdomainStep({ value, onChange, visaCategory }: Props) {
  const options = SUBDOMAIN_OPTIONS[visaCategory] || SUBDOMAIN_OPTIONS["Other visa"];

  const toggle = (key: string) => {
    onChange(value.includes(key) ? value.filter((v) => v !== key) : [...value, key]);
  };

  const title = visaCategory === "Green Card"
    ? "What do you need help with as a permanent resident?"
    : visaCategory === "U.S. Citizen"
    ? "What immigration-related service do you need?"
    : "What specifically do you need help with?";

  return (
    <WizardStep title={title} subtitle="Select all that apply.">
      <div className="space-y-2">
        {options.map((opt) => (
          <label key={opt.key} className="flex items-center gap-3 rounded-lg border border-stone-200 p-3 cursor-pointer hover:bg-stone-50">
            <input
              type="checkbox"
              checked={value.includes(opt.key)}
              onChange={() => toggle(opt.key)}
              className="h-4 w-4 rounded border-stone-300"
            />
            <div>
              <span className="text-sm">{opt.label}</span>
              {opt.description && <p className="text-xs text-stone-400 mt-0.5">{opt.description}</p>}
            </div>
          </label>
        ))}
      </div>
    </WizardStep>
  );
}
