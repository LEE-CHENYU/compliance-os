/**
 * Brand marks for the MCP host apps, rendered as inline SVGs.
 * Colors follow each vendor's public brand palette (Anthropic coral
 * #D97757, OpenAI monochrome) but shapes are simplified/abstracted so
 * they're recognizable without being pixel-copies of the trademarked
 * logos. Sized to fit the 40×40 tile used in the app pickers.
 */

type AppId = "claude-desktop" | "claude-code" | "codex";

function ClaudeStar({ className = "" }: { className?: string }) {
  // Anthropic's Claude mark — simplified 8-ray star
  return (
    <svg viewBox="0 0 32 32" className={className} fill="currentColor" aria-hidden>
      <path d="M16 1.5 L17.3 12.3 L25.3 5.3 L20.1 14.8 L30.5 16 L20.1 17.2 L25.3 26.7 L17.3 19.7 L16 30.5 L14.7 19.7 L6.7 26.7 L11.9 17.2 L1.5 16 L11.9 14.8 L6.7 5.3 L14.7 12.3 Z" />
    </svg>
  );
}

function OpenAIKnot({ className = "" }: { className?: string }) {
  // OpenAI's hexagonal rosette, simplified — 3 lobes
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="16" cy="16" r="11" />
      <path d="M16 5.5 V26.5" />
      <path d="M6.9 10.75 L25.1 21.25" />
      <path d="M6.9 21.25 L25.1 10.75" />
    </svg>
  );
}

function TerminalMark({ className = "" }: { className?: string }) {
  // Claude Code = CLI — CLI prompt overlay
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M8 11 L13 16 L8 21" />
      <path d="M16 22 H24" />
    </svg>
  );
}

export function AppIcon({
  app,
  selected = false,
  size = 40,
}: {
  app: AppId;
  selected?: boolean;
  size?: number;
}) {
  // Tile palette per app
  const palettes = {
    "claude-desktop": {
      bg: selected ? "#F4E7DD" : "#FAF4EE",
      fg: "#D97757",
      border: selected ? "#D97757" : "transparent",
    },
    "claude-code": {
      bg: selected ? "#0d1424" : "#1a2036",
      fg: "#D97757",
      border: selected ? "#D97757" : "transparent",
    },
    codex: {
      bg: selected ? "#0d1424" : "#1a2036",
      fg: "#ffffff",
      border: selected ? "#ffffff" : "transparent",
    },
  } as const;

  const p = palettes[app];

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.3,
        background: p.bg,
        color: p.fg,
        border: `1.5px solid ${p.border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {app === "claude-desktop" && (
        <ClaudeStar className="w-[62%] h-[62%]" />
      )}
      {app === "claude-code" && (
        <div className="relative w-full h-full">
          <ClaudeStar className="absolute inset-[18%] opacity-25" />
          <TerminalMark className="absolute inset-0 w-full h-full" />
        </div>
      )}
      {app === "codex" && (
        <OpenAIKnot className="w-[62%] h-[62%]" />
      )}
    </div>
  );
}

export type { AppId };
