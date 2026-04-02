import CardSelect from "@/components/ui/CardSelect";
import WizardStep from "../WizardStep";

const OPTIONS = [
  { value: "Immigration", label: "Immigration", description: "Visa status, work authorization, applications" },
  { value: "Tax Filing", label: "Tax Filing", description: "Tax returns, amendments, compliance forms" },
  { value: "Corporate Compliance", label: "Corporate Compliance", description: "Business entity filings, annual reports" },
  { value: "Other", label: "Other", description: "Something else" },
];

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
}

export default function ConcernAreaStep({ value, onChange }: Props) {
  return (
    <WizardStep title="What brings you here today?" subtitle="Select all that apply.">
      <CardSelect options={OPTIONS} selected={value} onChange={onChange} multi />
    </WizardStep>
  );
}
