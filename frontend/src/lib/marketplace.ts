"use client";

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
}

export interface Form8843GenerateResponse {
  order_id: string;
  user_id: string;
  pdf_url: string;
}

export interface Form8843OrderResponse {
  order_id: string;
  status: string;
  pdf_url: string | null;
  email_status: string | null;
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

export async function getForm8843Order(orderId: string): Promise<Form8843OrderResponse> {
  const response = await fetch(`${API}/form8843/orders/${orderId}`);
  return parseResponse<Form8843OrderResponse>(response);
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
