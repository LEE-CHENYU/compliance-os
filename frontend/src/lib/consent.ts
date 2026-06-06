// Egress consent store. `always` → localStorage; `session` → in-memory; `once` → not stored.
// Keyed by `${egressType}:${purpose}`.

export type EgressType = "web_doc_upload" | "share_data_room";
export type ConsentScope = "once" | "session" | "always" | "deny";

export interface ConsentRecord {
  egressType: EgressType;
  purpose: string;
  destination: string;
  dataCategories: string[];
  scope: ConsentScope;
}

const STORE_KEY = "guardian_consent";
const sessionGrants = new Set<string>();

function k(egressType: string, purpose: string): string {
  return `${egressType}:${purpose}`;
}

function loadAlways(): Record<string, true> {
  if (typeof localStorage === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function hasConsent(egressType: string, purpose: string): boolean {
  if (sessionGrants.has(k(egressType, purpose))) return true;
  return loadAlways()[k(egressType, purpose)] === true;
}

export function grant(record: ConsentRecord): void {
  if (record.scope === "always") {
    const all = loadAlways();
    all[k(record.egressType, record.purpose)] = true;
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(all));
    } catch {
      sessionGrants.add(k(record.egressType, record.purpose)); // fallback: treat as session
    }
  } else if (record.scope === "session") {
    sessionGrants.add(k(record.egressType, record.purpose));
  }
  // "once" and "deny": nothing stored.
}

export function revoke(egressType: string, purpose: string): void {
  sessionGrants.delete(k(egressType, purpose));
  const all = loadAlways();
  delete all[k(egressType, purpose)];
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

// Test-only: clear in-memory session grants (simulates a page reload).
export function _resetSessionForTest(): void {
  sessionGrants.clear();
}
