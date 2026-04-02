interface Props {
  role: "user" | "assistant";
  content: string;
}

export default function ChatMessageBubble({ role, content }: Props) {
  return (
    <div className={`flex ${role === "user" ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 text-sm ${
          role === "user"
            ? "bg-stone-800 text-white"
            : "bg-stone-100 text-stone-800"
        }`}
      >
        <div className="whitespace-pre-wrap">{content}</div>
      </div>
    </div>
  );
}
