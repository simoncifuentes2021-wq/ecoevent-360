from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.core.config import settings


def validate_single_head(code_heads, database_heads) -> str:
    code = tuple(code_heads)
    database = tuple(database_heads)
    if not code:
        raise SystemExit("Alembic verification failed: code has no head revision")
    if len(code) != 1:
        raise SystemExit(
            f"Alembic verification failed: code must have exactly one head, found {sorted(code)}"
        )
    if not database:
        raise SystemExit("Alembic verification failed: database has no recorded revision")
    if len(database) != 1:
        raise SystemExit(
            "Alembic verification failed: database must have exactly one recorded revision, "
            f"found {sorted(database)}"
        )
    if database[0] != code[0]:
        raise SystemExit(
            "Alembic verification failed: database revision does not match code head "
            f"(database={database[0]}, code={code[0]})"
        )
    return code[0]


def main() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    engine = create_engine(settings.migration_database_url or settings.database_url)
    with engine.connect() as connection:
        database_heads = MigrationContext.configure(connection).get_current_heads()
    head = validate_single_head(script.get_heads(), database_heads)
    print(f"Alembic head verified: {head}")


if __name__ == "__main__":
    main()
