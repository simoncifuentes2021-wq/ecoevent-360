"""Allow scoped public form submissions through RLS.

Revision ID: 20260909_0061
Revises: 20260904_0060
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260909_0061"
down_revision: str | None = "20260904_0060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PUBLIC_RESPONSE_SCOPE = """
    form_id = nullif(current_setting('app.public_form_id', true), '')::uuid
    and (
        id = nullif(current_setting('app.public_response_id', true), '')::uuid
        or (
            coalesce(current_setting('app.public_idempotency_key', true), '') <> ''
            and coalesce(metadata ->> 'idempotency_key', '') =
                current_setting('app.public_idempotency_key', true)
        )
    )
    and exists (
        select 1 from event_forms f
        where f.id = form_id and f.status = 'ACTIVE'
    )
"""

PUBLIC_RESPONSE_INSERT = """
    id = nullif(current_setting('app.public_response_id', true), '')::uuid
    and form_id = nullif(current_setting('app.public_form_id', true), '')::uuid
    and exists (
        select 1 from event_forms f
        where f.id = form_id and f.status = 'ACTIVE'
    )
"""

PUBLIC_CHILD_SCOPE = """
    exists (
        select 1
        from form_responses r
        join event_forms f on f.id = r.form_id
        where r.id = response_id
          and r.id = nullif(current_setting('app.public_response_id', true), '')::uuid
          and r.form_id = nullif(current_setting('app.public_form_id', true), '')::uuid
          and f.status = 'ACTIVE'
    )
"""


def upgrade() -> None:
    op.execute("drop policy if exists form_responses_rls on form_responses")
    op.execute(
        f"create policy form_responses_select on form_responses for select "
        f"using (app_can_view_event(event_id) or ({PUBLIC_RESPONSE_SCOPE}))"
    )
    op.execute(
        f"create policy form_responses_insert on form_responses for insert "
        f"with check (app_can_view_event(event_id) or ({PUBLIC_RESPONSE_INSERT}))"
    )
    op.execute(
        "create policy form_responses_update on form_responses for update "
        "using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))"
    )
    op.execute(
        "create policy form_responses_delete on form_responses for delete "
        "using (app_can_view_event(event_id))"
    )

    op.execute("drop policy if exists form_answers_rls on form_answers")
    authenticated_answer_scope = (
        "exists (select 1 from form_responses r "
        "where r.id = response_id and app_can_view_event(r.event_id))"
    )
    op.execute(
        f"create policy form_answers_select on form_answers for select "
        f"using ({authenticated_answer_scope} or ({PUBLIC_CHILD_SCOPE}))"
    )
    op.execute(
        f"create policy form_answers_insert on form_answers for insert "
        f"with check ({authenticated_answer_scope} or ({PUBLIC_CHILD_SCOPE}))"
    )
    op.execute(
        f"create policy form_answers_update on form_answers for update "
        f"using ({authenticated_answer_scope}) with check ({authenticated_answer_scope})"
    )
    op.execute(
        f"create policy form_answers_delete on form_answers for delete "
        f"using ({authenticated_answer_scope})"
    )

    op.execute("drop policy if exists bike_zone_records_rls on bike_zone_records")
    op.execute(
        f"create policy bike_zone_records_select on bike_zone_records for select "
        f"using (app_can_view_event(event_id) or ({PUBLIC_CHILD_SCOPE}))"
    )
    op.execute(
        f"create policy bike_zone_records_insert on bike_zone_records for insert "
        f"with check (app_can_view_event(event_id) or ({PUBLIC_CHILD_SCOPE}))"
    )
    op.execute(
        "create policy bike_zone_records_update on bike_zone_records for update "
        "using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))"
    )
    op.execute(
        "create policy bike_zone_records_delete on bike_zone_records for delete "
        "using (app_can_view_event(event_id))"
    )


def downgrade() -> None:
    for table, policies in (
        ("form_responses", ("select", "insert", "update", "delete")),
        ("form_answers", ("select", "insert", "update", "delete")),
        ("bike_zone_records", ("select", "insert", "update", "delete")),
    ):
        for policy in policies:
            op.execute(f"drop policy if exists {table}_{policy} on {table}")

    op.execute(
        "create policy form_responses_rls on form_responses for all "
        "using (app_can_view_event(event_id)) "
        "with check (app_can_view_event(event_id) or exists "
        "(select 1 from event_forms f where f.id = form_id and f.status = 'ACTIVE'))"
    )
    op.execute(
        "create policy form_answers_rls on form_answers for all "
        "using (exists (select 1 from form_responses r where r.id = response_id "
        "and app_can_view_event(r.event_id))) "
        "with check (exists (select 1 from form_responses r join event_forms f "
        "on f.id = r.form_id where r.id = response_id and "
        "(app_can_view_event(r.event_id) or f.status = 'ACTIVE')))"
    )
    op.execute(
        "create policy bike_zone_records_rls on bike_zone_records for all "
        "using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))"
    )
