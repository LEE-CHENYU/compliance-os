import CardSelect from "@/components/ui/CardSelect";
import WizardStep from "../WizardStep";

const OPTIONS = [
  { value: "Preparing to file", label: "Preparing to File", description: "Haven't filed yet for this year" },
  { value: "Already filed, want review", label: "Already Filed, Want Review", description: "Filed but want to check correctness" },
  { value: "Amending prior year", label: "Amending Prior Year", description: "Need to correct a previously filed return" },
  { value: "Received IRS notice", label: "Received IRS Notice", description: "Got a letter from the IRS" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function TaxFilingStageStep({ value, onChange }: Props) {
  return (
    <WizardStep title="Where are you in the tax filing process?">
      <CardSelect options={OPTIONS} selected={value} onChange={onChange} />
    </WizardStep>
  );
}
