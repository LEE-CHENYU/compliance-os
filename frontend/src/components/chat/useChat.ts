"use client";

import { useCallback, useEffect, useState } from "react";
import { ChatMessage, getChat, sendChat } from "@/lib/api";

export function useChat(caseId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    getChat(caseId)
      .then((data) => setMessages(data.messages))
      .finally(() => setLoading(false));
  }, [caseId]);

  const send = useCallback(
    async (content: string) => {
      setSending(true);
      try {
        const data = await sendChat(caseId, content);
        setMessages(data.messages);
      } finally {
        setSending(false);
      }
    },
    [caseId]
  );

  return { messages, loading, sending, send };
}
