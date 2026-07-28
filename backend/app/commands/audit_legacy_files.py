"""Inventory legacy file references without downloading, deleting, or logging URLs."""
import argparse
import hashlib

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.core import Evidence, LogisticsEvidence, OrderEvidence, SurveyImport
from app.core.config import settings
from app.services.file_storage_service import legacy_reference_to_key, stored_file_exists


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Convert unambiguous DB references only")
    parser.add_argument("--check-remote", action="store_true", help="Allow remote object existence checks")
    args = parser.parse_args()
    totals = {"absolute_url": 0, "uploads_path": 0, "private_key": 0, "public_key": 0,
              "invalid": 0, "missing": 0, "convertible": 0, "unchanged": 0}
    with SessionLocal() as db:
        for model in (Evidence, LogisticsEvidence, OrderEvidence, SurveyImport):
            for row in db.scalars(select(model)).all():
                value = row.file_url
                if not value:
                    totals["unchanged"] += 1
                    continue
                if value.startswith(("http://", "https://")):
                    totals["absolute_url"] += 1
                elif value.replace("\\", "/").startswith("uploads/"):
                    totals["uploads_path"] += 1
                elif value.startswith(settings.r2_private_prefix.strip("/") + "/"):
                    totals["private_key"] += 1
                elif value.startswith(settings.r2_public_prefix.strip("/") + "/"):
                    totals["public_key"] += 1
                try:
                    key = legacy_reference_to_key(value)
                except ValueError:
                    totals["invalid"] += 1
                    print(f"manual model={model.__name__} id={row.id} ref_hash={hashlib.sha256(value.encode()).hexdigest()[:12]}")
                    continue
                if (not settings.use_r2_storage or args.check_remote) and not stored_file_exists(value):
                    totals["missing"] += 1
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
