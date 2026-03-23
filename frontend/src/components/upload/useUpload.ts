"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Document,
  DocumentSlot,
  deleteDocument,
  getChecklist,
  listDocuments,
  updateDocument,
  uploadDocument,
} from "@/lib/api";

export function useUpload(caseId: string) {
  const [slots, setSlots] = useState<DocumentSlot[]>([]);
  const [filled, setFilled] = useState<Record<string, string>>({});
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState<string | null>(null); // slot key or "general"

  const refresh = useCallback(async () => {
    const [checklistData, docsData] = await Promise.all([
      getChecklist(caseId),
      listDocuments(caseId),
    ]);
    setSlots(checklistData.slots);
    setFilled(checklistData.filled);
    setDocuments(docsData.documents);
  }, [caseId]);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const upload = useCallback(
    async (file: File, slotKey?: string) => {
      setUploading(slotKey || "general");
      try {
        await uploadDocument(caseId, file, slotKey);
        await refresh();
      } finally {
        setUploading(null);
      }
    },
    [caseId, refresh]
  );

  const remove = useCallback(
    async (docId: string) => {
      await deleteDocument(caseId, docId);
      await refresh();
    },
    [caseId, refresh]
  );

  const assignSlot = useCallback(
    async (docId: string, slotKey: string) => {
      await updateDocument(caseId, docId, { slot_key: slotKey });
      await refresh();
    },
    [caseId, refresh]
  );

  const requiredSlots = slots.filter((s) => s.required);
  const filledRequired = requiredSlots.filter((s) => filled[s.key]);
  const completionCount = filledRequired.length;
  const totalRequired = requiredSlots.length;
  const isComplete = totalRequired > 0 && completionCount === totalRequired;

  return {
    slots,
    filled,
    documents,
    loading,
    uploading,
    upload,
    remove,
    assignSlot,
    completionCount,
    totalRequired,
    isComplete,
  };
}
