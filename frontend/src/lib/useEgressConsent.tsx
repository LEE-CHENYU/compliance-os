"use client";
import { useCallback, useRef, useState } from "react";
import { EgressConsentModal } from "@/components/EgressConsentModal";
import { grant, hasConsent, type ConsentScope, type EgressType } from "@/lib/consent";

interface Args {
  egressType: EgressType;
  purpose: string;
  destination: string;
  dataCategories: string[];
}

// Returns `ensure()` — resolves true if upload may proceed (consent already held
// or just granted), false if denied — plus the modal element to render.
export function useEgressConsent({ egressType, purpose, destination, dataCategories }: Args) {
  const [open, setOpen] = useState(false);
  const resolver = useRef<((ok: boolean) => void) | null>(null);

  const ensure = useCallback((): Promise<boolean> => {
    if (hasConsent(egressType, purpose)) return Promise.resolve(true);
    setOpen(true);
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
    });
  }, [egressType, purpose]);

  const onDecide = useCallback((scope: ConsentScope) => {
    setOpen(false);
    if (scope !== "deny") grant({ egressType, purpose, destination, dataCategories, scope });
    resolver.current?.(scope !== "deny");
    resolver.current = null;
  }, [egressType, purpose, destination, dataCategories]);

  const modal = (
    <EgressConsentModal open={open} destination={destination} dataCategories={dataCategories} onDecide={onDecide} />
  );

  return { ensure, modal };
}
