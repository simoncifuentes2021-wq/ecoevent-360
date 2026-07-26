import os
import hashlib
import subprocess
from pathlib import Path

import psycopg


root = Path(__file__).resolve().parents[2]
baseline_source = "0bcc03b:base_datos/ecoevent_360_schema.sql"
expected_sha256 = "ab254fcdfb290f6f7c1a576cf2d5fcbd3119c535b7aadc993d00074cf12e0001"
database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
baseline = subprocess.check_output(["git", "-C", str(root), "show", baseline_source])
actual_sha256 = hashlib.sha256(baseline).hexdigest()
if actual_sha256 != expected_sha256:
    raise SystemExit(
        f"Baseline checksum mismatch (actual={actual_sha256}, expected={expected_sha256})"
    )
sql = baseline.decode("utf-8")

with psycopg.connect(database_url) as connection:
    with connection.cursor() as cursor:
        cursor.execute(sql)

print(f"PostgreSQL revision 0001 baseline loaded ({baseline_source}, checksum OK)")
