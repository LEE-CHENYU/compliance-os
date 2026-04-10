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
  result_ready: boolean;
  pdf_url?: string | null;
  email_status?: string | null;
  filing_instructions?: Form8843FilingInstructions;
  mailing_service_available?: boolean;
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
