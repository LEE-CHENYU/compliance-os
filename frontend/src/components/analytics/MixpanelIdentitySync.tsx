"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";

import { getUser, syncMixpanelUser } from "@/lib/auth";

export default function MixpanelIdentitySync() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const user = getUser();

    if (!user) {
      return;
    }

    syncMixpanelUser(user);
  }, [pathname, searchParams]);

  return null;
}
