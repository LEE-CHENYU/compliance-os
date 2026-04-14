"""Generate 1080×1440 PNG screenshots from all XHS HTML slides."""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

SLIDES_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "gtm" / "xiaohongshu"
OUTPUT_DIR = SLIDES_DIR / "png"


async def screenshot_all():
    html_files = sorted(SLIDES_DIR.glob("*.html"))
    if not html_files:
        print(f"No HTML files found in {SLIDES_DIR}")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1440})

        for html_file in html_files:
            if html_file.name == "shared.css":
                continue
            png_name = html_file.stem + ".png"
            png_path = OUTPUT_DIR / png_name

            await page.goto(f"file://{html_file}")
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(png_path), full_page=False)
            print(f"  ✓ {png_name}")

        await browser.close()

    print(f"\nDone — {len(list(OUTPUT_DIR.glob('*.png')))} PNGs in {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(screenshot_all())
