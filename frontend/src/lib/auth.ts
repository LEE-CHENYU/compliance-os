/**
 * Auth client — JWT storage, register, login, helpers.
 */

const API = typeof window !== "undefined" && window.location.hostname === "localhost"
  ? "http://localhost:8000/api/auth"
  : "/api/auth";

export interface AuthUser {
  user_id: string;
  email: string;
  token: string;
}

type MixpanelClient = {
  identify?: (distinctId: string) => void;
  register?: (properties: Record<string, unknown>) => void;
  reset?: () => void;
  people?: {
    set?: (properties: Record<string, unknown>) => void;
  };
};

function getMixpanel(): MixpanelClient | null {
  if (typeof window === "undefined") return null;
  return (window as Window & { mixpanel?: MixpanelClient }).mixpanel ?? null;
}

function safelyInvokeMixpanel(action: () => void) {
  try {
    action();
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.warn("Mixpanel call skipped", error);
    }
  }
}

export function syncMixpanelUser(data: { user_id: string; email: string }) {
  if (process.env.NODE_ENV !== "production") return;
  const mixpanel = getMixpanel();
  if (!mixpanel) return;

  safelyInvokeMixpanel(() => {
    mixpanel.identify?.(data.user_id);
  });
  safelyInvokeMixpanel(() => {
    mixpanel.register?.({
      user_id: data.user_id,
      email: data.email,
    });
  });
  safelyInvokeMixpanel(() => {
    mixpanel.people?.set?.({
      $email: data.email,
      email: data.email,
    });
  });
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("guardian_token");
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("guardian_token");
  const user_id = localStorage.getItem("guardian_user_id");
  const email = localStorage.getItem("guardian_email");
  if (!token || !user_id || !email) return null;
  return { token, user_id, email };
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function saveAuth(data: { token: string; user_id: string; email: string }) {
  localStorage.setItem("guardian_token", data.token);
  localStorage.setItem("guardian_user_id", data.user_id);
  localStorage.setItem("guardian_email", data.email);
  syncMixpanelUser(data);
}

export function logout() {
  localStorage.removeItem("guardian_token");
  localStorage.removeItem("guardian_user_id");
  localStorage.removeItem("guardian_email");
  getMixpanel()?.reset?.();
}

export async function register(email: string, password: string): Promise<AuthUser> {
  const resp = await fetch(`${API}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed");
  }
  const data = await resp.json();
  saveAuth(data);
  return data;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const resp = await fetch(`${API}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  const data = await resp.json();
  saveAuth(data);
  return data;
}

export async function getGoogleAuthUrl(): Promise<string> {
  const resp = await fetch(`${API}/google/url`);
  const data = await resp.json();
  return data.url;
}

export function handleGoogleCallback(params: URLSearchParams): AuthUser | null {
  const token = params.get("token");
  const email = params.get("email");
  const user_id = params.get("user_id");
  if (token && email && user_id) {
    const data = { token, email, user_id };
    saveAuth(data);
    return data;
  }
  return null;
}

export async function linkCheckToUser(checkId: string): Promise<void> {
  const token = getToken();
  if (!token) return;
  await fetch(`${API}/link-check/${checkId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}
