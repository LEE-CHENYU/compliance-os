"""Generate promotional assets for Anthropic Connector Directory submission.

Outputs to frontend/public/assets/:
  - guardian-logo.svg  — the stacked-bars mark (trademark-ready asset)
  - guardian-logo-512.png — 512x512 filled tile variant for app icon slots
  - screenshots/*.png — 1280x800 screenshots of key surfaces, captured
    from the live site via Playwright

Run:
  python scripts/generate_submission_assets.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None  # type: ignore


SITE = "https://guardiancompliance.app"
OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "assets"
SHOTS = OUT / "screenshots"


LOGO_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="bar" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#5b8dee"/>
      <stop offset="100%" stop-color="#4a74d4"/>
    </linearGradient>
  </defs>
  <g transform="translate(12, 18)">
    <rect x="2"  y="0"  width="40" height="7" rx="1" fill="url(#bar)"/>
    <rect x="-1" y="10" width="40" height="7" rx="1" fill="url(#bar)"/>
    <rect x="3"  y="20" width="40" height="7" rx="1" fill="url(#bar)"/>
  </g>
</svg>
"""


def write_logo(path: Path) -> None:
    path.write_text(LOGO_SVG, encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size} bytes)")


def write_logo_png_tile(path: Path, size: int = 512) -> None:
    """Solid-fill tile with stacked-bars centered — for app-icon slots."""
    import io

    from PIL import Image, ImageDraw

    img = Image.new("RGB", (size, size), (13, 20, 36))  # #0d1424
    draw = ImageDraw.Draw(img)
    bar_w = int(size * 0.56)
    bar_h = int(size * 0.11)
    gap = int(size * 0.04)
    start_y = (size - (3 * bar_h + 2 * gap)) // 2
    left = (size - bar_w) // 2
    offsets = [+int(size * 0.025), -int(size * 0.015), +int(size * 0.04)]
    for i, off in enumerate(offsets):
        y = start_y + i * (bar_h + gap)
        draw.rounded_rectangle(
            [(left + off, y), (left + off + bar_w, y + bar_h)],
            radius=max(2, bar_h // 6),
            fill=(91, 141, 238),  # #5b8dee
        )
    img.save(path, "PNG", optimize=True)
    print(f"wrote {path} ({path.stat().st_size} bytes)")


async def capture_shots(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    shots = [
        ("01-landing.png",         f"{SITE}/",              1280, 800,  False),
        ("02-docs-install.png",    f"{SITE}/docs/install",  1280, 1600, True),
        ("03-connect.png",         f"{SITE}/connect",       1280, 900,  False),
        ("04-demo-data-room.png",  f"{SITE}/share/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6InNoYXJlIiwiZm9sZGVyIjoiL2RhdGEvY2FzZXMvZGVtb19oMWJfcGV0aXRpb24iLCJ0ZW1wbGF0ZV9pZCI6ImgxYl9wZXRpdGlvbiIsInJlY2lwaWVudCI6IlByb3NwZWN0aXZlIENvdW5zZWwgKERlbW8pIiwiaXNzdWVyIjoiR3VhcmRpYW4gRGVtbyIsImlhdCI6MTc3NjQ1MTMxNywiZXhwIjoxNzg0MjI3MzE3fQ.sLIiEWlFztKYbsfcvniBotcxhYu9pcoVBLus3dGxeCE", 1280, 1600, True),
        ("05-privacy.png",         f"{SITE}/privacy",       1280, 1000, False),
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for fname, url, w, h, full_page in shots:
            ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(800)
            out = target_dir / fname
            await page.screenshot(path=str(out), full_page=full_page)
            print(f"shot {out} ({out.stat().st_size // 1024} KB)")
            await ctx.close()
        await browser.close()


async def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    write_logo(OUT / "guardian-logo.svg")
    write_logo_png_tile(OUT / "guardian-logo-512.png", 512)
    write_logo_png_tile(OUT / "guardian-logo-1024.png", 1024)
    if async_playwright is None:
        print("playwright not installed; skipping screenshots. Install with:")
        print("  pip install playwright && playwright install chromium")
        return 0
    print("generating screenshots (network access required)...")
    try:
        await capture_shots(SHOTS)
    except Exception as exc:
        print(f"screenshot capture failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
