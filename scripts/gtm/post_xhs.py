"""Post carousel images to 小红书 via Playwright.

Usage:
    python scripts/gtm/post_xhs.py --login
    python scripts/gtm/post_xhs.py --post 1
    python scripts/gtm/post_xhs.py --post 2
    python scripts/gtm/post_xhs.py --post 3
    python scripts/gtm/post_xhs.py --post banner
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

PNG_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "gtm" / "xiaohongshu" / "png"
SESSION_DIR = Path(__file__).resolve().parents[2] / ".xhs-session"

POSTS = {
    "1": {
        "title": "留学生报税最容易忽略的一张表｜Form 8843 免费生成",
        "images": [
            "post1-cover.png",
            "post1-slide1.png",
            "post1-slide2.png",
            "post1-slide3.png",
            "post1-cta.png",
        ],
        "body": (
            "每个F-1/J-1留学生每年都必须提交Form 8843，即使你没有任何收入！\n\n"
            "大部分同学都不知道这张表的存在，但不交可能会影响你未来的绿卡和H-1B申请。\n\n"
            "Guardian 免费帮你一键生成，2分钟填完，直接下载PDF打印签名邮寄。\n\n"
            "截止日期：6月15日\n"
            "🔗 链接见评论区置顶\n\n"
            "#留学生报税 #Form8843 #F1签证 #J1签证 #留学生必看 #美国报税 #IRS #Guardian"
        ),
    },
    "2": {
        "title": "Form 8843 完全指南｜免费生成器",
        "images": [
            "post2-cover.png",
            "post2-slide1.png",
            "post2-slide2.png",
            "post2-cta.png",
        ],
        "body": (
            "Form 8843 完全指南 — 收藏这篇就够了！\n\n"
            "✅ 谁要交：所有F-1/J-1/M-1/Q签证持有人\n"
            "✅ 什么时候：每年6月15日前\n"
            "✅ 怎么交：打印签名后邮寄到IRS Austin, TX\n\n"
            "Guardian 帮你免费生成PDF，不需要注册，2分钟搞定前两步。\n\n"
            "⚠️ Form 8843不能电子提交，必须邮寄纸质版！\n\n"
            "🔗 链接见评论区置顶\n\n"
            "#Form8843 #留学生报税指南 #F1签证 #美国留学 #报税攻略 #IRS #Guardian #留学生必看"
        ),
    },
    "3": {
        "title": "在美华人必备的合规工具｜Guardian",
        "images": [
            "post3-cover.png",
            "post3-slide1.png",
            "post3-slide2.png",
            "post3-slide3.png",
            "post3-cta.png",
        ],
        "body": (
            "从留学生到创业者，你的每一个身份阶段都有不同的合规风险。\n\n"
            "Guardian 是一个 AI 驱动的移民合规助手，帮你同时检查：\n"
            "📋 移民文件（H-1B, O-1, 绿卡）\n"
            "📋 税务文件（FBAR, 1040-NR, 83(b)）\n"
            "📋 公司文件（Entity Formation, QSBS）\n\n"
            "别人只查一个领域，Guardian 三个一起查 — 你的律师看不到的跨领域矛盾，它能看到。\n\n"
            "🎓 留学生 → 💼 职场新人 → 🚀 创业者，全阶段覆盖\n\n"
            "免费工具立即可用，专业服务$29起。\n\n"
            "🔗 链接见评论区置顶\n\n"
            "#在美华人 #移民合规 #H1B #创业者 #留学生 #美国报税 #Guardian #AI工具"
        ),
    },
    "banner": {
        "title": "Guardian｜AI移民合规助手 — 留学生·创业者·新移民",
        "images": ["banner.png"],
        "body": (
            "Guardian — 一站式移民合规检查平台\n\n"
            "Immigration × Tax × Corporate 跨领域文件交叉检查\n"
            "从F-1学生到创业者，帮你检查每一份文件。\n\n"
            "🎓 留学生：Form 8843, 1040-NR, OPT\n"
            "💼 职场新人：H-1B, FBAR, 税务合规\n"
            "🚀 创业者：O-1, EB-1, 83(b), Entity\n\n"
            "免费工具 + 专业服务，中英双语。\n\n"
            "🔗 链接见评论区置顶\n\n"
            "#Guardian #移民合规 #AI工具 #在美华人 #留学生 #H1B #创业者"
        ),
    },
}

PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"
LOGIN_URL = "https://creator.xiaohongshu.com"


async def login_session():
    """Open browser for manual login — auto-detects when login completes."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(LOGIN_URL)

        print("=" * 55)
        print("Browser open — log in to 小红书 manually.")
        print("Waiting up to 5 minutes for login to complete...")
        print("=" * 55)

        # Poll until we leave the login page (URL no longer contains /login or /sso)
        deadline = asyncio.get_event_loop().time() + 300  # 5 min
        while asyncio.get_event_loop().time() < deadline:
            current_url = page.url
            if "creator.xiaohongshu.com" in current_url and "login" not in current_url and "sso" not in current_url:
                # Extra check: look for a creator-dashboard element
                try:
                    await page.wait_for_selector(
                        '[class*="creator"], [class*="home"], [class*="publish"], nav',
                        timeout=3000,
                    )
                    print(f"Login detected — current URL: {current_url}")
                    break
                except Exception:
                    pass
            await asyncio.sleep(2)
        else:
            print("Timed out waiting for login. Session may be incomplete.")

        print(f"Session saved to {SESSION_DIR}")
        await asyncio.sleep(1)
        await ctx.close()


async def post_to_xhs(post_key: str):
    """Upload images, fill title & body, then auto-publish."""
    post = POSTS[post_key]

    # Verify images exist
    image_paths = []
    for img in post["images"]:
        p = PNG_DIR / img
        if not p.exists():
            print(f"ERROR: Missing {p}\nRun screenshot_slides.py first.")
            return
        image_paths.append(str(p))

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        print(f"\nPosting: {post['title']}")
        print(f"Images:  {len(image_paths)}")

        # Navigate to publish page
        await page.goto(PUBLISH_URL)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # Check we're not on a login redirect
        if "login" in page.url or "sso" in page.url:
            print("ERROR: Not logged in. Run --login first.")
            await ctx.close()
            return

        # ── Switch to 图文笔记 (image post) tab ───────────────────────────────
        img_tab = page.locator(
            ':has-text("图文"), '
            '[class*="image-tab"], '
            '[class*="photo"], '
            'button:has-text("图文笔记")'
        ).first
        try:
            await img_tab.click(timeout=5000)
            await asyncio.sleep(1)
            print("  ✓ Switched to 图文笔记 tab")
        except Exception:
            print("  ~ Tab click skipped (may already be on image post)")

        # ── Upload images ──────────────────────────────────────────────────────
        # Target the image-specific file input (not the video one)
        file_input = page.locator(
            'input[type="file"][accept*="jpg"], '
            'input[type="file"][accept*="png"], '
            'input[type="file"][accept*="jpeg"], '
            'input[type="file"][accept*="image"], '
            'input[type="file"][accept*="gif"], '
            'input[type="file"][accept*="webp"]'
        ).first
        await file_input.set_input_files(image_paths)
        print(f"  ✓ Uploaded {len(image_paths)} images")

        # Wait for thumbnails to render
        await asyncio.sleep(4)

        # ── Fill title ─────────────────────────────────────────────────────────
        title_sel = (
            '#note-title, '
            '[placeholder*="标题"], '
            '[class*="title"] input, '
            '[class*="title"] textarea'
        )
        title_input = page.locator(title_sel).first
        await title_input.click()
        await title_input.fill(post["title"])
        print(f"  ✓ Title set")

        # ── Fill body ──────────────────────────────────────────────────────────
        body_sel = (
            '#note-content, '
            '[contenteditable="true"], '
            '[placeholder*="正文"], '
            '[class*="content"] [contenteditable], '
            '.ql-editor'
        )
        body_editor = page.locator(body_sel).first
        await body_editor.click()

        for line in post["body"].split("\n"):
            await page.keyboard.type(line, delay=8)
            await page.keyboard.press("Enter")
        print(f"  ✓ Body filled")

        await asyncio.sleep(1)

        # ── Click publish ──────────────────────────────────────────────────────
        publish_btn = page.locator(
            'button:has-text("发布"), '
            '[class*="publish-btn"], '
            '[class*="submit"]'
        ).last
        await publish_btn.scroll_into_view_if_needed()
        await publish_btn.click()
        print(f"  ✓ Publish clicked")

        # Wait for success signal (URL change or success toast)
        try:
            await page.wait_for_url("**/success**", timeout=15000)
            print("  ✓ Published successfully!")
        except Exception:
            # Try waiting for a success toast instead
            try:
                await page.wait_for_selector(
                    '[class*="success"], [class*="toast"], :has-text("发布成功")',
                    timeout=10000,
                )
                print("  ✓ Published successfully!")
            except Exception:
                current = page.url
                print(f"  ? Publish result unclear — current URL: {current}")
                print("  Check the browser window to confirm.")
                await asyncio.sleep(5)

        await asyncio.sleep(2)
        await ctx.close()


async def main():
    parser = argparse.ArgumentParser(description="Post to 小红书 via Playwright")
    parser.add_argument("--login", action="store_true", help="Open browser for manual login")
    parser.add_argument("--post", choices=["1", "2", "3", "banner"], help="Which post to publish")
    args = parser.parse_args()

    if args.login:
        await login_session()
    elif args.post:
        await post_to_xhs(args.post)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
