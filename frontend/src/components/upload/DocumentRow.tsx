import Badge from "@/components/ui/Badge";
import type { Document, DocumentSlot } from "@/lib/api";

interface Props {
  doc: Document;
  slots: DocumentSlot[];
  onAssignSlot: (slotKey: string) => void;
  onRemove: () => void;
}

export default function DocumentRow({ doc, slots, onAssignSlot, onRemove }: Props) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-stone-200 bg-white p-3">
      <div className="flex items-center gap-3 min-w-0">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{doc.filename}</p>
          <p className="text-xs text-stone-400">{(doc.file_size / 1024).toFixed(0)} KB</p>
        </div>
        {doc.classification && (
          <Badge variant="classified">{doc.classification}</Badge>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <select
          value={doc.slot_key || ""}
          onChange={(e) => e.target.value && onAssignSlot(e.target.value)}
          className="text-xs border border-stone-200 rounded px-2 py-1"
        >
          <option value="">Assign to slot...</option>
          {slots.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
        <button onClick={onRemove} className="text-xs text-red-500 hover:text-red-700">Remove</button>
      </div>
    </div>
  );
}
