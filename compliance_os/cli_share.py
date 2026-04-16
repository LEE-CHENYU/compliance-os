"""CLI to issue data-room share links.

Usage:
    guardian-share h1b /path/to/folder
    guardian-share h1b /path/to/folder --recipient "Elise Fialkowski" --days 7
    guardian-share h1b /path/to/folder --host https://guardiancompliance.app
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compliance_os.web.services.share_tokens import create_share_token

_TEMPLATES = {"h1b": "h1b_petition"}


def main() -> int:
    p = argparse.ArgumentParser(
        prog="guardian-share",
        description="Issue a read-only share link for a case package.",
    )
    p.add_argument("template", choices=sorted(_TEMPLATES.keys()), help="Case template")
    p.add_argument("folder", help="Absolute path to the case folder")
    p.add_argument("--recipient", default="", help="Recipient name (for audit)")
    p.add_argument("--issuer", default="", help="Issuer name/email (for audit)")
    p.add_argument("--days", type=int, default=14, help="Expiry in days (default 14)")
    p.add_argument(
        "--host",
        default="http://localhost:3000",
        help="Frontend host for the share URL (default localhost:3000)",
    )
    args = p.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"ERROR: folder not found: {folder}", file=sys.stderr)
        return 1

    token = create_share_token(
        folder=str(folder),
        template_id=_TEMPLATES[args.template],
        recipient=args.recipient,
        issuer=args.issuer,
        expires_in_days=args.days,
    )
    url = f"{args.host.rstrip('/')}/share/{token}"
    print(f"Share URL ({args.days} days):")
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
