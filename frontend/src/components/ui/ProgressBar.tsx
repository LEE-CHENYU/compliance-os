interface Props {
  currentStep: number;
  totalSteps: number;
  labels?: string[];
}

export default function ProgressBar({ currentStep, totalSteps, labels }: Props) {
  return (
    <div className="flex items-center gap-1 w-full">
      {Array.from({ length: totalSteps }, (_, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div
            className={`h-1.5 w-full rounded-full transition-colors ${
              i < currentStep ? "bg-stone-800" : i === currentStep ? "bg-stone-500" : "bg-stone-200"
            }`}
          />
          {labels && labels[i] && (
            <span className={`text-[10px] ${i <= currentStep ? "text-stone-600" : "text-stone-300"}`}>
              {labels[i]}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
