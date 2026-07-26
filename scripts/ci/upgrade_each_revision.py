import subprocess
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory


script = ScriptDirectory.from_config(Config("alembic.ini"))
revisions = list(reversed(list(script.walk_revisions(base="20260528_0001", head="heads"))))

for revision in revisions:
    if revision.revision == "20260528_0001":
        continue
    print(f"Applying Alembic revision {revision.revision}", flush=True)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision.revision],
        check=True,
    )
