/**
 * Guardian check flow API client.
 */

const API = typeof window !== "undefined" && window.location.hostname === "localhost"
  ? "http://localhost:8000/api"
  : "/api";

// --- Types ---

export interface Check {
  id: string;
  track: string;
  stage: string | null;
  status: string;
  answers: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentOut {
  id: string;
  check_id: string;
  doc_type: string;
  filename: string;
  file_size: number;
  mime_type: string;
  uploaded_at: string;
}

export interface ExtractedField {
  id: string;
  document_id: string;
  field_name: string;
  field_value: string | null;
  confidence: number | null;
}

export interface Comparison {
  id: string;
  check_id: string;
  field_name: string;
  value_a: string | null;
  value_b: string | null;
  match_type: string;
  status: string; // match | mismatch | needs_review
  confidence: number | null;
  detail: string | null;
}

export interface Followup {
  id: string;
  check_id: string;
  question_key: string;
  question_text: string | null;
  chips: string[] | null;
  answer: string | null;
  answered_at: string | null;
}

export interface Finding {
  id: string;
  check_id: string;
  rule_id: string;
  severity: string; // critical | warning | info
  category: string; // comparison | logic | advisory
  title: string;
  action: string;
  consequence: string;
  immigration_impact: boolean;
}

export interface Snapshot {
  check: Check;
  extractions: Record<string, ExtractedField[]>;
  comparisons: Comparison[];
  findings: Finding[];
  followups: Followup[];
  advisories: Finding[];
}

// --- API calls ---

export async function createCheck(
  track: string,
  answers: Record<string, unknown>
): Promise<Check> {
  const resp = await fetch(`${API}/checks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ track, answers }),
  });
  return resp.json();
}

export async function getCheck(id: string): Promise<Check> {
  const resp = await fetch(`${API}/checks/${id}`);
  return resp.json();
}

export async function updateCheck(
  id: string,
  data: { answers?: Record<string, unknown>; status?: string }
): Promise<Check> {
  const resp = await fetch(`${API}/checks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return resp.json();
}

export async function uploadDocument(
  checkId: string,
  file: File,
  docType: string
): Promise<DocumentOut> {
  const form = new FormData();
  form.append("file", file);
  form.append("doc_type", docType);
  const resp = await fetch(`${API}/checks/${checkId}/documents`, {
    method: "POST",
    body: form,
  });
  return resp.json();
}

export async function getDocuments(checkId: string): Promise<DocumentOut[]> {
  const resp = await fetch(`${API}/checks/${checkId}/documents`);
  return resp.json();
}

export async function triggerExtraction(
  checkId: string
): Promise<{ status: string; results: Record<string, Record<string, unknown>> }> {
  const resp = await fetch(`${API}/checks/${checkId}/extract`, { method: "POST" });
  return resp.json();
}

export async function getExtractions(
  checkId: string
): Promise<Record<string, ExtractedField[]>> {
  const resp = await fetch(`${API}/checks/${checkId}/extractions`);
  return resp.json();
}

export async function triggerCompare(checkId: string): Promise<Comparison[]> {
  const resp = await fetch(`${API}/checks/${checkId}/compare`, { method: "POST" });
  return resp.json();
}

export async function getComparisons(checkId: string): Promise<Comparison[]> {
  const resp = await fetch(`${API}/checks/${checkId}/comparisons`);
  return resp.json();
}

export async function triggerEvaluate(checkId: string): Promise<Finding[]> {
  const resp = await fetch(`${API}/checks/${checkId}/evaluate`, { method: "POST" });
  return resp.json();
}

export async function getFindings(checkId: string): Promise<Finding[]> {
  const resp = await fetch(`${API}/checks/${checkId}/findings`);
  return resp.json();
}

export async function generateFollowups(checkId: string): Promise<Followup[]> {
  const resp = await fetch(`${API}/checks/${checkId}/followups`, { method: "POST" });
  return resp.json();
}

export async function getFollowups(checkId: string): Promise<Followup[]> {
  const resp = await fetch(`${API}/checks/${checkId}/followups`);
  return resp.json();
}

export async function answerFollowup(
  checkId: string,
  followupId: string,
  answer: string
): Promise<Followup> {
  const resp = await fetch(`${API}/checks/${checkId}/followups/${followupId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
  return resp.json();
}

export async function getSnapshot(checkId: string): Promise<Snapshot> {
  const resp = await fetch(`${API}/checks/${checkId}/snapshot`);
  return resp.json();
}
