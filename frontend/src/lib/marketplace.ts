"use client";

import { authHeaders } from "@/lib/auth";

const API = typeof window !== "undefined" && window.location.hostname === "localhost"
  ? "http://localhost:8000/api"
  : "/api";

export interface Form8843Request {
  email: string;
  full_name: string;
  visa_type: string;
  school_name: string;
  country_citizenship: string;
  country_passport?: string;
  passport_number?: string;
  current_nonimmigrant_status?: string;
  arrival_date?: string;
  school_address?: string;
  school_contact?: string;
  program_director?: string;
  us_taxpayer_id?: string;
  address_country?: string;
  address_us?: string;
  days_present_current: number;
  days_present_year_1_ago: number;
  days_present_year_2_ago: number;
  days_excludable_current?: number;
  changed_status?: boolean;
  applied_for_residency?: boolean;
  filing_with_tax_return?: boolean;
}

export interface MarketplaceProduct {
  sku: string;
  name: string;
  description: string;
  price_cents: number;
  tier: string;
  requires_attorney: boolean;
  requires_questionnaire: boolean;
  active: boolean;
  category: string | null;
  filing_method: string | null;
  fulfillment_mode: string | null;
  headline: string | null;
  highlights: string[];
  cta_label: string | null;
  path: string | null;
}

export interface MarketplaceArtifact {
  label: string;
  filename: string;
  url: string;
}

export interface MarketplaceFinding {
  rule_id: string;
  severity: string;
  category: string;
  title: string;
  action: string;
  consequence: string;
  immigration_impact?: boolean;
}

export interface MarketplaceDocumentSummary {
  doc_type: string;
  filename: string;
  fields: Record<string, string>;
}

export interface MarketplaceComparison {
  field_name: string;
  value_a: string | null;
  value_b: string | null;
  match_type: string;
  status: string;
  confidence: number;
  detail?: string | null;
}

export interface MarketplaceMailingInstructions {
  headline: string;
  summary: string;
  steps: string[];
}

export interface MarketplaceAgreement {
  agreement_id: string;
  signed_at: string | null;
  user_signature?: string | null;
}

export interface MarketplaceAttorney {
  attorney_id: string;
  full_name: string;
  email: string;
  bar_state: string | null;
  bar_number: string | null;
  bar_verified: boolean;
  languages?: string[];
  location?: string | null;
}

export interface MarketplaceAttorneyAssignment {
  assignment_id: string;
  attorney_id: string;
  decision: string;
  assigned_at: string | null;
  reviewed_at: string | null;
  completed_at: string | null;
  checklist_responses?: Record<string, boolean>;
  attorney_notes?: string | null;
  attorney?: MarketplaceAttorney | null;
}

export interface QuestionnaireItem {
  id: string;
  label: string;
}

export interface QuestionnaireSection {
  id: string;
  title: string;
  required_for_execution: string;
  items: QuestionnaireItem[];
}

export interface MarketplaceQuestionnaireConfig {
  service: string;
  title: string;
  description: string;
  sections: QuestionnaireSection[];
  routing?: Record<string, unknown>;
}

export interface MarketplaceQuestionnaireResult {
  questionnaire_response_id: string;
  recommendation: string;
  advisory_reason: string | null;
  execution_reason: string | null;
  missing_required_items: string[];
  complexity_flags: string[];
}

export interface MarketplaceResultPayload {
  order_id: string;
  product_sku: string;
  summary: string | null;
  findings: MarketplaceFinding[];
  finding_count: number;
  next_steps: string[];
  artifacts: MarketplaceArtifact[];
  requires_fbar?: boolean;
  aggregate_max_balance_usd?: number;
  filing_deadline?: string | null;
  document_summary?: MarketplaceDocumentSummary[];
  comparisons?: MarketplaceComparison[];
  mailing_instructions?: MarketplaceMailingInstructions | null;
  receipt_number?: string | null;
  filing_confirmation?: string | null;
  filed_at?: string | null;
}

export interface Form8843FilingInstructions {
  scenario: string;
  headline: string;
  summary: string;
  filing_deadline: string | null;
  deadline_label: string;
  address_block: string;
  delivery_method: string;
  mailing_status: string;
  mail_required: boolean;
  can_mark_mailed: boolean;
  certified_mail_recommended: boolean;
  steps: string[];
  mailing_service_available: boolean;
  mailing_service_price_cents: number;
  mailing_service_note: string;
}

export interface Form8843OrderResponse {
  order_id: string;
  status: string;
  pdf_url: string | null;
  email_status: string | null;
  user_id?: string;
  delivery_method: string;
  filing_deadline: string | null;
  mailing_status: string;
  mailed_at: string | null;
  tracking_number: string | null;
  filing_instructions: Form8843FilingInstructions;
  mailing_service_available: boolean;
}

export interface MarketplaceOrder {
  user_id: string;
  order_id: string;
  product_sku: string;
  status: string;
  amount_cents: number;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  delivery_method: string;
  filing_deadline: string | null;
  mailing_status: string;
  mailed_at: string | null;
  tracking_number: string | null;
  product: MarketplaceProduct;
  intake_complete: boolean;
  result_ready: boolean;
  questionnaire_response_id?: string | null;
  chosen_mode?: string | null;
  agreement_signed?: boolean;
  agreement?: MarketplaceAgreement | null;
  attorney_assignment?: MarketplaceAttorneyAssignment | null;
  summary?: string | null;
  finding_count?: number;
  next_steps?: string[];
  artifacts?: MarketplaceArtifact[];
  pdf_url?: string | null;
  email_status?: string | null;
  filing_instructions?: Form8843FilingInstructions;
  mailing_service_available?: boolean;
  result?: MarketplaceResultPayload;
}

export interface Form8843GenerateResponse extends Form8843OrderResponse {
  user_id: string;
}

export interface Form8843MailingKitResponse {
  order_id: string;
  mailing_status: string;
  filing_deadline: string | null;
  address_block: string;
  filing_notes: string;
  mailing_label_text: string;
  envelope_template_text: string;
  recommended_service: string;
}

export interface MarketplaceAgreementResponse {
  order_id: string;
  agreement_text: string;
  signed: boolean;
  agreement?: MarketplaceAgreement | null;
}

export interface AttorneyDashboardResponse {
  attorney: MarketplaceAttorney | null;
  pending_cases: Array<{
    order_id: string;
    product_sku: string | null;
    status: string | null;
    decision: string;
    assigned_at: string | null;
    client_email: string | null;
    client_name: string | null;
  }>;
  completed_cases: Array<{
    order_id: string;
    product_sku: string | null;
    status: string | null;
    decision: string;
    assigned_at: string | null;
    client_email: string | null;
    client_name: string | null;
  }>;
  stats: {
    pending_review: number;
    completed_reviews: number;
    total_cases: number;
  };
}

export interface AttorneyCaseResponse {
  order: MarketplaceOrder;
  assignment: MarketplaceAttorneyAssignment | null;
  agreement: {
    agreement_id: string;
    signed_at: string | null;
    user_signature: string | null;
    agreement_text: string | null;
  } | null;
  checklist: {
    service: string;
    checklist: QuestionnaireItem[];
    decision: Record<string, string>;
  };
  intake_data: Record<string, unknown>;
  result: Record<string, unknown>;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail || body?.message || "Request failed");
  }
  return body as T;
}

export async function generateForm8843(payload: Form8843Request): Promise<Form8843GenerateResponse> {
  const response = await fetch(`${API}/form8843/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<Form8843GenerateResponse>(response);
}

export async function listMarketplaceProducts(includeInactive = false): Promise<MarketplaceProduct[]> {
  const response = await fetch(
    `${API}/marketplace/products${includeInactive ? "?include_inactive=true" : ""}`,
  );
  const body = await parseResponse<{ products: MarketplaceProduct[] }>(response);
  return body.products;
}

export async function getMarketplaceProduct(sku: string, includeInactive = false): Promise<MarketplaceProduct> {
  const response = await fetch(
    `${API}/marketplace/products/${encodeURIComponent(sku)}${includeInactive ? "?include_inactive=true" : ""}`,
  );
  return parseResponse<MarketplaceProduct>(response);
}

export async function createMarketplaceOrder(
  sku: string,
  options?: { questionnaire_response_id?: string; chosen_mode?: string },
): Promise<MarketplaceOrder> {
  const response = await fetch(`${API}/marketplace/orders`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ sku, ...options }),
  });
  return parseResponse<MarketplaceOrder>(response);
}

export async function getMarketplaceQuestionnaire(sku: string): Promise<MarketplaceQuestionnaireConfig> {
  const response = await fetch(`${API}/marketplace/products/${encodeURIComponent(sku)}/questionnaire`);
  return parseResponse<MarketplaceQuestionnaireConfig>(response);
}

export async function submitMarketplaceQuestionnaire(
  sku: string,
  responses: Array<{ item_id: string; checked: boolean }>,
): Promise<MarketplaceQuestionnaireResult> {
  const response = await fetch(`${API}/marketplace/products/${encodeURIComponent(sku)}/questionnaire`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ responses }),
  });
  return parseResponse<MarketplaceQuestionnaireResult>(response);
}

export async function listMarketplaceOrders(): Promise<MarketplaceOrder[]> {
  const response = await fetch(`${API}/marketplace/orders`, {
    headers: authHeaders(),
  });
  const body = await parseResponse<{ orders: MarketplaceOrder[] }>(response);
  return body.orders;
}

export async function getMarketplaceOrder(orderId: string): Promise<MarketplaceOrder> {
  const response = await fetch(`${API}/marketplace/orders/${encodeURIComponent(orderId)}`, {
    headers: authHeaders(),
  });
  return parseResponse<MarketplaceOrder>(response);
}

export async function saveMarketplaceOrderJsonIntake(
  orderId: string,
  payload: Record<string, unknown>,
): Promise<MarketplaceOrder> {
  const response = await fetch(`${API}/marketplace/orders/${encodeURIComponent(orderId)}/intake`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse<MarketplaceOrder>(response);
}

export async function saveMarketplaceOrderFileIntake(
  orderId: string,
  formData: FormData,
): Promise<MarketplaceOrder> {
  const response = await fetch(`${API}/marketplace/orders/${encodeURIComponent(orderId)}/intake`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  return parseResponse<MarketplaceOrder>(response);
}

export async function processMarketplaceOrder(orderId: string): Promise<MarketplaceOrder> {
  const response = await fetch(`${API}/marketplace/orders/${encodeURIComponent(orderId)}/process`, {
    method: "POST",
    headers: authHeaders(),
  });
  return parseResponse<MarketplaceOrder>(response);
}

export async function getMarketplaceOrderResult(orderId: string): Promise<MarketplaceResultPayload> {
  const response = await fetch(`${API}/marketplace/orders/${encodeURIComponent(orderId)}/result`, {
    headers: authHeaders(),
  });
  return parseResponse<MarketplaceResultPayload>(response);
}

export async function markMarketplaceOrderMailed(
  orderId: string,
  payload: { mailed_at?: string; tracking_number?: string } = {},
): Promise<MarketplaceOrder> {
  const response = await fetch(`${API}/marketplace/orders/${encodeURIComponent(orderId)}/mark-mailed`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse<MarketplaceOrder>(response);
}

export async function getMarketplaceAgreement(orderId: string): Promise<MarketplaceAgreementResponse> {
  const response = await fetch(`${API}/marketplace/orders/${encodeURIComponent(orderId)}/agreement`, {
    headers: authHeaders(),
  });
  return parseResponse<MarketplaceAgreementResponse>(response);
}

export async function signMarketplaceAgreement(
  orderId: string,
  payload: { signature: string; agreement_text_snapshot: string },
): Promise<{
  agreement_id: string;
  signed_at: string | null;
  order: MarketplaceOrder;
  attorney_assignment: MarketplaceAttorneyAssignment | null;
}> {
  const response = await fetch(`${API}/marketplace/orders/${encodeURIComponent(orderId)}/sign-agreement`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function getAttorneyDashboard(): Promise<AttorneyDashboardResponse> {
  const response = await fetch(`${API}/attorney/dashboard`, {
    headers: authHeaders(),
  });
  return parseResponse<AttorneyDashboardResponse>(response);
}

export async function getAttorneyCase(orderId: string): Promise<AttorneyCaseResponse> {
  const response = await fetch(`${API}/attorney/cases/${encodeURIComponent(orderId)}`, {
    headers: authHeaders(),
  });
  return parseResponse<AttorneyCaseResponse>(response);
}

export async function reviewAttorneyCase(
  orderId: string,
  payload: {
    checklist_responses: Record<string, boolean>;
    decision: string;
    notes?: string;
  },
): Promise<{
  decision_recorded: boolean;
  next_action: string;
  assignment: MarketplaceAttorneyAssignment | null;
  order: MarketplaceOrder;
}> {
  const response = await fetch(`${API}/attorney/cases/${encodeURIComponent(orderId)}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function fileAttorneyCase(
  orderId: string,
  payload: { receipt_number: string; filing_confirmation?: string },
): Promise<{
  filed_at: string;
  receipt_number: string;
  order: MarketplaceOrder;
}> {
  const response = await fetch(`${API}/attorney/cases/${encodeURIComponent(orderId)}/file`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function getForm8843Order(orderId: string): Promise<Form8843OrderResponse> {
  const response = await fetch(`${API}/form8843/orders/${orderId}`);
  return parseResponse<Form8843OrderResponse>(response);
}

export async function markForm8843Mailed(
  orderId: string,
  payload: { mailed_at?: string; tracking_number?: string } = {},
): Promise<Form8843OrderResponse> {
  const response = await fetch(`${API}/form8843/orders/${orderId}/mark-mailed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<Form8843OrderResponse>(response);
}

export async function getForm8843MailingKit(orderId: string): Promise<Form8843MailingKitResponse> {
  const response = await fetch(`${API}/form8843/orders/${orderId}/mailing-kit`);
  return parseResponse<Form8843MailingKitResponse>(response);
}

export function resolveForm8843PdfUrl(pdfUrl: string | null): string | null {
  if (!pdfUrl) {
    return null;
  }
  if (pdfUrl.startsWith("http://") || pdfUrl.startsWith("https://")) {
    return pdfUrl;
  }
  return `${API}${pdfUrl.replace(/^\/api/, "")}`;
}

export function resolveMarketplaceArtifactUrl(url: string | null): string | null {
  if (!url) {
    return null;
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  return `${API}${url.replace(/^\/api/, "")}`;
}

export async function downloadMarketplaceArtifact(url: string, filename: string): Promise<void> {
  const targetUrl = resolveMarketplaceArtifactUrl(url);
  if (!targetUrl) {
    throw new Error("Artifact URL is not available");
  }

  const response = await fetch(targetUrl, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || "Could not download artifact");
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
