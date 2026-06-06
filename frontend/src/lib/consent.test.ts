import { beforeEach, describe, expect, it } from "vitest";
import { hasConsent, grant, revoke, _resetSessionForTest } from "./consent";

const KEY = { egressType: "web_doc_upload", purpose: "extraction" } as const;

beforeEach(() => {
  localStorage.clear();
  _resetSessionForTest();
});

describe("consent store", () => {
  it("has no consent initially", () => {
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(false);
  });

  it("once does not persist", () => {
    grant({ egressType: KEY.egressType, purpose: KEY.purpose, destination: "d", dataCategories: ["x"], scope: "once" });
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(false);
  });

  it("session persists in-memory but not in localStorage", () => {
    grant({ egressType: KEY.egressType, purpose: KEY.purpose, destination: "d", dataCategories: ["x"], scope: "session" });
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(true);
    expect(localStorage.getItem("guardian_consent")).toBeNull();
  });

  it("always persists in localStorage and survives a session reset", () => {
    grant({ egressType: KEY.egressType, purpose: KEY.purpose, destination: "d", dataCategories: ["x"], scope: "always" });
    _resetSessionForTest(); // simulate reload (memory cleared, localStorage kept)
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(true);
  });

  it("revoke clears an always grant", () => {
    grant({ egressType: KEY.egressType, purpose: KEY.purpose, destination: "d", dataCategories: ["x"], scope: "always" });
    revoke(KEY.egressType, KEY.purpose);
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(false);
  });
});
