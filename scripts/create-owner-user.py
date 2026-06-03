#!/usr/bin/env python3
"""Idempotently create a Cyclope Central organization owner for headless deployments."""
from __future__ import annotations

import argparse
import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select

from app.core.bootstrap import create_first_owner, setup_required, validate_strong_password
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Create first owner user without printing secrets.")
    parser.add_argument("--organization", required=True, help="Organization display name")
    parser.add_argument("--email", required=True, help="Owner email address")
    parser.add_argument("--password-file", help="Read owner password from file instead of prompt")
    args = parser.parse_args()

    password = Path(args.password_file).read_text().strip() if args.password_file else getpass.getpass("Owner password: ")
    validate_strong_password(password)

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == args.email.lower()))
        if existing is not None:
            print("Owner user already exists; no changes made.")
            return 0
        if setup_required(db):
            user, _refresh = create_first_owner(
                db,
                organization_name=args.organization,
                owner_name=args.email,
                owner_email=args.email,
                owner_password=password,
            )
            db.commit()
            print(f"Created owner user {user.email} for new organization.")
            return 0
        org = db.scalar(select(Organization).order_by(Organization.created_at).limit(1))
        if org is None:
            raise RuntimeError("No organization exists but setup is marked complete")
        user = User(
            organization_id=org.id,
            email=args.email.lower(),
            hashed_password=hash_password(password),
            role="owner",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created owner user {user.email} for existing organization.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
