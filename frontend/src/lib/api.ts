const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// --- Cases ---

export interface Case {
  id: string;
  workflow_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  answer_count: number;
}

export const createCase = (workflow_type: string) =>
  request<Case>("/cases", {
    method: "POST",
    body: JSON.stringify({ workflow_type }),
  });

export const listCases = () =>
  request<{ cases: Case[] }>("/cases");

export const getCase = (id: string) =>
  request<Case>(`/cases/${id}`);

// --- Discovery ---

export interface DiscoveryAnswer {
  id: string;
  step: string;
  question_key: string;
  answer: unknown;
  answered_at: string;
}

export const saveAnswer = (caseId: string, step: string, question_key: string, answer: unknown) =>
  request<DiscoveryAnswer>(`/cases/${caseId}/discovery`, {
    method: "POST",
    body: JSON.stringify({ step, question_key, answer }),
  });

export const getAnswers = (caseId: string) =>
  request<{ answers: DiscoveryAnswer[] }>(`/cases/${caseId}/discovery`);

export const generateSummary = (caseId: string) =>
  request<{ summary: Record<string, unknown> }>(`/cases/${caseId}/discovery/summary`);

// --- Chat ---

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export const getChat = (caseId: string) =>
  request<{ messages: ChatMessage[] }>(`/cases/${caseId}/chat`);

export const sendChat = (caseId: string, content: string) =>
  request<{ messages: ChatMessage[] }>(`/cases/${caseId}/chat`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });

// --- Documents ---

export interface DocumentSlot {
  key: string;
  label: string;
  required: boolean;
  group: string;
  repeatable: boolean;
}

export interface Document {
  id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  slot_key: string | null;
  classification: string | null;
  status: string;
  uploaded_at: string;
}

export const getChecklist = (caseId: string) =>
  request<{ slots: DocumentSlot[]; filled: Record<string, string> }>(`/cases/${caseId}/documents/checklist`);

export const listDocuments = (caseId: string) =>
  request<{ documents: Document[] }>(`/cases/${caseId}/documents`);

export async function uploadDocument(caseId: string, file: File, slotKey?: string): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  if (slotKey) formData.append("slot_key", slotKey);
  const res = await fetch(`${API_BASE}/cases/${caseId}/documents`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const updateDocument = (caseId: string, docId: string, update: { slot_key?: string; classification?: string }) =>
  request<Document>(`/cases/${caseId}/documents/${docId}`, {
    method: "PATCH",
    body: JSON.stringify(update),
  });

export const deleteDocument = (caseId: string, docId: string) =>
  request<{ ok: boolean }>(`/cases/${caseId}/documents/${docId}`, { method: "DELETE" });
