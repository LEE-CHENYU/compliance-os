import CardSelect from "@/components/ui/CardSelect";
import WizardStep from "../WizardStep";

const OPTIONS = [
  { value: "Lawyer", label: "Lawyer" },
  { value: "CPA/Accountant", label: "CPA / Accountant" },
  { value: "Filing software", label: "Filing software (TurboTax, etc.)" },
  { value: "None", label: "None" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function ExistingHelpStep({ value, onChange }: Props) {
  return (
    <WizardStep title="Are you working with any professionals?" subtitle="Select all that apply.">
      <CardSelect options={OPTIONS} selected={value} onChange={onChange} multi />
    </WizardStep>
  );
}
