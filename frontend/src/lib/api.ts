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

// --- Professional Search (lawyer / CPA / banker discovery) ---

export interface ProfessionalSearch {
  id: string;
  status: "queued" | "running" | "complete" | "failed";
  purpose: string;
  vertical: string;
  case_brief: string;
  uploaded_notes: string | null;
  persona_status: Record<
    string,
    {
      status?: "complete" | "failed";
      output_path?: string;
      firm_count?: number;
      error?: string;
      started_at?: string;
      finished_at?: string;
      input_tokens?: number;
      output_tokens?: number;
      cache_read_tokens?: number;
      cache_write_tokens?: number;
    }
  >;
  tier_report: Array<{
    firm: string;
    purpose: string;
    status: string;
    score: number | null;
    priority: string | null;
    next_action: string | null;
    next_action_date: string | null;
    last_contact_date: string | null;
    lowest_quote: number | null;
    highest_quote: number | null;
    open_risks: number;
  }> | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
  paid_at: string | null;
  is_paid: boolean;
  is_claimed: boolean;
  stripe_customer_email: string | null;
}

export async function startProfessionalSearch(params: {
  case_brief: string;
  purpose: string;
  vertical?: string;
  case_id?: string | null;
  files?: File[];
}): Promise<ProfessionalSearch> {
  const fd = new FormData();
  fd.append("case_brief", params.case_brief);
  fd.append("purpose", params.purpose);
  if (params.vertical) fd.append("vertical", params.vertical);
  if (params.case_id) fd.append("case_id", params.case_id);
  for (const f of params.files ?? []) fd.append("files", f);
  const res = await fetch(`${API_BASE}/professional-search`, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const getProfessionalSearch = (id: string) =>
  request<ProfessionalSearch>(`/professional-search/${id}`);

export interface MarketplaceMatch {
  sku: string;
  name: string;
  public_name: string | null;
  description: string;
  public_description: string | null;
  price_cents: number;
  headline: string | null;
  public_headline: string | null;
  cta_label: string | null;
  public_cta_label: string | null;
  path: string | null;
  match_score: number;
  match_reason: string;
}

export const getMarketplaceMatch = (searchId: string) =>
  request<MarketplaceMatch[]>(`/professional-search/${searchId}/marketplace-match`);

export const downloadProfessionalSearchUrl = (id: string) =>
  `${API_BASE}/professional-search/${id}/download`;

export async function startCheckout(searchId: string): Promise<{ url: string }> {
  const res = await fetch(`${API_BASE}/professional-search/${searchId}/checkout`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function claimSearch(searchId: string): Promise<ProfessionalSearch> {
  const token = typeof window !== "undefined" ? localStorage.getItem("guardian_token") : null;
  const res = await fetch(`${API_BASE}/professional-search/${searchId}/claim`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// --- Case ↔ professional-search integration ---

export interface ProfessionalSearchSummary {
  id: string;
  status: "queued" | "running" | "complete" | "failed";
  purpose: string;
  vertical: string;
  created_at: string;
  completed_at: string | null;
  paid_at: string | null;
  firm_count: number;
  top_firms: Array<{ name: string; confidence: number | null }>;
}

export const listCaseSearches = (caseId: string) =>
  request<ProfessionalSearchSummary[]>(`/cases/${caseId}/professional-searches`);

export interface DraftBrief {
  brief: string;
  suggested_vertical: string;
  suggested_purpose: string;
}

export const getCaseDraftBrief = (caseId: string) =>
  request<DraftBrief>(`/cases/${caseId}/draft-brief`);

// --- Lawyer engagements (CRM) ---

export type EngagementStatus =
  | "not_contacted"
  | "outreach_sent"
  | "in_discussion"
  | "engaged"
  | "declined";

export const ENGAGEMENT_STATUSES: EngagementStatus[] = [
  "not_contacted",
  "outreach_sent",
  "in_discussion",
  "engaged",
  "declined",
];

export interface Engagement {
  id: string;
  case_id: string;
  search_id: string | null;
  firm_name: string;
  firm_emails: string[];
  firm_phone: string | null;
  firm_website: string | null;
  firm_lead_attorney: string | null;
  status: EngagementStatus;
  notes: string | null;
  created_at: string;
  last_activity_at: string;
}

export const listCaseEngagements = (caseId: string) =>
  request<Engagement[]>(`/cases/${caseId}/engagements`);

export const createEngagement = (
  caseId: string,
  body: {
    firm_name: string;
    firm_emails?: string[];
    firm_phone?: string | null;
    firm_website?: string | null;
    firm_lead_attorney?: string | null;
    search_id?: string | null;
    notes?: string | null;
    status?: EngagementStatus;
  },
) =>
  request<Engagement>(`/cases/${caseId}/engagements`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const updateEngagement = (
  caseId: string,
  engagementId: string,
  body: { status?: EngagementStatus; notes?: string | null },
) =>
  request<Engagement>(`/cases/${caseId}/engagements/${engagementId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deleteEngagement = (caseId: string, engagementId: string) =>
  request<{ ok: boolean }>(`/cases/${caseId}/engagements/${engagementId}`, {
    method: "DELETE",
  });

export async function listMySearches(): Promise<ProfessionalSearch[]> {
  const token = typeof window !== "undefined" ? localStorage.getItem("guardian_token") : null;
  const res = await fetch(`${API_BASE}/professional-search/mine/list`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}
