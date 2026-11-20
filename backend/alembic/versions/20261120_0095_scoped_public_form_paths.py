"""Add event/programming scoped public form routes.

Revision ID: 20261120_0095
Revises: 20261119_0094
"""

from collections import defaultdict
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from app.utils.slug import slugify_url_segment


revision: str = "20261120_0095"
down_revision: str | None = "20261119_0094"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("event_forms", sa.Column("public_path_context_slug", sa.String(220), nullable=True))
    op.add_column("event_forms", sa.Column("public_path_slug", sa.String(220), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            select f.id, f.title, f.public_slug, f.created_at,
                   coalesce(s.name, e.name) as context_name
            from event_forms f
            join events e on e.id = f.event_id
            left join event_sessions s on s.id = f.session_id
            order by f.created_at, f.id
            """
        )
    ).mappings().all()

    grouped: dict[tuple[str, str], list[object]] = defaultdict(list)
    for row in rows:
        context_slug = slugify_url_segment(row["context_name"] or "") or f"event-{row['id']}"
        base_slug = slugify_url_segment(row["title"] or "") or slugify_url_segment(row["public_slug"] or "") or f"form-{row['id']}"
        grouped[(context_slug, base_slug)].append(row)

    reserved = defaultdict(set)
    for context_slug, base_slug in grouped:
        reserved[context_slug].add(base_slug)

    assigned: dict[str, set[str]] = defaultdict(set)
    for (context_slug, base_slug), group in sorted(grouped.items()):
        group.sort(key=lambda row: (row["created_at"], str(row["id"])))
        for index, row in enumerate(group):
            if index == 0:
                route_slug = base_slug
            else:
                ordinal = 2
                while True:
                    candidate = f"{base_slug}-{ordinal}"
                    if candidate not in reserved[context_slug] and candidate not in assigned[context_slug]:
                        route_slug = candidate
                        break
                    ordinal += 1
            assigned[context_slug].add(route_slug)
            connection.execute(
                sa.text(
                    "update event_forms set public_path_context_slug=:context, public_path_slug=:slug where id=:id"
                ),
                {"context": context_slug, "slug": route_slug, "id": row["id"]},
            )

    op.alter_column("event_forms", "public_path_context_slug", nullable=False)
    op.alter_column("event_forms", "public_path_slug", nullable=False)
    op.create_index(
        "uq_event_forms_public_path",
        "event_forms",
        ["public_path_context_slug", "public_path_slug"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_event_forms_public_path", table_name="event_forms")
    op.drop_column("event_forms", "public_path_slug")
    op.drop_column("event_forms", "public_path_context_slug")
