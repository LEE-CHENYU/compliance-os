"use client";
import type { ConsentScope } from "@/lib/consent";

export interface EgressConsentModalProps {
  open: boolean;
  destination: string;
  dataCategories: string[];
  onDecide: (scope: ConsentScope) => void;
}

export function EgressConsentModal({ open, destination, dataCategories, onDecide }: EgressConsentModalProps) {
  if (!open) return null;
  return (
    <div
      data-testid="egress-consent-modal"
      style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(13,20,36,0.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}
    >
      <div style={{ background: "#fff", borderRadius: 16, maxWidth: 440, width: "100%", padding: 28, boxShadow: "0 20px 60px rgba(13,20,36,0.25)" }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: "#0d1424" }}>Approve upload?</h3>
        <p style={{ fontSize: 14, color: "#556480", lineHeight: 1.6, marginBottom: 8 }}>
          Your {dataCategories.join(", ")} will be uploaded to <strong>{destination}</strong> to extract fields. Nothing is sent until you approve.
        </p>
        <p style={{ fontSize: 12.5, color: "#8e9ab5", lineHeight: 1.6, marginBottom: 20 }}>
          Prefer your documents never leave your device? Use the local Guardian extension.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <button data-testid="consent-always" onClick={() => onDecide("always")} style={btnPrimary}>Always allow</button>
          <button data-testid="consent-session" onClick={() => onDecide("session")} style={btn}>Allow for this session</button>
          <button data-testid="consent-once" onClick={() => onDecide("once")} style={btn}>Allow once</button>
          <button data-testid="consent-deny" onClick={() => onDecide("deny")} style={btnGhost}>Deny</button>
        </div>
      </div>
    </div>
  );
}

const btnBase: React.CSSProperties = { padding: "10px 16px", borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer", border: "1px solid rgba(91,141,238,0.2)" };
const btnPrimary: React.CSSProperties = { ...btnBase, background: "#5b8dee", color: "#fff", border: "none" };
const btn: React.CSSProperties = { ...btnBase, background: "rgba(91,141,238,0.06)", color: "#3a5a8c" };
const btnGhost: React.CSSProperties = { ...btnBase, background: "transparent", color: "#8e9ab5" };
