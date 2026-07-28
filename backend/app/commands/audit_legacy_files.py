"""Inventory legacy file references without downloading, deleting, or logging URLs."""
import argparse
import hashlib

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.core import Evidence, LogisticsEvidence, OrderEvidence, SurveyImport
from app.services.file_storage_service import legacy_reference_to_key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Convert unambiguous DB references only")
    args = parser.parse_args()
    totals = {"convertible": 0, "manual": 0, "unchanged": 0}
    with SessionLocal() as db:
        for model in (Evidence, LogisticsEvidence, OrderEvidence, SurveyImport):
            for row in db.scalars(select(model)).all():
                value = row.file_url
                if not value:
                    totals["unchanged"] += 1
                    continue
                try:
                    key = legacy_reference_to_key(value)
                except ValueError:
                    totals["manual"] += 1
                    print(f"manual model={model.__name__} id={row.id} ref_hash={hashlib.sha256(value.encode()).hexdigest()[:12]}")
                    continue
                if key == value:
                    totals["unchanged"] += 1
                else:
                    totals["convertible"] += 1
                    if args.apply:
                        row.file_url = key
        if args.apply:
            db.commit()
        else:
            db.rollback()
    print(f"mode={'apply' if args.apply else 'dry-run'} totals={totals}")


if __name__ == "__main__":
    main()
