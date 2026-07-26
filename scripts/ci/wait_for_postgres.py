import os
import time

import psycopg


database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
deadline = time.monotonic() + 60
last_error: Exception | None = None

while time.monotonic() < deadline:
    try:
        with psycopg.connect(database_url, connect_timeout=3) as connection:
            connection.execute("select 1")
        print("PostgreSQL health check: OK")
        raise SystemExit(0)
    except psycopg.Error as error:
        last_error = error
        time.sleep(2)

raise SystemExit(f"PostgreSQL did not become healthy within 60 seconds: {last_error}")
