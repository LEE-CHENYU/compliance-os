import CardSelect from "@/components/ui/CardSelect";
import WizardStep from "../WizardStep";

const OPTIONS = [
  { value: "Nonresident alien", label: "Nonresident Alien", description: "F-1/J-1 in first 5 years, or failed Substantial Presence Test" },
  { value: "U.S. resident", label: "U.S. Resident for Tax Purposes", description: "Passed SPT, Green Card holder, or elected resident status" },
  { value: "Dual-status", label: "Dual-Status", description: "Changed status during the tax year (part NR, part resident)" },
  { value: "Not sure", label: "Not Sure", description: "We can help determine this" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function TaxResidencyStep({ value, onChange }: Props) {
  return (
    <WizardStep
      title="What is your tax residency status?"
      subtitle="This determines which tax return you file (1040 vs 1040-NR) and which reporting requirements apply."
    >
      <CardSelect options={OPTIONS} selected={value} onChange={onChange} />
    </WizardStep>
  );
}
