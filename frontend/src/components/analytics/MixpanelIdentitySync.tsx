"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

import { getUser, syncMixpanelUser } from "@/lib/auth";

export default function MixpanelIdentitySync() {
  const pathname = usePathname();

  useEffect(() => {
    const user = getUser();

    if (!user) {
      return;
    }

    syncMixpanelUser(user);
  }, [pathname]);

  return null;
}
