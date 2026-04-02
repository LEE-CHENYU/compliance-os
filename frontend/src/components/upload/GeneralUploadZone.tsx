import FileDropZone from "@/components/ui/FileDropZone";

interface Props {
  uploading: boolean;
  onDrop: (file: File) => void;
}

export default function GeneralUploadZone({ uploading, onDrop }: Props) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide">Additional Documents</h3>
      <FileDropZone onDrop={onDrop} disabled={uploading} className="p-8">
        <div className="text-center">
          <p className="text-sm text-stone-500">{uploading ? "Uploading..." : "Drop files here or click to upload"}</p>
          <p className="text-xs text-stone-400 mt-1">PDF, PNG, JPG, CSV, or TXT (max 20MB)</p>
        </div>
      </FileDropZone>
    </div>
  );
}
