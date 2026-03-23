interface Props {
  variant: "required" | "optional" | "uploaded" | "classified" | "empty";
  children: React.ReactNode;
}

const STYLES: Record<string, string> = {
  required: "bg-amber-50 text-amber-700 border-amber-200",
  optional: "bg-stone-50 text-stone-500 border-stone-200",
  uploaded: "bg-blue-50 text-blue-700 border-blue-200",
  classified: "bg-green-50 text-green-700 border-green-200",
  empty: "bg-stone-50 text-stone-400 border-stone-200",
};

export default function Badge({ variant, children }: Props) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${STYLES[variant]}`}>
      {children}
    </span>
  );
}
