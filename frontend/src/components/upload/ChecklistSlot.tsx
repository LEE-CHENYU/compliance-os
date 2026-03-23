import Badge from "@/components/ui/Badge";
import FileDropZone from "@/components/ui/FileDropZone";
import type { Document, DocumentSlot } from "@/lib/api";

interface Props {
  slot: DocumentSlot;
  document: Document | null;
  uploading: boolean;
  onDrop: (file: File) => void;
  onRemove: () => void;
}

export default function ChecklistSlot({ slot, document: doc, uploading, onDrop, onRemove }: Props) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">{slot.label}</span>
        <Badge variant={doc ? "uploaded" : slot.required ? "required" : "optional"}>
          {doc ? "Uploaded" : slot.required ? "Required" : "Optional"}
        </Badge>
      </div>
      {doc ? (
        <div className="flex items-center justify-between text-sm text-stone-500">
          <span>{doc.filename} ({(doc.file_size / 1024).toFixed(0)} KB)</span>
          <button onClick={onRemove} className="text-xs text-red-500 hover:text-red-700">Remove</button>
        </div>
      ) : (
        <FileDropZone onDrop={onDrop} disabled={uploading} className="p-4">
          <p className="text-sm text-stone-400 text-center">
            {uploading ? "Uploading..." : "Drop file here or click to upload"}
          </p>
        </FileDropZone>
      )}
    </div>
  );
}
