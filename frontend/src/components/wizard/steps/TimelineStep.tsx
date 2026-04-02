import WizardStep from "../WizardStep";

interface TimelineValue {
  date: string;
  description: string;
}

interface Props {
  value: TimelineValue;
  onChange: (v: TimelineValue) => void;
}

export default function TimelineStep({ value, onChange }: Props) {
  return (
    <WizardStep title="Are there any upcoming deadlines you're aware of?" subtitle="If you're not sure, you can skip this.">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Date</label>
          <input
            type="date"
            value={value.date}
            onChange={(e) => onChange({ ...value, date: e.target.value })}
            className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-stone-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Description</label>
          <textarea
            value={value.description}
            onChange={(e) => onChange({ ...value, description: e.target.value })}
            placeholder="What is this deadline for?"
            rows={3}
            className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-stone-500 focus:outline-none resize-none"
          />
        </div>
      </div>
    </WizardStep>
  );
}
