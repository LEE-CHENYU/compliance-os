import CardSelect from "@/components/ui/CardSelect";
import WizardStep from "../WizardStep";

const OPTIONS = [
  { value: "Not started", label: "Not Started Yet", description: "Planning or researching" },
  { value: "Preparing application", label: "Preparing Application", description: "Gathering documents, working with attorney" },
  { value: "Pending case", label: "Case Filed / Pending", description: "Waiting for USCIS or consular decision" },
  { value: "Approved, next steps", label: "Approved, Need Next Steps", description: "Got approval, need to know what's next" },
  { value: "Review prior filing", label: "Review Prior Filing", description: "Want to check if a previous application was done correctly" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function ImmStageStep({ value, onChange }: Props) {
  return (
    <WizardStep title="Where are you in the immigration process?">
      <CardSelect options={OPTIONS} selected={value} onChange={onChange} />
    </WizardStep>
  );
}
