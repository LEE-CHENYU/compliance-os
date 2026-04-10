#!/usr/bin/env python3
"""Seed a local attorney auth account and marketplace attorney profile."""

from __future__ import annotations

import argparse

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import create_engine_and_tables
from compliance_os.web.models.marketplace import AttorneyRow, MarketplaceUserRow
from compliance_os.web.services.auth_service import hash_password

from sqlalchemy.orm import Session, sessionmaker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed an attorney account for local testing.")
    parser.add_argument("--email", default="local-attorney@example.com")
    parser.add_argument("--password", default="secure12345")
    parser.add_argument("--name", default="Casey Counsel")
    parser.add_argument("--bar-state", default="NY")
    parser.add_argument("--bar-number", default="A1234567")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = create_engine_and_tables()
    session_factory = sessionmaker(bind=engine)
    session: Session = session_factory()
    try:
        user = session.query(UserRow).filter(UserRow.email == args.email).first()
        if user is None:
            user = UserRow(
                email=args.email,
                password_hash=hash_password(args.password),
                role="attorney",
            )
            session.add(user)
            session.flush()
        else:
            user.password_hash = hash_password(args.password)
            user.role = "attorney"

        marketplace_user = session.query(MarketplaceUserRow).filter(MarketplaceUserRow.email == args.email).first()
        if marketplace_user is None:
            session.add(
                MarketplaceUserRow(
                    email=args.email,
                    source="direct",
                    role="attorney",
                    full_name=args.name,
                )
            )
        else:
            marketplace_user.role = "attorney"
            marketplace_user.full_name = args.name

        attorney = session.query(AttorneyRow).filter(AttorneyRow.email == args.email).first()
        if attorney is None:
            attorney = AttorneyRow(
                full_name=args.name,
                email=args.email,
                bar_state=args.bar_state,
                bar_number=args.bar_number,
                active=True,
                bar_verified=True,
            )
            session.add(attorney)
        else:
            attorney.full_name = args.name
            attorney.bar_state = args.bar_state
            attorney.bar_number = args.bar_number
            attorney.active = True
            attorney.bar_verified = True

        session.commit()
        print(f"Seeded attorney account: {args.email}")
        print(f"Password: {args.password}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
