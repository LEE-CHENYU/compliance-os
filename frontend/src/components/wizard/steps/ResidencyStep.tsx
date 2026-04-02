import CardSelect from "@/components/ui/CardSelect";
import WizardStep from "../WizardStep";

const OPTIONS = [
  { value: "F-1", label: "F-1 Student" },
  { value: "H-1B", label: "H-1B Worker" },
  { value: "L-1", label: "L-1 Intracompany" },
  { value: "O-1", label: "O-1 Extraordinary Ability" },
  { value: "Green Card", label: "Green Card Holder" },
  { value: "Citizen", label: "U.S. Citizen" },
  { value: "Other", label: "Other" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function ResidencyStep({ value, onChange }: Props) {
  return (
    <WizardStep title="What is your current immigration/residency status?">
      <CardSelect options={OPTIONS} selected={value} onChange={onChange} />
    </WizardStep>
  );
}
