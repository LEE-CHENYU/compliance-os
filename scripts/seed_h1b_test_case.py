"""Seed a fresh H-1B test case for engagement-panel UX testing.

Creates a clean state for an existing test user:
  1. New CaseRow (workflow_type=immigration, status=discovery)
  2. Paid + claimed ProfessionalSearchRequest with 5-firm shortlist
  3. NO engagements — so the dashboard's MyEngagements panel stays
     hidden until the user clicks "Track" on a firm. That's the
     specific transition we want to test.

Idempotent on the case side: each run creates a NEW CaseRow + new
search; existing data is left alone. Print case_id + the paid-results
URL at the end so the tester can navigate straight there.

Usage (local dev DB):
    conda run -n compliance-os python scripts/seed_h1b_test_case.py

Usage (prod, via fly ssh):
    fly ssh console -a guardian-compliance -C \\
        "python /app/scripts/seed_h1b_test_case.py --email fretin13@gmail.com"
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables import (
    CaseRow,
    ProfessionalSearchRequestRow,
)


CASE_BRIEF = """H-1B beneficiary case for FY2027 lottery cycle. Beneficiary is a research
data scientist on STEM OPT (graduated MS Computer Science from a US university),
currently employed by an early-stage AI research company in Menlo Park, CA.
Petitioner is a Delaware C-Corp incorporated January 2026, ~12 employees,
$8M seed round closed February 2026. Looking for an immigration attorney with
strong startup-employer experience, comfort with H-1B specialty-occupation
RFEs in technical roles, and demonstrated track record on cap-subject filings
for early-stage companies. Prefer west coast (CA / WA) but will engage
remote-first firms with US-licensed counsel. Beneficiary speaks Mandarin and
English; bilingual counsel a plus but not required."""


# Realistic immigration-firm shortlist for testing. All names are firms that
# are widely recognized in the H-1B space (publicly listed in AILA, USCIS
# notices, etc.) — included as test fixture data with `_demo: True` so it's
# clearly synthetic, never claiming to be a real verified search result.
DEMO_FIRMS = [
    {
        "name": "Klasko Immigration Law Partners",
        "city": "Philadelphia",
        "state": "PA",
        "website": "https://klaskolaw.com",
        "phone": "+1-215-825-8600",
        "lead_attorney": "H. Ronald Klasko",
        "emails": ["info@klaskolaw.com"],
        "confidence": 92,
        "_personas": ["startup_h1b", "elite_boutique"],
        "_why_fits": [
            "Recognized authority on EB-5 + employment-based immigration; written practice guides used by other AILA attorneys.",
            "Active practice on H-1B specialty-occupation RFEs in tech roles.",
        ],
        "_credentials": [
            "AILA past national president",
            "Chambers USA Band 1 — Immigration",
        ],
        "_sources": ["https://klaskolaw.com/attorneys/h-ronald-klasko/"],
        "_demo": True,
    },
    {
        "name": "Fragomen, Del Rey, Bernsen & Loewy",
        "city": "New York",
        "state": "NY",
        "website": "https://www.fragomen.com",
        "phone": "+1-212-688-8555",
        "lead_attorney": "Austin T. Fragomen Jr.",
        "emails": ["info@fragomen.com"],
        "confidence": 88,
        "_personas": ["startup_h1b", "enterprise_h1b"],
        "_why_fits": [
            "World's largest immigration-only law firm; deep H-1B cap-filing capacity.",
            "Strong startup-side practice through fragomen.com/early-stage.",
        ],
        "_credentials": [
            "Chambers Global Band 1 — Immigration",
            "AILA-recognized leadership across multiple offices",
        ],
        "_sources": ["https://www.fragomen.com/about/"],
        "_demo": True,
    },
    {
        "name": "Ogletree Deakins (Immigration)",
        "city": "San Francisco",
        "state": "CA",
        "website": "https://ogletree.com/practices/immigration",
        "phone": "+1-415-442-4810",
        "lead_attorney": "Mary Pivec",
        "emails": ["info@ogletree.com"],
        "confidence": 81,
        "_personas": ["enterprise_h1b", "west_coast"],
        "_why_fits": [
            "Full-service immigration group with embedded employment-law counsel.",
            "Active SF office; experienced with venture-backed petitioners.",
        ],
        "_credentials": [
            "AmLaw 100",
            "Chambers USA — Immigration (multi-state)",
        ],
        "_sources": ["https://ogletree.com/practices/immigration/"],
        "_demo": True,
    },
    {
        "name": "Berry Appleman & Leiden (BAL)",
        "city": "Dallas",
        "state": "TX",
        "website": "https://www.bal.com",
        "phone": "+1-214-432-1100",
        "lead_attorney": "Frieda Garcia",
        "emails": ["info@bal.com"],
        "confidence": 78,
        "_personas": ["enterprise_h1b"],
        "_why_fits": [
            "Tech-heavy book of business with deep H-1B cap-filing pipeline.",
            "Cogent technology platform for case-status tracking.",
        ],
        "_credentials": [
            "AILA-recognized national practice",
            "Chambers Global — Immigration",
        ],
        "_sources": ["https://www.bal.com/about/"],
        "_demo": True,
    },
    {
        "name": "Foster LLP",
        "city": "Houston",
        "state": "TX",
        "website": "https://www.fosterglobal.com",
        "phone": "+1-713-625-9200",
        "lead_attorney": "Charles C. Foster",
        "emails": ["info@fosterglobal.com"],
        "confidence": 74,
        "_personas": ["startup_h1b"],
        "_why_fits": [
            "Boutique immigration firm with strong cap-subject H-1B practice.",
            "Multilingual capability including Mandarin support.",
        ],
        "_credentials": [
            "AILA past national president (Charles Foster)",
            "Chambers USA — Immigration",
        ],
        "_sources": ["https://www.fosterglobal.com/professionals.html"],
        "_demo": True,
    },
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--email", default="fretin13@gmail.com",
                   help="Email of the test user to seed under (must already exist).")
    args = p.parse_args()

    db = next(get_session())
    try:
        user = db.query(UserRow).filter(UserRow.email == args.email).first()
        if user is None:
            print(f"ERROR: no user with email {args.email}", file=sys.stderr)
            return 1

        case = CaseRow(
            user_id=user.id,
            workflow_type="immigration",
            status="discovery",
        )
        db.add(case)
        db.flush()

        now = datetime.utcnow()
        search = ProfessionalSearchRequestRow(
            case_id=case.id,
            user_id=user.id,
            case_brief=CASE_BRIEF,
            purpose="H-1B FY2027 — startup petitioner",
            vertical="immigration_attorney",
            status="complete",
            firms_data=DEMO_FIRMS,
            paid_at=now,
            stripe_customer_email=args.email,
            stripe_session_id=f"cs_demo_{case.id[:8]}",
            completed_at=now,
        )
        db.add(search)
        db.commit()

        # Production deploy URL. Local dev would use http://localhost:3000.
        base = "https://guardiancompliance.app"
        print(f"\nSeeded H-1B test case for {args.email}")
        print(f"  case_id   = {case.id}")
        print(f"  search_id = {search.id}")
        print(f"  firms     = {len(DEMO_FIRMS)}")
        print(f"\nLinks (start with the report — that's where the actionable")
        print(f"      content lives, including the Track buttons that")
        print(f"      populate the case + engagement panel):")
        print(f"  → Paid report : {base}/find-lawyer/{search.id}/paid")
        print(f"  Case view     : {base}/case/{case.id}  (becomes useful once you Track)")
        print(f"  Dashboard     : {base}/dashboard")
        print(f"\nNo engagements seeded — click 'Track' on any firm to test the panel.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
