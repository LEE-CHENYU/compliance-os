"use client";

type ChecklistItem = {
  id: string;
  label: string;
};

export default function SignOffChecklist({
  items,
  responses,
  onChange,
}: {
  items: ChecklistItem[];
  responses: Record<string, boolean>;
  onChange: (itemId: string, checked: boolean) => void;
}) {
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <label
          key={item.id}
          className="flex items-start gap-4 rounded-[22px] border border-[#dbe5f2] bg-white px-4 py-4 text-[15px] leading-6 text-[#435774]"
        >
          <input
            type="checkbox"
            checked={Boolean(responses[item.id])}
            onChange={(event) => onChange(item.id, event.target.checked)}
            className="mt-1 h-5 w-5 rounded border-[#b8c8df] text-[#5b8dee] focus:ring-[#5b8dee]"
          />
          <span>{item.label}</span>
        </label>
      ))}
    </div>
  );
}
