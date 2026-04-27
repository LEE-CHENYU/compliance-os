const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // Forward the bearer token whenever it's available — case endpoints
  // are now soft-authed (anonymous still works, authenticated gets
  // ownership), so this is harmless when the user isn't signed in but
  // is required for cases scoped to their account.
  const token =
    typeof window !== "undefined" ? localStorage.getItem("guardian_token") : null;
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeader,
      ...options?.headers,
    },
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
  // firms_data carries the per-firm Stage 1 + Stage 2 details. Stage 1
  // populates `name`, `lead_attorney`, `_credentials`, etc. Stage 2 adds
  // underscore-prefixed enrichment keys: `_lead_attorney_band`,
  // `_lead_attorney_credentials`, `_alternate_attorneys`, `_verified_sources`,
  // `_individual_band_gap`, `_individual_vs_firm_band_gap_warning`,
  // `_enriched_at`. The shape is loose because persona YAML schemas vary
  // — keep it as a Record and narrow at access sites.
  firms_data: Array<Record<string, unknown>> | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
  paid_at: string | null;
  is_paid: boolean;
  is_claimed: boolean;
  stripe_customer_email: string | null;
  case_id: string | null;
  // Stage 2 enrichment lifecycle (per-firm individual-attorney verification).
  enrichment_status: "idle" | "enriching" | "complete" | "failed";
  enrichment_started_at: string | null;
  enrichment_completed_at: string | null;
  enrichment_error: string | null;
}

export interface EnrichmentStatus {
  status: "idle" | "enriching" | "complete" | "failed";
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  firms_enriched: number;
  firms_total: number;
}

export const getEnrichmentStatus = (id: string) =>
  request<EnrichmentStatus>(`/professional-search/${id}/enrichment-status`);

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

// Opt-in 30-day Pro trial post-search-payment. Uses the card the user
// saved during the $15 checkout to set up auto-renewal at $20/mo after
// the trial ends. Returns { ok: true, already_active?, trial_days? }.
export async function startProTrialFromSearch(
  searchId: string,
): Promise<{ ok: boolean; already_active?: boolean; trial_days?: number }> {
  const headers = _authHeaders();
  if (!headers.Authorization) throw new Error("Sign in first");
  const res = await fetch(
    `${API_BASE}/professional-search/${searchId}/start-pro-trial`,
    { method: "POST", headers },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const downloadProfessionalSearchUrl = (id: string) =>
  `${API_BASE}/professional-search/${id}/download`;

export async function startCheckout(
  searchId: string,
): Promise<{ url: string; pro_free_grant?: boolean }> {
  // Send the auth token if present so the backend can short-circuit to
  // the Pro free-search grant path (skips Stripe entirely for Pro users
  // who haven't consumed their 1-per-period free search).
  const token = typeof window !== "undefined" ? localStorage.getItem("guardian_token") : null;
  const res = await fetch(`${API_BASE}/professional-search/${searchId}/checkout`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
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
  body: { status?: EngagementStatus; notes?: string | null; firm_emails?: string[] },
) =>
  request<Engagement>(`/cases/${caseId}/engagements/${engagementId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deleteEngagement = (caseId: string, engagementId: string) =>
  request<{ ok: boolean }>(`/cases/${caseId}/engagements/${engagementId}`, {
    method: "DELETE",
  });

export interface DraftEmail {
  to: string[];
  subject: string;
  body: string;
}

export const getEngagementDraftEmail = (caseId: string, engagementId: string) =>
  request<DraftEmail>(`/cases/${caseId}/engagements/${engagementId}/draft-email`);

// --- Gmail integration (OAuth) ---

export interface GmailStatus {
  connected: boolean;
  scope?: string;
  granted_at?: string | null;
  expires_at?: string | null;
}

function _authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("guardian_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getGmailStatus(): Promise<GmailStatus> {
  const headers = _authHeaders();
  if (!headers.Authorization) return { connected: false };
  const res = await fetch(`${API_BASE}/auth/me/gmail/status`, { headers });
  if (!res.ok) return { connected: false };
  return res.json();
}

export async function getGmailConnectUrl(nextPath?: string): Promise<{ url: string }> {
  const headers = _authHeaders();
  if (!headers.Authorization) throw new Error("Sign in first to connect Gmail");
  const params = new URLSearchParams();
  if (nextPath) params.set("next", nextPath);
  const res = await fetch(
    `${API_BASE}/auth/google/connect-gmail/url${params.toString() ? `?${params}` : ""}`,
    { headers },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export interface EmailThread {
  id: string;
  gmail_thread_id: string;
  subject: string;
  last_message_at: string;
  last_message_snippet: string;
  last_message_from: string;
  last_message_direction: "inbound" | "outbound";
  message_count: number;
}

export const listEngagementThreads = (caseId: string, engagementId: string) =>
  request<EmailThread[]>(`/cases/${caseId}/engagements/${engagementId}/threads`);

export interface GmailSyncResult {
  skipped?: boolean;
  reason?: string;
  messages_scanned?: number;
  threads_matched?: number;
  threads_new?: number;
  last_synced_at: string;
  /** LLM-generated 1-2 sentence summary of what was synced.
   *  Null when no threads were touched, no Anthropic key set, or the
   *  summary call failed (sync result is the source of truth either way). */
  summary?: string | null;
}

export async function syncGmail(force = false): Promise<GmailSyncResult> {
  const headers = _authHeaders();
  if (!headers.Authorization) throw new Error("Sign in first to sync Gmail");
  const params = force ? "?force=true" : "";
  const res = await fetch(`${API_BASE}/auth/me/gmail/sync${params}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function disconnectGmail(): Promise<{ ok: boolean }> {
  const headers = _authHeaders();
  if (!headers.Authorization) throw new Error("Not signed in");
  const res = await fetch(`${API_BASE}/auth/me/gmail/disconnect`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// --- Cross-case engagement view (dashboard) ---

export type AttentionLabel =
  | "new_reply"
  | "needs_followup"
  | "awaiting_response";

export interface MyEngagement {
  id: string;
  case_id: string;
  case_workflow_type: string;
  case_status: string;
  firm_name: string;
  firm_lead_attorney: string | null;
  status: EngagementStatus;
  notes: string | null;
  last_activity_at: string;
  thread_count: number;
  last_thread_at: string | null;
  last_thread_direction: "inbound" | "outbound" | null;
  last_thread_subject: string | null;
  attention_label: AttentionLabel | null;
}

export async function listMyEngagements(): Promise<MyEngagement[]> {
  const headers = _authHeaders();
  if (!headers.Authorization) return [];
  const res = await fetch(`${API_BASE}/me/engagements`, { headers });
  if (!res.ok) return [];
  return res.json();
}

/** Pull the activity-context blob (lawyer searches + engagements + recent
 *  email threads) for the voice agent's call-start system message. The
 *  chat assistant gets the same data server-side via /api/chat. Returns
 *  empty string for signed-out users — caller can concat unconditionally. */
export async function getActivityContext(): Promise<string> {
  const headers = _authHeaders();
  if (!headers.Authorization) return "";
  const res = await fetch(`${API_BASE}/me/activity-context`, { headers });
  if (!res.ok) return "";
  const body = (await res.json().catch(() => ({ text: "" }))) as { text?: string };
  return body.text ?? "";
}

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

// ----------------------------------------------------------------------------
// Subscription (Guardian Pro $20/mo)
// ----------------------------------------------------------------------------

export type Tier = "free" | "pro_trial" | "pro";

export interface SubscriptionState {
  tier: Tier;
  is_pro: boolean;          // Pro OR Pro Trial — unlimited extractions
  is_paying_pro: boolean;   // paid Pro only — eligible for free lawyer search
  subscription: {
    status: string;
    trial_end: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
    has_billing_portal: boolean;
  } | null;
  extraction_quota: {
    used: number;
    limit: number | null;     // null means unlimited
    remaining: number | null;
    at_limit: boolean;
    reset_at: string | null;  // ISO timestamp; only set for Free tier
  };
  pro_search_quota: {
    used: number;
    limit: number | null;     // null means not eligible (Free / Trial)
    has_free_search: boolean;
    period_end: string | null;
  };
  limits: {
    free_extractions_per_month: number;
    pro_free_searches_per_period: number;
  };
}

/** Read-only entitlement snapshot. Cheap — call from the dashboard mount
 *  + any component that needs to render quota. Returns null if the user
 *  isn't authenticated (no token in localStorage). */
export async function getSubscriptionState(): Promise<SubscriptionState | null> {
  const token = typeof window !== "undefined" ? localStorage.getItem("guardian_token") : null;
  if (!token) return null;
  const res = await fetch(`${API_BASE}/subscription/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function startProSubscriptionCheckout(opts?: {
  successPath?: string;
  cancelPath?: string;
  trialPeriodDays?: number;
}): Promise<{ url: string; session_id: string }> {
  const token = typeof window !== "undefined" ? localStorage.getItem("guardian_token") : null;
  if (!token) throw new Error("Sign in first to subscribe.");
  const res = await fetch(`${API_BASE}/subscription/checkout`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      success_path: opts?.successPath,
      cancel_path: opts?.cancelPath,
      trial_period_days: opts?.trialPeriodDays,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : (err.detail?.message ?? res.statusText));
  }
  return res.json();
}

export async function openBillingPortal(returnPath?: string): Promise<{ url: string }> {
  const token = typeof window !== "undefined" ? localStorage.getItem("guardian_token") : null;
  if (!token) throw new Error("Sign in first.");
  const res = await fetch(`${API_BASE}/subscription/portal`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ return_path: returnPath }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : (err.detail?.message ?? res.statusText));
  }
  return res.json();
}

/** Detail shape of a 402 response from the upload route when the user
 *  has hit the Free-tier extraction cap. The dashboard upload paywall
 *  modal keys on `code === "extraction_quota_exceeded"`. */
export interface ExtractionQuotaExceededDetail {
  code: "extraction_quota_exceeded";
  tier: Tier;
  used: number;
  limit: number;
  reset_at: string | null;
  upgrade_url: string;
  message: string;
}
