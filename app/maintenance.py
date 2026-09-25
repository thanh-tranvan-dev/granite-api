"""Preview or apply the 180-day lead retention policy."""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models import Lead


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete expired leads after reviewing the preview")
    args = parser.parse_args()
    cutoff = datetime.now(timezone.utc) - timedelta(days=180)
    with SessionLocal() as session:
        count = session.scalar(select(func.count()).select_from(Lead).where(Lead.created_at < cutoff))
        if args.apply:
            session.execute(delete(Lead).where(Lead.created_at < cutoff))
            session.commit()
            print(f"Deleted {count} leads older than 180 days.")
        else:
            print(f"Would delete {count} leads older than 180 days. Re-run with --apply to proceed.")


if __name__ == "__main__":
    main()
