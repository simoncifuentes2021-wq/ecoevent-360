import os
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models.core import Client, Event, EventStaff, User
from app.models.enums import (
    EventStatus, LogbookAssignmentMode, LogbookInstanceStatus,
    LogbookOperationalStage, LogbookRecurrenceEndMode,
    LogbookRecurrenceExceptionType, LogbookRecurrenceFrequency,
    LogbookRecurrenceStatus, LogbookTemplateStatus, LogbookVersionStatus, UserRole,
)
from app.models.logbook import (
    LogbookInstance, LogbookRecurrenceException, LogbookRecurrenceParticipant,
    LogbookRecurrenceSeries, LogbookTemplate, LogbookTemplateVersion,
)


@pytest.fixture()
def rls_context():
    runtime_url = os.environ.get("RLS_DATABASE_URL")
    if not runtime_url:
        pytest.fail("RLS_DATABASE_URL is required for direct RLS certification")
    owner_engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    runtime_engine = create_engine(runtime_url)
    ids = {}
    with Session(owner_engine, expire_on_commit=False) as db:
        suffix = uuid4().hex[:8]
        client1 = Client(business_name=f"RLS client 1 {suffix}", contact_email=f"c1-{suffix}@example.com")
        client2 = Client(business_name=f"RLS client 2 {suffix}", contact_email=f"c2-{suffix}@example.com")
        db.add_all([client1, client2])
        db.flush()
        roles = {
            "admin": UserRole.ADMIN,
            "supervisor": UserRole.SUPERVISOR,
            "other_supervisor": UserRole.SUPERVISOR,
            "worker": UserRole.WORKER,
            "worker2": UserRole.WORKER,
            "outsider": UserRole.WORKER,
            "logistics": UserRole.LOGISTICS_OPERATOR,
            "client": UserRole.CLIENT,
            "other_client": UserRole.CLIENT,
            "unrelated": UserRole.WORKER,
        }
        users = {}
        for name, role in roles.items():
            users[name] = User(
                full_name=f"RLS {name}", email=f"{name}-{suffix}@example.com",
                password_hash="x", role=role,
                client_id=client1.id if name == "client" else client2.id if name == "other_client" else None,
            )
        db.add_all(users.values())
        db.flush()
        now = datetime.now(UTC)
        event1 = Event(client_id=client1.id, name=f"RLS event 1 {suffix}", start_date=now, end_date=now + timedelta(days=30), status=EventStatus.PLANNING, created_by=users["admin"].id)
        event2 = Event(client_id=client2.id, name=f"RLS event 2 {suffix}", start_date=now, end_date=now + timedelta(days=30), status=EventStatus.PLANNING, created_by=users["admin"].id)
        db.add_all([event1, event2])
        db.flush()
        db.add_all([
            EventStaff(event_id=event1.id, user_id=users[name].id)
            for name in ("supervisor", "worker", "worker2", "logistics")
        ] + [EventStaff(event_id=event2.id, user_id=users["other_supervisor"].id)])
        template = LogbookTemplate(
            name=f"RLS template {suffix}", operational_stage=LogbookOperationalStage.OPERATION,
            status=LogbookTemplateStatus.ACTIVE,
            default_assignment_mode=LogbookAssignmentMode.INDIVIDUAL,
            created_by=users["admin"].id,
        )
        db.add(template)
        db.flush()
        version = LogbookTemplateVersion(
            template_id=template.id, version_number=1, status=LogbookVersionStatus.PUBLISHED,
            created_by=users["admin"].id, published_by=users["admin"].id,
        )
        db.add(version)
        db.flush()

        def new_series(event, name):
            item = LogbookRecurrenceSeries(
                event_id=event.id, template_id=template.id, template_version_id=version.id,
                name=name, operational_stage=LogbookOperationalStage.OPERATION,
                assignment_mode=LogbookAssignmentMode.INDIVIDUAL,
                frequency=LogbookRecurrenceFrequency.DAILY, interval=1,
                start_date=now.date(), end_mode=LogbookRecurrenceEndMode.COUNT,
                max_occurrences=2, opens_at_local=time(9), due_at_local=time(18),
                timezone="America/Santiago", status=LogbookRecurrenceStatus.ACTIVE,
                created_by=users["admin"].id,
            )
            db.add(item)
            db.flush()
            return item

        series1 = new_series(event1, "RLS series event 1")
        series2 = new_series(event2, "RLS series event 2")
        empty_series = new_series(event1, "RLS empty target")
        db.add(LogbookRecurrenceParticipant(series_id=series1.id, event_id=event1.id, user_id=users["worker"].id))
        db.add(LogbookRecurrenceException(series_id=series1.id, original_date=now.date(), exception_type=LogbookRecurrenceExceptionType.SKIPPED, created_by=users["admin"].id))
        recurring = LogbookInstance(
            event_id=event1.id, template_id=template.id, template_version_id=version.id,
            name="RLS recurring instance", operational_stage=LogbookOperationalStage.OPERATION,
            assignment_mode=LogbookAssignmentMode.INDIVIDUAL, status=LogbookInstanceStatus.SCHEDULED,
            client_visibility=True, recurrence_series_id=series1.id, occurrence_date=now.date(),
        )
        ordinary = LogbookInstance(
            event_id=event1.id, template_id=template.id, template_version_id=version.id,
            name="RLS ordinary instance", operational_stage=LogbookOperationalStage.OPERATION,
            assignment_mode=LogbookAssignmentMode.INDIVIDUAL, status=LogbookInstanceStatus.OPEN,
            client_visibility=True,
        )
        db.add_all([recurring, ordinary])
        db.commit()
        ids = {
            "clients": [client1.id, client2.id], "events": [event1.id, event2.id],
            "users": users, "event1": event1.id, "event2": event2.id,
            "template": template.id, "version": version.id,
            "series1": series1.id, "series2": series2.id, "empty_series": empty_series.id,
            "recurring": recurring.id, "ordinary": ordinary.id,
        }
    with owner_engine.begin() as connection:
        for table_name in (
            "logbook_recurrence_series", "logbook_recurrence_participants",
            "logbook_recurrence_exceptions", "logbook_instances",
        ):
            connection.execute(text(f"alter table {table_name} force row level security"))
    try:
        yield ids, runtime_engine
    finally:
        runtime_engine.dispose()
        with owner_engine.begin() as connection:
            for table_name in (
                "logbook_recurrence_series", "logbook_recurrence_participants",
                "logbook_recurrence_exceptions", "logbook_instances",
            ):
                connection.execute(text(f"alter table {table_name} no force row level security"))
        with Session(owner_engine) as db:
            db.execute(delete(LogbookInstance).where(LogbookInstance.event_id.in_(ids["events"])))
            db.execute(delete(LogbookRecurrenceException).where(LogbookRecurrenceException.series_id.in_([ids["series1"], ids["series2"], ids["empty_series"]])))
            db.execute(delete(LogbookRecurrenceParticipant).where(LogbookRecurrenceParticipant.series_id.in_([ids["series1"], ids["series2"], ids["empty_series"]])))
            db.execute(delete(LogbookRecurrenceSeries).where(LogbookRecurrenceSeries.id.in_([ids["series1"], ids["series2"], ids["empty_series"]])))
            db.execute(delete(LogbookTemplateVersion).where(LogbookTemplateVersion.id == ids["version"]))
            db.execute(delete(LogbookTemplate).where(LogbookTemplate.id == ids["template"]))
            db.execute(delete(EventStaff).where(EventStaff.event_id.in_(ids["events"])))
            db.execute(delete(Event).where(Event.id.in_(ids["events"])))
            db.execute(delete(User).where(User.id.in_([user.id for user in ids["users"].values()])))
            db.execute(delete(Client).where(Client.id.in_(ids["clients"])))
            db.commit()
        owner_engine.dispose()


def _run(engine, user, statement, params=None):
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(text("select set_config('app.current_user_id', :v, true)"), {"v": str(user.id)})
        connection.execute(text("select set_config('app.current_role', :v, true)"), {"v": user.role.value})
        connection.execute(text("select set_config('app.current_client_id', :v, true)"), {"v": str(user.client_id or "")})
        try:
            result = connection.execute(text(statement), params or {})
            rows = result.fetchall() if result.returns_rows else []
            effective = True if result.returns_rows else result.rowcount > 0
            transaction.rollback()
            return effective, rows, None
        except DBAPIError as exc:
            transaction.rollback()
            return False, [], exc


def _series_insert(ids):
    return """insert into logbook_recurrence_series(
      id,event_id,template_id,template_version_id,name,operational_stage,assignment_mode,
      frequency,interval,start_date,end_mode,max_occurrences,opens_at_local,due_at_local,timezone,status
    ) values (:id,:event,:template,:version,'RLS inserted','OPERATION','INDIVIDUAL',
      'DAILY',1,current_date,'COUNT',1,'09:00','18:00','America/Santiago','ACTIVE')""", {
        "id": uuid4(), "event": ids["event1"], "template": ids["template"], "version": ids["version"]
    }


@pytest.mark.parametrize("role_name,may_manage", [
    ("admin", True), ("supervisor", True), ("other_supervisor", False),
    ("worker", False), ("outsider", False), ("logistics", False),
    ("client", False), ("other_client", False), ("unrelated", False),
])
def test_rls_series_select_insert_update_delete(rls_context, role_name, may_manage):
    ids, engine = rls_context
    user = ids["users"][role_name]
    selected, rows, _ = _run(engine, user, "select id from logbook_recurrence_series where id=:id", {"id": ids["series1"]})
    assert selected and bool(rows) is may_manage
    sql, params = _series_insert(ids)
    inserted, _, _ = _run(engine, user, sql, params)
    updated, _, _ = _run(engine, user, "update logbook_recurrence_series set name=name where id=:id", {"id": ids["empty_series"]})
    deleted, _, _ = _run(engine, user, "delete from logbook_recurrence_series where id=:id", {"id": ids["empty_series"]})
    assert (inserted, updated, deleted) == (may_manage, may_manage, may_manage)


@pytest.mark.parametrize("table", ["logbook_recurrence_participants", "logbook_recurrence_exceptions"])
@pytest.mark.parametrize("role_name,may_manage", [
    ("admin", True), ("supervisor", True), ("other_supervisor", False),
    ("worker", False), ("outsider", False), ("logistics", False),
    ("client", False), ("other_client", False), ("unrelated", False),
])
def test_rls_children_select_insert_update_delete(rls_context, table, role_name, may_manage):
    ids, engine = rls_context
    user = ids["users"][role_name]
    selected, rows, _ = _run(engine, user, f"select id from {table} where series_id=:id", {"id": ids["series1"]})
    assert selected and bool(rows) is may_manage
    if table.endswith("participants"):
        insert_sql = "insert into logbook_recurrence_participants(id,series_id,event_id,user_id) values (:new,:series,:event,:user)"
        params = {"new": uuid4(), "series": ids["empty_series"], "event": ids["event1"], "user": ids["users"]["worker2"].id}
        update_sql = "update logbook_recurrence_participants set user_id=:worker2 where series_id=:series"
        update_params = {"worker2": ids["users"]["worker2"].id, "series": ids["series1"]}
    else:
        insert_sql = "insert into logbook_recurrence_exceptions(id,series_id,original_date,exception_type) values (:new,:series,current_date + 1,'SKIPPED')"
        params = {"new": uuid4(), "series": ids["empty_series"]}
        update_sql = "update logbook_recurrence_exceptions set reason='RLS test' where series_id=:series"
        update_params = {"series": ids["series1"]}
    inserted, _, _ = _run(engine, user, insert_sql, params)
    updated, _, _ = _run(engine, user, update_sql, update_params)
    deleted, _, _ = _run(engine, user, f"delete from {table} where series_id=:series", {"series": ids["series1"]})
    assert (inserted, updated, deleted) == (may_manage, may_manage, may_manage)


def test_rls_blocks_cross_event_ids_and_preserves_instance_visibility(rls_context):
    ids, engine = rls_context
    admin = ids["users"]["admin"]
    linked, _, link_error = _run(
        engine, admin,
        "insert into logbook_recurrence_participants(id,series_id,event_id,user_id) values (:new,:series,:event,:user)",
        {"new": uuid4(), "series": ids["series1"], "event": ids["event1"], "user": ids["users"]["other_supervisor"].id},
    )
    assert not linked and "fk_logbook_recurrence_participant_event_staff" in str(link_error)
    relinked, _, relink_error = _run(
        engine, admin,
        "update logbook_instances set recurrence_series_id=:series where id=:instance",
        {"series": ids["series2"], "instance": ids["ordinary"]},
    )
    assert not relinked and "fk_logbook_instance_recurrence_event" in str(relink_error)

    expectations = {
        "admin": True, "supervisor": True, "other_supervisor": False,
        "worker": True, "outsider": False, "logistics": True,
        "client": True, "other_client": False, "unrelated": False,
    }
    for role_name, visible in expectations.items():
        ok, rows, _ = _run(engine, ids["users"][role_name], "select id,recurrence_series_id from logbook_instances where id in (:ordinary,:recurring)", {"ordinary": ids["ordinary"], "recurring": ids["recurring"]})
        assert ok and (len(rows) == 2) is visible


def test_rls_runtime_role_is_non_owner_without_bypassrls(rls_context):
    _, engine = rls_context
    with engine.connect() as connection:
        row = connection.execute(text("""
          select r.rolsuper, r.rolbypassrls,
                 r.oid = c.relowner as owns_series, c.relforcerowsecurity
          from pg_roles r cross join pg_class c
          where r.rolname=current_user and c.relname='logbook_recurrence_series'
        """)).one()
    assert row == (False, False, False, True)
