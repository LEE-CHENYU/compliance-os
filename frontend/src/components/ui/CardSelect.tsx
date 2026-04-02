interface Option {
  value: string;
  label: string;
  description?: string;
}

interface Props {
  options: Option[];
  selected: string[];
  onChange: (selected: string[]) => void;
  multi?: boolean;
}

export default function CardSelect({ options, selected, onChange, multi = false }: Props) {
  const toggle = (value: string) => {
    if (multi) {
      onChange(
        selected.includes(value)
          ? selected.filter((v) => v !== value)
          : [...selected, value]
      );
    } else {
      onChange([value]);
    }
  };

  return (
    <div className="grid gap-3">
      {options.map((opt) => {
        const isSelected = selected.includes(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => toggle(opt.value)}
            className={`text-left rounded-lg border-2 p-4 transition-all ${
              isSelected
                ? "border-stone-800 bg-stone-50"
                : "border-stone-200 hover:border-stone-300"
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`h-5 w-5 rounded-full border-2 flex items-center justify-center ${
                  isSelected ? "border-stone-800" : "border-stone-300"
                }`}
              >
                {isSelected && <div className="h-2.5 w-2.5 rounded-full bg-stone-800" />}
              </div>
              <div>
                <div className="font-medium">{opt.label}</div>
                {opt.description && (
                  <div className="text-sm text-stone-500 mt-0.5">{opt.description}</div>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
