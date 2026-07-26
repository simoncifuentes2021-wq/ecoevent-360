from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.core.config import settings


config = Config("alembic.ini")
script = ScriptDirectory.from_config(config)
expected = set(script.get_heads())
engine = create_engine(settings.database_url)
with engine.connect() as connection:
    current = set(MigrationContext.configure(connection).get_current_heads())

if current != expected:
    raise SystemExit(f"Alembic is not at head (current={sorted(current)}, expected={sorted(expected)})")
print(f"Alembic head verified: {', '.join(sorted(current))}")
