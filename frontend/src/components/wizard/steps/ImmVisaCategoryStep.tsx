import CardSelect from "@/components/ui/CardSelect";
import WizardStep from "../WizardStep";

const OPTIONS = [
  { value: "F-1", label: "F-1 Student" },
  { value: "J-1", label: "J-1 Exchange Visitor" },
  { value: "H-1B", label: "H-1B Worker" },
  { value: "L-1", label: "L-1 Intracompany Transferee" },
  { value: "O-1", label: "O-1 Extraordinary Ability" },
  { value: "TN", label: "TN (USMCA Professional)" },
  { value: "E-2", label: "E-2 Treaty Investor" },
  { value: "Green Card", label: "Green Card Holder (Permanent Resident)" },
  { value: "U.S. Citizen", label: "U.S. Citizen" },
  { value: "Other visa", label: "Other Visa Category" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function ImmVisaCategoryStep({ value, onChange }: Props) {
  return (
    <WizardStep
      title="What is your current immigration status?"
      subtitle="This determines which immigration forms and processes apply to you."
    >
      <CardSelect options={OPTIONS} selected={value} onChange={onChange} />
    </WizardStep>
  );
}
