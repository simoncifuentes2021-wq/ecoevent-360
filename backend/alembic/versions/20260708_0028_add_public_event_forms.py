"""add public event forms

Revision ID: 20260708_0028
Revises: 20260708_0027
Create Date: 2026-07-08 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260708_0028"
down_revision = "20260708_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (select 1 from pg_type where typname = 'event_form_type') then
                create type event_form_type as enum ('TRANSPORT_SURVEY', 'BIKE_ZONE_REGISTRATION', 'EXPERIENCE_SURVEY', 'CUSTOM');
            end if;
            if not exists (select 1 from pg_type where typname = 'event_form_status') then
                create type event_form_status as enum ('DRAFT', 'ACTIVE', 'CLOSED', 'ARCHIVED');
            end if;
            if not exists (select 1 from pg_type where typname = 'form_field_type') then
                create type form_field_type as enum (
                    'TEXT', 'EMAIL', 'PHONE', 'NUMBER', 'TEXTAREA', 'SELECT', 'MULTI_SELECT', 'RADIO',
                    'CHECKBOX', 'DATE', 'RATING_1_5', 'RATING_1_7', 'YES_NO', 'FILE'
                );
            end if;
            if not exists (select 1 from pg_type where typname = 'bike_zone_status') then
                create type bike_zone_status as enum ('REGISTERED', 'CHECKED_IN', 'CHECKED_OUT');
            end if;
        end $$;
        """
    )
    form_type = postgresql.ENUM(name="event_form_type", create_type=False)
    form_status = postgresql.ENUM(name="event_form_status", create_type=False)
    field_type = postgresql.ENUM(name="form_field_type", create_type=False)
    bike_status = postgresql.ENUM(name="bike_zone_status", create_type=False)

    op.create_table(
        "event_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("venue_name", sa.String(180), nullable=True),
        sa.Column("stage_name", sa.String(180), nullable=True),
        sa.Column("expected_attendees", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("real_attendees", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), server_default=sa.text("'PLANNED'"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_event_sessions_event_id", "event_sessions", ["event_id"])
    op.create_index("idx_event_sessions_status", "event_sessions", ["status"])

    op.create_table(
        "event_forms",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("form_type", form_type, nullable=False),
        sa.Column("public_slug", sa.String(220), nullable=False),
        sa.Column("status", form_status, server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("banner_url", sa.Text(), nullable=True),
        sa.Column("primary_logo_url", sa.Text(), nullable=True),
        sa.Column("secondary_logo_url", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.String(20), server_default=sa.text("'#16b86a'"), nullable=False),
        sa.Column("show_event_name", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("show_session_name", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("collect_personal_data", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("default_language", sa.String(10), server_default=sa.text("'es'"), nullable=False),
        sa.Column("available_languages", postgresql.JSONB(), server_default=sa.text("'[\"es\"]'::jsonb"), nullable=False),
        sa.Column("requires_language_selection", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("opens_at", sa.DateTime(), nullable=True),
        sa.Column("closes_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_slug", name="uq_event_forms_public_slug"),
    )
    op.create_index("idx_event_forms_event_id", "event_forms", ["event_id"])
    op.create_index("idx_event_forms_session_id", "event_forms", ["session_id"])
    op.create_index("idx_event_forms_status", "event_forms", ["status"])

    op.create_table(
        "form_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("form_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(220), nullable=False),
        sa.Column("field_key", sa.String(120), nullable=False),
        sa.Column("field_type", field_type, nullable=False),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("placeholder", sa.String(220), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("min_value", sa.Numeric(), nullable=True),
        sa.Column("max_value", sa.Numeric(), nullable=True),
        sa.Column("max_length", sa.Integer(), nullable=True),
        sa.Column("analytics_key", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("form_id", "field_key", name="uq_form_fields_form_key"),
    )
    op.create_index("idx_form_fields_form_id", "form_fields", ["form_id"])

    op.create_table(
        "form_field_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("field_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("form_fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("value", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_id", "value", name="uq_form_field_options_field_value"),
    )
    op.create_index("idx_form_field_options_field_id", "form_field_options", ["field_id"])

    op.create_table(
        "form_field_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("field_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("form_fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("label", sa.String(220), nullable=False),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("placeholder", sa.String(220), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_id", "language", name="uq_form_field_translations_field_language"),
    )

    op.create_table(
        "form_field_option_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("option_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("form_field_options.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("option_id", "language", name="uq_form_field_option_translations_option_language"),
    )

    op.create_table(
        "form_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("form_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("response_code", sa.String(100), nullable=True),
        sa.Column("respondent_name", sa.String(180), nullable=True),
        sa.Column("respondent_email", sa.String(180), nullable=True),
        sa.Column("respondent_phone", sa.String(60), nullable=True),
        sa.Column("language", sa.String(10), server_default=sa.text("'es'"), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_code", name="uq_form_responses_response_code"),
    )
    op.create_index("idx_form_responses_form_id", "form_responses", ["form_id"])
    op.create_index("idx_form_responses_event_id", "form_responses", ["event_id"])
    op.create_index("idx_form_responses_session_id", "form_responses", ["session_id"])

    op.create_table(
        "form_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("response_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("form_responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("form_fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_number", sa.Numeric(), nullable=True),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("value_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_form_answers_response_id", "form_answers", ["response_id"])
    op.create_index("idx_form_answers_field_id", "form_answers", ["field_id"])

    op.create_table(
        "bike_zone_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("response_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("form_responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("status", bike_status, server_default=sa.text("'REGISTERED'"), nullable=False),
        sa.Column("check_in_at", sa.DateTime(), nullable=True),
        sa.Column("check_out_at", sa.DateTime(), nullable=True),
        sa.Column("checked_in_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("checked_out_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_bike_zone_records_code"),
    )
    op.create_index("idx_bike_zone_records_event_id", "bike_zone_records", ["event_id"])
    op.create_index("idx_bike_zone_records_session_id", "bike_zone_records", ["session_id"])

    for table in (
        "event_sessions",
        "event_forms",
        "form_fields",
        "form_field_options",
        "form_field_translations",
        "form_field_option_translations",
        "form_responses",
        "form_answers",
        "bike_zone_records",
    ):
        op.execute(f"alter table {table} enable row level security")

    op.execute("create policy event_sessions_rls on event_sessions for all using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))")
    op.execute("create policy event_forms_rls on event_forms for all using (app_can_view_event(event_id) or status = 'ACTIVE') with check (app_can_view_event(event_id))")
    op.execute(
        """
        create policy form_fields_rls on form_fields for all
        using (exists (select 1 from event_forms f where f.id = form_id and (app_can_view_event(f.event_id) or f.status = 'ACTIVE')))
        with check (exists (select 1 from event_forms f where f.id = form_id and app_can_view_event(f.event_id)))
        """
    )
    op.execute(
        """
        create policy form_field_options_rls on form_field_options for all
        using (exists (
            select 1 from form_fields ff join event_forms f on f.id = ff.form_id
            where ff.id = field_id and (app_can_view_event(f.event_id) or f.status = 'ACTIVE')
        ))
        with check (exists (
            select 1 from form_fields ff join event_forms f on f.id = ff.form_id
            where ff.id = field_id and app_can_view_event(f.event_id)
        ))
        """
    )
    op.execute(
        """
        create policy form_field_translations_rls on form_field_translations for all
        using (exists (
            select 1 from form_fields ff join event_forms f on f.id = ff.form_id
            where ff.id = field_id and (app_can_view_event(f.event_id) or f.status = 'ACTIVE')
        ))
        with check (exists (
            select 1 from form_fields ff join event_forms f on f.id = ff.form_id
            where ff.id = field_id and app_can_view_event(f.event_id)
        ))
        """
    )
    op.execute(
        """
        create policy form_field_option_translations_rls on form_field_option_translations for all
        using (exists (
            select 1 from form_field_options fo
            join form_fields ff on ff.id = fo.field_id
            join event_forms f on f.id = ff.form_id
            where fo.id = option_id and (app_can_view_event(f.event_id) or f.status = 'ACTIVE')
        ))
        with check (exists (
            select 1 from form_field_options fo
            join form_fields ff on ff.id = fo.field_id
            join event_forms f on f.id = ff.form_id
            where fo.id = option_id and app_can_view_event(f.event_id)
        ))
        """
    )
    op.execute("create policy form_responses_rls on form_responses for all using (app_can_view_event(event_id)) with check (app_can_view_event(event_id) or exists (select 1 from event_forms f where f.id = form_id and f.status = 'ACTIVE'))")
    op.execute(
        """
        create policy form_answers_rls on form_answers for all
        using (exists (select 1 from form_responses r where r.id = response_id and app_can_view_event(r.event_id)))
        with check (exists (
            select 1 from form_responses r join event_forms f on f.id = r.form_id
            where r.id = response_id and (app_can_view_event(r.event_id) or f.status = 'ACTIVE')
        ))
        """
    )
    op.execute("create policy bike_zone_records_rls on bike_zone_records for all using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))")


def downgrade() -> None:
    for table in (
        "bike_zone_records",
        "form_answers",
        "form_responses",
        "form_field_option_translations",
        "form_field_translations",
        "form_field_options",
        "form_fields",
        "event_forms",
        "event_sessions",
    ):
        op.execute(f"drop policy if exists {table}_rls on {table}")
        op.drop_table(table)
    op.execute("drop type if exists bike_zone_status")
    op.execute("drop type if exists form_field_type")
    op.execute("drop type if exists event_form_status")
    op.execute("drop type if exists event_form_type")
