#!/usr/bin/env python3
"""Create a hashed enrollment token for local development.

Prints the plaintext token once. The database stores only its hash.
"""
from __future__ import annotations

import argparse

from app.core.enrollment import build_enrollment_token
from app.db.session import SessionLocal
from app.models.organization import Organization


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Cyclope Central enrollment token")
    parser.add_argument("--organization", default="default", help="Organization slug")
    parser.add_argument("--name", default="Default Organization", help="Organization display name")
    parser.add_argument("--ttl-hours", type=int, default=24)
    parser.add_argument("--max-uses", type=int, default=1)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.slug == args.organization).one_or_none()
        if org is None:
            org = Organization(name=args.name, slug=args.organization)
            db.add(org)
            db.flush()
        plaintext, token = build_enrollment_token(org.id, ttl_hours=args.ttl_hours, max_uses=args.max_uses)
        db.add(token)
        db.commit()
        print(plaintext)
    finally:
        db.close()


if __name__ == "__main__":
    main()
