"use client";

import { useState } from "react";
import { useChat } from "./useChat";
import ChatMessageBubble from "./ChatMessage";

interface Props {
  caseId: string;
}

export default function ChatPanel({ caseId }: Props) {
  const { messages, loading, sending, send } = useChat(caseId);
  const [input, setInput] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sending) return;
    const text = input;
    setInput("");
    await send(text);
  };

  if (loading) return <p className="text-stone-400 text-sm">Loading follow-up questions...</p>;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide">Follow-Up</h3>
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {messages.map((m) => (
          <ChatMessageBubble key={m.id} role={m.role} content={m.content} />
        ))}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your response..."
          disabled={sending}
          className="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-stone-500 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || sending}
          className="rounded-lg bg-stone-800 px-4 py-2 text-sm text-white disabled:opacity-50 hover:bg-stone-700"
        >
          {sending ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
