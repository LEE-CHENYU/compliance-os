import CardSelect from "@/components/ui/CardSelect";
import WizardStep from "../WizardStep";

const STAGE_OPTIONS: Record<string, { value: string; label: string }[]> = {
  Immigration: [
    { value: "new_application", label: "New application" },
    { value: "pending_case", label: "Pending case" },
    { value: "renewal", label: "Renewal" },
    { value: "status_change", label: "Status change" },
    { value: "review_prior", label: "Review prior filing" },
  ],
  "Tax Filing": [
    { value: "preparing", label: "Preparing to file" },
    { value: "review_filed", label: "Already filed, want review" },
    { value: "irs_notice", label: "Received IRS notice" },
    { value: "amending", label: "Amending prior year" },
  ],
  "Corporate Compliance": [
    { value: "new_entity", label: "New entity" },
    { value: "annual_compliance", label: "Annual compliance" },
    { value: "dissolution", label: "Dissolution" },
  ],
  Other: [
    { value: "general_review", label: "General review" },
  ],
};

interface Props {
  value: string[];
  onChange: (v: string[]) => void;
  concerns: string[];
}

export default function CurrentStageStep({ value, onChange, concerns }: Props) {
  const options = concerns.flatMap((c) => STAGE_OPTIONS[c] || []);
  const unique = options.filter((o, i, arr) => arr.findIndex((x) => x.value === o.value) === i);

  return (
    <WizardStep title="Where are you in the process?" subtitle="Select the stage that best describes your situation.">
      <CardSelect options={unique} selected={value} onChange={onChange} />
    </WizardStep>
  );
}
