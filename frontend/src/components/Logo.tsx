"use client";

/**
 * Guardian wordmark — stacked-bars 3D logo + "Guardian" text, linked to /.
 *
 * Use this on every page header for brand consistency. Pair with an
 * optional subtitle prop (e.g. "Data Room", "Docs", "Connect") that
 * renders muted on sm+ screens.
 */
export function Logo({ subtitle, size = "sm" }: { subtitle?: string; size?: "sm" | "md" }) {
  const barW = size === "md" ? 28 : 22;
  const barH = size === "md" ? 5.5 : 4.5;
  const gap = size === "md" ? 3 : 2.5;
  const containerH = size === "md" ? 28 : 22;

  return (
    <a
      href="/"
      className="flex items-center gap-2.5 group select-none"
      aria-label="Guardian home"
    >
      <div
        style={{
          width: barW,
          height: containerH,
          display: "flex",
          flexDirection: "column",
          gap,
          transform: "perspective(200px) rotateX(-8deg) rotateY(12deg)",
        }}
        className="group-hover:opacity-90 transition-opacity"
      >
        <div style={{ height: barH, background: "linear-gradient(135deg, #5b8dee, #4a74d4)", borderRadius: 1, width: barW, transform: "translateX(2px)" }} />
        <div style={{ height: barH, background: "linear-gradient(135deg, #5b8dee, #4a74d4)", borderRadius: 1, width: barW, transform: "translateX(-1px)" }} />
        <div style={{ height: barH, background: "linear-gradient(135deg, #5b8dee, #4a74d4)", borderRadius: 1, width: barW, transform: "translateX(3px)" }} />
      </div>
      <span className={`${size === "md" ? "text-base" : "text-sm"} font-bold tracking-tight text-[#0d1424]`}>
        Guardian
      </span>
      {subtitle ? (
        <span className={`${size === "md" ? "text-base" : "text-sm"} text-[#8b97ad] font-normal hidden sm:inline`}>
          · {subtitle}
        </span>
      ) : null}
    </a>
  );
}
