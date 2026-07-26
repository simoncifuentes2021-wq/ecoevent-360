import json
import logging

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.logbook_lifecycle_service import process_logbook_lifecycle


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        try:
            # The independent process has no authenticated request to seed the
            # existing PostgreSQL RLS context. It receives the same trusted
            # database configuration as the backend, never a user-supplied role.
            db.execute(text("select set_config('app.current_role', 'SUPER_ADMIN', false)"))
            db.execute(text("select set_config('app.current_user_id', '', false)"))
            db.execute(text("select set_config('app.current_client_id', '', false)"))
            summary = process_logbook_lifecycle(db)
            print(json.dumps(summary.model_dump(), default=str))
            return 1 if summary.failed_count else 0
        except Exception:
            logging.getLogger(__name__).exception("Logbook lifecycle processing failed")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
