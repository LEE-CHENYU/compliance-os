import type { Document, DocumentSlot } from "@/lib/api";
import ChecklistSlot from "./ChecklistSlot";

interface Props {
  slots: DocumentSlot[];
  filled: Record<string, string>;
  documents: Document[];
  uploading: string | null;
  onUpload: (file: File, slotKey: string) => void;
  onRemove: (docId: string) => void;
}

export default function DocumentChecklist({ slots, filled, documents, uploading, onUpload, onRemove }: Props) {
  const groups = slots.reduce<Record<string, DocumentSlot[]>>((acc, slot) => {
    (acc[slot.group] = acc[slot.group] || []).push(slot);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {Object.entries(groups).map(([group, groupSlots]) => (
        <div key={group} className="space-y-3">
          <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide">{group}</h3>
          <div className="space-y-2">
            {groupSlots.map((slot) => {
              const docId = filled[slot.key];
              const doc = docId ? documents.find((d) => d.id === docId) || null : null;
              return (
                <ChecklistSlot
                  key={slot.key}
                  slot={slot}
                  document={doc}
                  uploading={uploading === slot.key}
                  onDrop={(file) => onUpload(file, slot.key)}
                  onRemove={() => docId && onRemove(docId)}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
