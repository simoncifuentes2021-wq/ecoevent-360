# ruff: noqa: F405
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.core.permissions import can_access_event, can_manage_event
from app.core.security import create_access_token, decode_access_token
from app.models.core import Event, EventStaff, EventZone, Incident, Task, User
from app.models.enums import *  # noqa: F403
from app.models.logbook import *  # noqa: F403
from app.schemas.logbook_schema import *  # noqa: F403
from app.services.file_storage_service import read_stored_file, save_bytes_file
from app.services.audit_log_service import create_audit_log

ADMIN = {UserRole.ADMIN, UserRole.SUPER_ADMIN}


def fail(code, detail):
    raise HTTPException(status_code=code, detail=detail)


def audit(
    db, current, action, entity_type, entity_id, *, event_id=None, old=None, new=None, metadata=None
):
    create_audit_log(
        db,
        user=current,
        action=action,
        module="logbooks",
        entity_type=entity_type,
        entity_id=entity_id,
        event_id=event_id,
        old_data=old,
        new_data=new,
        metadata=metadata,
    )


def _template(db, id):
    obj = db.get(LogbookTemplate, id)
    if not obj:
        fail(404, "Logbook template not found")
    return obj


def _version(db, id, load=False):
    q = select(LogbookTemplateVersion).where(LogbookTemplateVersion.id == id)
    if load:
        q = q.options(
            selectinload(LogbookTemplateVersion.sections)
            .selectinload(LogbookSection.items)
            .selectinload(LogbookItem.options)
        )
    obj = db.scalar(q)
    if not obj:
        fail(404, "Logbook version not found")
    return obj


def _build(version, sections):
    for s in sections:
        section = LogbookSection(template_version_id=version.id, **s.model_dump(exclude={"items"}))
        version.sections.append(section)
        for i in s.items:
            item = LogbookItem(**i.model_dump(exclude={"options"}))
            section.items.append(item)
            item.options.extend(LogbookItemOption(**o.model_dump()) for o in i.options)


def create_template(db, p, current):
    if current.role not in ADMIN:
        fail(403, "Insufficient role")
    t = LogbookTemplate(**p.model_dump(exclude={"sections", "change_notes"}), created_by=current.id)
    db.add(t)
    db.flush()
    v = LogbookTemplateVersion(
        template_id=t.id, version_number=1, change_notes=p.change_notes, created_by=current.id
    )
    db.add(v)
    db.flush()
    _build(v, p.sections)
    db.commit()
    db.refresh(t)
    audit(
        db,
        current,
        "LOGBOOK_TEMPLATE_CREATED",
        "LogbookTemplate",
        t.id,
        new={"name": t.name, "status": t.status},
    )
    return t


def list_templates(db, current, page, limit, status_filter=None):
    if current.role not in ADMIN | {UserRole.SUPERVISOR}:
        fail(403, "Insufficient role")
    filters = [LogbookTemplate.status == status_filter] if status_filter else []
    total = (
        db.scalar(select(func.count()).select_from(LogbookTemplate).where(*filters)) or 0
    )
    return list(
        db.scalars(
            select(LogbookTemplate).where(*filters)
            .order_by(LogbookTemplate.updated_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    ), total


def update_template(db, id, p, current):
    if current.role not in ADMIN:
        fail(403, "Insufficient role")
    t = _template(db, id)
    if t.status == LogbookTemplateStatus.ARCHIVED:
        fail(409, "Archived templates cannot be edited")
    v = db.scalar(
        select(LogbookTemplateVersion)
        .where(
            LogbookTemplateVersion.template_id == id,
            LogbookTemplateVersion.status == LogbookVersionStatus.DRAFT,
        )
        .order_by(LogbookTemplateVersion.version_number.desc())
        .options(selectinload(LogbookTemplateVersion.sections))
    )
    if not v:
        fail(409, "Create a new draft version before editing a published template")
    old_visibility = t.default_client_visibility
    old_section_order = [section.id for section in sorted(v.sections, key=lambda item: item.position)]
    data = p.model_dump(exclude_unset=True)
    sections = data.pop("sections", None)
    notes = data.pop("change_notes", None)
    for k, val in data.items():
        setattr(t, k, val)
    if notes is not None:
        v.change_notes = notes
    if sections is not None:
        for s in list(v.sections):
            db.delete(s)
        db.flush()
        _build(v, p.sections or [])
    db.commit()
    db.refresh(t)
    audit(db, current, "LOGBOOK_TEMPLATE_UPDATED", "LogbookTemplate", t.id, new={"name": t.name})
    audit(
        db,
        current,
        "LOGBOOK_VERSION_UPDATED",
        "LogbookTemplateVersion",
        v.id,
        new={"version_number": v.version_number},
    )
    if sections is not None:
        audit(
            db,
            current,
            "LOGBOOK_STRUCTURE_REORDERED",
            "LogbookTemplateVersion",
            v.id,
            old={"section_order": old_section_order},
            new={"section_positions": [section.position for section in p.sections or []]},
        )
    if old_visibility != t.default_client_visibility:
        audit(
            db,
            current,
            "LOGBOOK_CLIENT_VISIBILITY_CHANGED",
            "LogbookTemplate",
            t.id,
            old={"client_visibility": old_visibility},
            new={"client_visibility": t.default_client_visibility},
        )
    return t


def publish(db, id, current):
    if current.role not in ADMIN:
        fail(403, "Insufficient role")
    v = _version(db, id, True)
    if v.template.status == LogbookTemplateStatus.ARCHIVED:
        fail(409, "Archived templates cannot be published")
    if v.status != LogbookVersionStatus.DRAFT:
        fail(409, "Only draft versions can be published")
    if not v.sections or any(not s.items for s in v.sections):
        fail(422, "A published version requires sections and items")
    old_status = v.status
    v.status = LogbookVersionStatus.PUBLISHED
    v.published_by = current.id
    v.published_at = datetime.utcnow()
    v.template.status = LogbookTemplateStatus.ACTIVE
    db.commit()
    db.refresh(v)
    audit(
        db,
        current,
        "LOGBOOK_VERSION_PUBLISHED",
        "LogbookTemplateVersion",
        v.id,
        old={"status": old_status},
        new={"status": v.status, "version_number": v.version_number},
    )
    return v


def new_version(db, template_id, current, source_version_id=None):
    if current.role not in ADMIN:
        fail(403, "Insufficient role")
    template = _template(db, template_id)
    if template.status == LogbookTemplateStatus.ARCHIVED:
        fail(409, "Archived templates cannot create new versions")
    latest = db.scalar(
        select(LogbookTemplateVersion)
        .where(LogbookTemplateVersion.template_id == template_id)
        .order_by(LogbookTemplateVersion.version_number.desc())
        .options(
            selectinload(LogbookTemplateVersion.sections)
            .selectinload(LogbookSection.items)
            .selectinload(LogbookItem.options)
        )
    )
    if not latest:
        fail(404, "Logbook template not found")
    if latest.status == LogbookVersionStatus.DRAFT:
        fail(409, "A draft already exists")
    source = _version(db, source_version_id, True) if source_version_id else latest
    if source.template_id != template_id:
        fail(422, "Source version does not belong to this template")
    v = LogbookTemplateVersion(
        template_id=template_id,
        version_number=latest.version_number + 1,
        created_by=current.id,
        change_notes="Nueva versión",
    )
    db.add(v)
    db.flush()
    sections = []
    for s in source.sections:
        sections.append(
            SectionIn(
                title=s.title,
                description=s.description,
                position=s.position,
                is_required=s.is_required,
                items=[
                    ItemIn(
                        title=i.title,
                        description=i.description,
                        instructions=i.instructions,
                        position=i.position,
                        item_type=i.item_type,
                        is_required=i.is_required,
                        allow_not_applicable=i.allow_not_applicable,
                        evidence_policy=i.evidence_policy,
                        min_evidences=i.min_evidences,
                        max_evidences=i.max_evidences,
                        require_comment_on_failure=i.require_comment_on_failure,
                        requires_supervisor_review=i.requires_supervisor_review,
                        client_visible_by_default=i.client_visible_by_default,
                        creates_incident_suggestion=i.creates_incident_suggestion,
                        options=[
                            OptionIn(
                                label=o.label,
                                value=o.value,
                                position=o.position,
                                is_success_value=o.is_success_value,
                                is_failure_value=o.is_failure_value,
                            )
                            for o in i.options
                        ],
                    )
                    for i in s.items
                ],
            )
        )
    _build(v, sections)
    db.commit()
    db.refresh(v)
    audit(
        db,
        current,
        "LOGBOOK_VERSION_CREATED",
        "LogbookTemplateVersion",
        v.id,
        new={"version_number": v.version_number},
        metadata={"source_version_id": source.id},
    )
    return v


def create_instance(db, event_id, p, current):
    if current.role not in ADMIN | {UserRole.SUPERVISOR} or not can_manage_event(
        current, event_id, db
    ):
        fail(403, "Insufficient role")
    event = db.get(Event, event_id)
    if not event:
        fail(404, "Event not found")
    v = _version(db, p.template_version_id)
    if (
        v.status != LogbookVersionStatus.PUBLISHED
        or v.template.status == LogbookTemplateStatus.ARCHIVED
    ):
        fail(422, "A published version from a non-archived template is required")
    if p.zone_id:
        z = db.get(EventZone, p.zone_id)
        if not z or z.event_id != event_id:
            fail(422, "Zone does not belong to event")
    staff = set(
        db.scalars(
            select(EventStaff.user_id)
            .join(User)
            .where(EventStaff.event_id == event_id, User.is_active.is_(True))
        ).all()
    )
    if not set(p.participant_ids) <= staff:
        fail(422, "All participants must be active event staff")
    if p.supervisor_id:
        supervisor = db.scalar(
            select(User)
            .join(EventStaff, EventStaff.user_id == User.id)
            .where(
                EventStaff.event_id == event_id,
                User.id == p.supervisor_id,
                User.role == UserRole.SUPERVISOR,
                User.is_active.is_(True),
            )
        )
        if not supervisor:
            fail(422, "Supervisor must be an active supervisor assigned to the event")
    inst = LogbookInstance(
        event_id=event_id,
        template_id=v.template_id,
        template_version_id=v.id,
        name=p.name or v.template.name,
        operational_stage=v.template.operational_stage,
        zone_id=p.zone_id,
        assignment_mode=p.assignment_mode,
        opens_at=p.opens_at,
        due_at=p.due_at,
        supervisor_id=p.supervisor_id,
        status=LogbookInstanceStatus.SCHEDULED
        if p.opens_at and p.opens_at > datetime.utcnow()
        else LogbookInstanceStatus.OPEN,
        client_visibility=p.client_visibility,
        created_by=current.id,
    )
    db.add(inst)
    db.flush()
    for uid in p.participant_ids:
        db.add(LogbookAssignment(logbook_instance_id=inst.id, user_id=uid))
    db.commit()
    db.refresh(inst)
    audit(
        db,
        current,
        "LOGBOOK_INSTANCE_CREATED",
        "LogbookInstance",
        inst.id,
        event_id=event_id,
        new={"status": inst.status, "assignment_mode": inst.assignment_mode},
        metadata={
            "participant_count": len(p.participant_ids),
            "client_visibility": p.client_visibility,
        },
    )
    return inst


def my_assignments(db, current, status_filter=None):
    filters = [LogbookAssignment.user_id == current.id]
    if status_filter:
        filters.append(LogbookAssignment.status == status_filter)
    return list(
        db.scalars(
            select(LogbookAssignment)
            .where(*filters)
            .order_by(LogbookAssignment.created_at.desc())
        ).all()
    )


def _assignment(db, id, current, manage=False):
    a = db.get(LogbookAssignment, id)
    if not a:
        fail(404, "Logbook assignment not found")
    allowed = (
        can_manage_event(current, a.instance.event_id, db)
        if manage
        else (a.user_id == current.id or can_manage_event(current, a.instance.event_id, db))
    )
    if not allowed:
        fail(403, "Insufficient role")
    return a


def save_response(db, assignment_id, p, current):
    a = _assignment(db, assignment_id, current)
    if a.user_id != current.id and current.role not in ADMIN:
        fail(403, "Solo el participante asignado puede editar las respuestas")
    if a.status not in {
        LogbookAssignmentStatus.PENDING,
        LogbookAssignmentStatus.IN_PROGRESS,
        LogbookAssignmentStatus.CHANGES_REQUESTED,
    }:
        fail(409, "Submitted assignments are locked")
    item = db.get(LogbookItem, p.item_id)
    if not item or item.section.template_version_id != a.instance.template_version_id:
        fail(422, "Item does not belong to this logbook version")
    if p.is_not_applicable and not item.allow_not_applicable:
        fail(422, "Not applicable is not allowed")
    if (
        item.item_type
        in {LogbookItemType.CHECKBOX, LogbookItemType.CONFIRMATION, LogbookItemType.YES_NO}
        and p.boolean_value is None
        and not p.is_not_applicable
    ):
        fail(422, "Debes marcar una opción de Sí/No o confirmación")
    if item.item_type == LogbookItemType.NUMBER and p.numeric_value is None:
        fail(422, "A numeric value is required")
    opt = None
    if item.item_type == LogbookItemType.STATUS_SELECT:
        opt = db.get(LogbookItemOption, p.selected_option_id) if p.selected_option_id else None
        if not opt or opt.logbook_item_id != item.id:
            fail(422, "Invalid option")
    if p.is_not_applicable:
        p.result_status = LogbookResultStatus.NOT_APPLICABLE
    elif item.item_type in {
        LogbookItemType.CHECKBOX,
        LogbookItemType.CONFIRMATION,
        LogbookItemType.YES_NO,
    }:
        p.result_status = (
            LogbookResultStatus.COMPLETED
            if p.boolean_value
            else LogbookResultStatus.FAILED
        )
    elif opt:
        p.result_status = (
            LogbookResultStatus.FAILED
            if opt.is_failure_value
            else LogbookResultStatus.COMPLETED
        )
    else:
        p.result_status = LogbookResultStatus.COMPLETED
    response_query = select(LogbookResponse).where(LogbookResponse.logbook_item_id == item.id)
    if a.instance.assignment_mode == LogbookAssignmentMode.SHARED:
        response_query = response_query.join(LogbookAssignment).where(
            LogbookAssignment.logbook_instance_id == a.instance.id
        )
    else:
        response_query = response_query.where(LogbookResponse.assignment_id == a.id)
    r = db.scalar(response_query)
    if r and p.version is not None and r.version != p.version:
        fail(409, "Response was modified by another user")
    if not r:
        r = LogbookResponse(
            assignment_id=a.id, logbook_item_id=item.id, result_status=p.result_status
        )
        db.add(r)
    for k, val in p.model_dump(exclude={"item_id", "version"}).items():
        setattr(r, k, val)
    r.completed_by = current.id
    r.completed_at = datetime.utcnow()
    r.version = (r.version or 0) + 1
    if a.status == LogbookAssignmentStatus.PENDING:
        a.status = LogbookAssignmentStatus.IN_PROGRESS
        a.started_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    audit(
        db,
        current,
        "LOGBOOK_RESPONSE_SAVED",
        "LogbookResponse",
        r.id,
        event_id=a.instance.event_id,
        new={"result_status": r.result_status, "version": r.version},
    )
    return r


def submit(db, id, current):
    a = _assignment(db, id, current)
    if a.user_id != current.id:
        fail(403, "Only the participant can submit")
    if a.status not in {
        LogbookAssignmentStatus.IN_PROGRESS,
        LogbookAssignmentStatus.CHANGES_REQUESTED,
    }:
        fail(409, "Assignment cannot be submitted")
    items = list(
        db.scalars(
            select(LogbookItem)
            .join(LogbookSection)
            .where(LogbookSection.template_version_id == a.instance.template_version_id)
        ).all()
    )
    assignment_group = (
        a.instance.assignments
        if a.instance.assignment_mode == LogbookAssignmentMode.SHARED
        else [a]
    )
    responses = {
        response.logbook_item_id: response
        for member in assignment_group
        for response in member.responses
    }
    for item in items:
        r = responses.get(item.id)
        if item.is_required and (not r or r.result_status == LogbookResultStatus.PENDING):
            fail(422, f"Required item missing: {item.title}")
        if (
            r
            and r.result_status == LogbookResultStatus.FAILED
            and item.require_comment_on_failure
            and not r.comment
        ):
            fail(422, f"Failure comment required: {item.title}")
        evidence_count = (
            db.scalar(
                select(func.count(LogbookEvidence.id)).where(
                    LogbookEvidence.response_id == r.id,
                    LogbookEvidence.deleted_at.is_(None),
                )
            )
            if r
            else 0
        ) or 0
        if (
            r
            and (
                item.evidence_policy == LogbookEvidencePolicy.REQUIRED
                or item.evidence_policy == LogbookEvidencePolicy.REQUIRED_ON_FAILURE
                and r.result_status == LogbookResultStatus.FAILED
            )
            and evidence_count < max(1, item.min_evidences)
        ):
            fail(422, f"Evidence required: {item.title}")
    old = a.status
    a.attempt_number += 1
    new_status = (
        LogbookAssignmentStatus.RESUBMITTED
        if old == LogbookAssignmentStatus.CHANGES_REQUESTED
        else LogbookAssignmentStatus.SUBMITTED
    )
    a.status = new_status
    a.submitted_at = datetime.utcnow()
    if a.instance.assignment_mode == LogbookAssignmentMode.SHARED:
        for member in a.instance.assignments:
            member.status = new_status
            member.submitted_at = a.submitted_at
            member.attempt_number = max(member.attempt_number, a.attempt_number)
    db.add(
        LogbookReviewHistory(
            assignment_id=a.id,
            actor_id=current.id,
            action="SUBMIT",
            previous_status=old.value,
            new_status=a.status.value,
            attempt_number=a.attempt_number,
        )
    )
    a.instance.status = LogbookInstanceStatus.UNDER_REVIEW
    db.commit()
    db.refresh(a)
    audit(
        db,
        current,
        "LOGBOOK_RESUBMITTED"
        if a.status == LogbookAssignmentStatus.RESUBMITTED
        else "LOGBOOK_SUBMITTED",
        "LogbookAssignment",
        a.id,
        event_id=a.instance.event_id,
        old={"status": old},
        new={"status": a.status, "attempt_number": a.attempt_number},
    )
    return a


def review(db, id, current, approve, comment):
    a = _assignment(db, id, current, True)
    if a.status not in {LogbookAssignmentStatus.SUBMITTED, LogbookAssignmentStatus.RESUBMITTED}:
        fail(409, "Only submitted assignments can be reviewed")
    if not approve and not comment:
        fail(422, "A comment is required when requesting changes")
    old = a.status
    new_status = (
        LogbookAssignmentStatus.APPROVED if approve else LogbookAssignmentStatus.CHANGES_REQUESTED
    )
    reviewed_at = datetime.utcnow()
    targets = (
        a.instance.assignments
        if a.instance.assignment_mode == LogbookAssignmentMode.SHARED
        else [a]
    )
    for member in targets:
        member.status = new_status
        member.review_comment = comment
        if approve:
            member.approved_at = reviewed_at
            member.approved_by = current.id
            member.changes_requested_at = None
            member.changes_requested_by = None
        else:
            member.changes_requested_at = reviewed_at
            member.changes_requested_by = current.id
            member.approved_at = None
            member.approved_by = None
    db.add(
        LogbookReviewHistory(
            assignment_id=a.id,
            actor_id=current.id,
            action="APPROVE" if approve else "REQUEST_CHANGES",
            previous_status=old.value,
            new_status=new_status.value,
            comment=comment,
            attempt_number=a.attempt_number,
        )
    )
    statuses = {x.status for x in a.instance.assignments}
    a.instance.status = (
        LogbookInstanceStatus.COMPLETED
        if statuses == {LogbookAssignmentStatus.APPROVED}
        else LogbookInstanceStatus.CHANGES_REQUESTED
        if LogbookAssignmentStatus.CHANGES_REQUESTED in statuses
        else LogbookInstanceStatus.UNDER_REVIEW
    )
    db.commit()
    db.refresh(a)
    audit(
        db,
        current,
        "LOGBOOK_APPROVED" if approve else "LOGBOOK_CHANGES_REQUESTED",
        "LogbookAssignment",
        a.id,
        event_id=a.instance.event_id,
        old={"status": old},
        new={"status": a.status},
        metadata={"has_comment": bool(comment)},
    )
    return a


def get_template_detail(db, template_id, current):
    if current.role not in ADMIN | {UserRole.SUPERVISOR}:
        fail(403, "Insufficient role")
    obj = db.scalar(
        select(LogbookTemplate)
        .where(LogbookTemplate.id == template_id)
        .options(selectinload(LogbookTemplate.versions))
    )
    if not obj:
        fail(404, "Logbook template not found")
    return obj


def get_version_detail(db, version_id, current):
    if current.role not in ADMIN | {UserRole.SUPERVISOR}:
        fail(403, "Insufficient role")
    return _version(db, version_id, True)


def archive_template(db, template_id, current):
    if current.role not in ADMIN:
        fail(403, "Insufficient role")
    template = _template(db, template_id)
    old_status = template.status
    template.status = LogbookTemplateStatus.ARCHIVED
    template.archived_at = datetime.utcnow()
    db.commit()
    db.refresh(template)
    audit(
        db,
        current,
        "LOGBOOK_TEMPLATE_ARCHIVED",
        "LogbookTemplate",
        template.id,
        old={"status": old_status},
        new={"status": template.status},
    )
    return template


def list_event_instances(
    db, event_id, current, page, limit, status_filter=None, template_id=None, stage=None
):
    if not can_access_event(current, event_id, db):
        fail(403, "Insufficient role")
    filters = [LogbookInstance.event_id == event_id]
    if current.role == UserRole.CLIENT:
        filters.append(LogbookInstance.client_visibility.is_(True))
    if status_filter:
        filters.append(LogbookInstance.status == status_filter)
    if template_id:
        filters.append(LogbookInstance.template_id == template_id)
    if stage:
        filters.append(LogbookInstance.operational_stage == stage)
    total = db.scalar(select(func.count()).select_from(LogbookInstance).where(*filters)) or 0
    items = list(
        db.scalars(
            select(LogbookInstance)
            .where(*filters)
            .order_by(LogbookInstance.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def _load_instance(db, instance_id):
    instance = db.scalar(
        select(LogbookInstance)
        .where(LogbookInstance.id == instance_id)
        .options(
            selectinload(LogbookInstance.version)
            .selectinload(LogbookTemplateVersion.sections)
            .selectinload(LogbookSection.items)
            .selectinload(LogbookItem.options),
            selectinload(LogbookInstance.assignments)
            .selectinload(LogbookAssignment.responses)
            .selectinload(LogbookResponse.evidences),
        )
    )
    if not instance:
        fail(404, "Logbook instance not found")
    return instance


def calculate_metrics(instance):
    assignments = instance.assignments
    counts = {status: 0 for status in LogbookAssignmentStatus}
    for assignment in assignments:
        counts[assignment.status] += 1
    responses = [response for assignment in assignments for response in assignment.responses]
    required_ids = {
        item.id
        for section in instance.version.sections
        for item in section.items
        if item.is_required
    }
    effective = [r for r in responses if r.logbook_item_id in required_ids]
    completed_ids = {
        r.logbook_item_id
        for r in effective
        if r.result_status in {LogbookResultStatus.COMPLETED, LogbookResultStatus.NOT_APPLICABLE}
    }
    failed_ids = {
        r.logbook_item_id for r in effective if r.result_status == LogbookResultStatus.FAILED
    }
    total_participants = len(assignments)
    engaged = sum(1 for a in assignments if a.status != LogbookAssignmentStatus.PENDING)
    submitted = sum(
        counts[s]
        for s in (
            LogbookAssignmentStatus.SUBMITTED,
            LogbookAssignmentStatus.RESUBMITTED,
            LogbookAssignmentStatus.APPROVED,
        )
    )
    denominator = (
        len(required_ids)
        if instance.assignment_mode == LogbookAssignmentMode.SHARED
        else len(required_ids) * max(total_participants, 1)
    )
    completed_response_count = sum(
        1
        for r in effective
        if r.result_status in {LogbookResultStatus.COMPLETED, LogbookResultStatus.NOT_APPLICABLE}
    )
    return {
        "completion_percentage": round(100 * completed_response_count / denominator, 2)
        if denominator
        else 0,
        "participation_percentage": round(100 * engaged / total_participants, 2)
        if total_participants
        else 0,
        "approval_percentage": round(
            100 * counts[LogbookAssignmentStatus.APPROVED] / total_participants, 2
        )
        if total_participants
        else 0,
        "total_participants": total_participants,
        "pending": counts[LogbookAssignmentStatus.PENDING],
        "in_progress": counts[LogbookAssignmentStatus.IN_PROGRESS],
        "submitted": submitted,
        "changes_requested": counts[LogbookAssignmentStatus.CHANGES_REQUESTED],
        "approved": counts[LogbookAssignmentStatus.APPROVED],
        "total_required_items": len(required_ids),
        "completed_items": len(completed_ids),
        "failed_items": len(failed_ids),
        "collaborating_participants": sum(1 for a in assignments if a.responses),
    }


def get_instance_detail(db, instance_id, current):
    instance = _load_instance(db, instance_id)
    if current.role == UserRole.CLIENT:
        fail(403, "Use the client logbook summary endpoint")
    if not can_access_event(current, instance.event_id, db):
        fail(403, "Insufficient role")
    metrics = calculate_metrics(instance)
    visible_assignments = list(instance.assignments)
    if current.role in {UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}:
        visible_assignments = [
            assignment for assignment in instance.assignments if assignment.user_id == current.id
        ]
        if not visible_assignments:
            fail(403, "Not assigned to this logbook")
    data = InstanceRead.model_validate(instance).model_dump()
    event = db.get(Event, instance.event_id)
    data["event_name"] = event.name if event else ""
    data["version"] = VersionDetail.model_validate(instance.version).model_dump()
    assignments_data = []
    shared_participant_view = (
        instance.assignment_mode == LogbookAssignmentMode.SHARED
        and current.role in {UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}
    )
    shared_responses = (
        [
            response
            for member in instance.assignments
            for response in member.responses
        ]
        if shared_participant_view
        else []
    )
    for assignment in visible_assignments:
        assignment_data = AssignmentDetail.model_validate(assignment).model_dump()
        display_responses = shared_responses if shared_participant_view else assignment.responses
        if shared_participant_view:
            assignment_data["responses"] = [
                ResponseDetail.model_validate(response).model_dump()
                for response in display_responses
            ]
        user = db.get(User, assignment.user_id)
        assignment_data["user_name"] = user.full_name if user else None
        assignment_data["history"] = [
            ReviewHistoryRead.model_validate(entry).model_dump()
            for entry in db.scalars(
                select(LogbookReviewHistory)
                .where(LogbookReviewHistory.assignment_id == assignment.id)
                .order_by(LogbookReviewHistory.created_at.asc())
            ).all()
        ]
        for response_data, response in zip(assignment_data["responses"], display_responses):
            author = db.get(User, response.completed_by) if response.completed_by else None
            response_data["completed_by_name"] = author.full_name if author else None
            response_data["corrective_incident_id"] = db.scalar(
                select(LogbookIncidentLink.incident_id).where(
                    LogbookIncidentLink.response_id == response.id
                )
            )
            response_data["corrective_task_id"] = db.scalar(
                select(LogbookTaskLink.task_id).where(LogbookTaskLink.response_id == response.id)
            )
        assignments_data.append(assignment_data)
    data["assignments"] = assignments_data
    data["metrics"] = metrics
    return data


def open_instance(db, instance_id, current):
    instance = _load_instance(db, instance_id)
    if not can_manage_event(current, instance.event_id, db):
        fail(403, "Insufficient role")
    if instance.status not in {LogbookInstanceStatus.DRAFT, LogbookInstanceStatus.SCHEDULED}:
        fail(409, "Only draft or scheduled logbooks can be opened")
    old_status = instance.status
    instance.status = LogbookInstanceStatus.OPEN
    db.commit()
    db.refresh(instance)
    audit(
        db,
        current,
        "LOGBOOK_INSTANCE_OPENED",
        "LogbookInstance",
        instance.id,
        event_id=instance.event_id,
        old={"status": old_status},
        new={"status": instance.status},
    )
    return instance


def cancel_instance(db, instance_id, reason, current):
    instance = _load_instance(db, instance_id)
    if not can_manage_event(current, instance.event_id, db):
        fail(403, "Insufficient role")
    if instance.status in {LogbookInstanceStatus.COMPLETED, LogbookInstanceStatus.CANCELLED}:
        fail(409, "Logbook cannot be cancelled")
    old_status = instance.status
    instance.status = LogbookInstanceStatus.CANCELLED
    instance.cancelled_at = datetime.utcnow()
    instance.cancellation_reason = reason
    for assignment in instance.assignments:
        assignment.status = LogbookAssignmentStatus.CANCELLED
    db.commit()
    db.refresh(instance)
    audit(
        db,
        current,
        "LOGBOOK_INSTANCE_CANCELLED",
        "LogbookInstance",
        instance.id,
        event_id=instance.event_id,
        old={"status": old_status},
        new={"status": instance.status},
        metadata={"reason": reason},
    )
    return instance


def add_participants(db, instance_id, user_ids, current):
    instance = _load_instance(db, instance_id)
    if not can_manage_event(current, instance.event_id, db):
        fail(403, "Insufficient role")
    existing = {a.user_id for a in instance.assignments}
    if existing & set(user_ids):
        fail(409, "Participant is already assigned")
    valid = set(
        db.scalars(
            select(EventStaff.user_id)
            .join(User)
            .where(EventStaff.event_id == instance.event_id, User.is_active.is_(True))
        ).all()
    )
    if not set(user_ids) <= valid:
        fail(422, "All participants must be active event staff")
    for user_id in user_ids:
        db.add(LogbookAssignment(logbook_instance_id=instance.id, user_id=user_id))
    db.commit()
    audit(
        db,
        current,
        "LOGBOOK_PARTICIPANTS_ADDED",
        "LogbookInstance",
        instance.id,
        event_id=instance.event_id,
        metadata={"participant_count": len(user_ids)},
    )
    return _load_instance(db, instance_id).assignments


def remove_participant(db, instance_id, assignment_id, current):
    instance = _load_instance(db, instance_id)
    if not can_manage_event(current, instance.event_id, db):
        fail(403, "Insufficient role")
    assignment = next((a for a in instance.assignments if a.id == assignment_id), None)
    if not assignment:
        fail(404, "Participant not found")
    had_responses = bool(assignment.responses)
    if had_responses:
        assignment.status = LogbookAssignmentStatus.CANCELLED
    else:
        db.delete(assignment)
    db.commit()
    audit(
        db,
        current,
        "LOGBOOK_PARTICIPANT_REMOVED",
        "LogbookAssignment",
        assignment_id,
        event_id=instance.event_id,
        new={"status": assignment.status if had_responses else "REMOVED"},
    )


IMAGE_SIGNATURES = {
    "image/jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    "image/png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda content: (
        len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    ),
}


def validate_image_content(content: bytes, claimed_mime: str) -> None:
    validator = IMAGE_SIGNATURES.get(claimed_mime)
    if not validator or not validator(content):
        fail(422, "File content does not match an allowed image type")
    expected = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}[claimed_mime]
    try:
        with Image.open(BytesIO(content)) as image:
            actual = image.format
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        fail(422, "Invalid or corrupted image")
    if actual != expected:
        fail(422, "File content does not match the declared MIME type")


def upload_evidence(db, assignment_id, response_id, file: UploadFile, comment, current):
    assignment = _assignment(db, assignment_id, current)
    if assignment.user_id != current.id:
        fail(403, "Only the participant can upload evidence")
    if assignment.status not in {
        LogbookAssignmentStatus.PENDING,
        LogbookAssignmentStatus.IN_PROGRESS,
        LogbookAssignmentStatus.CHANGES_REQUESTED,
    }:
        fail(409, "Submitted assignments are locked")
    response = db.get(LogbookResponse, response_id)
    if not response:
        fail(404, "Response not found")
    response_assignment = db.get(LogbookAssignment, response.assignment_id)
    if response.assignment_id != assignment.id and not (
        response_assignment.logbook_instance_id == assignment.logbook_instance_id
        and assignment.instance.assignment_mode == LogbookAssignmentMode.SHARED
    ):
        fail(404, "Response not found")
    item = db.get(LogbookItem, response.logbook_item_id)
    current_count = (
        db.scalar(
            select(func.count())
            .select_from(LogbookEvidence)
            .where(LogbookEvidence.response_id == response.id, LogbookEvidence.deleted_at.is_(None))
        )
        or 0
    )
    if current_count >= item.max_evidences:
        fail(422, "Maximum evidence count reached")
    content = file.file.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        fail(413, f"File exceeds {settings.max_upload_size_mb} MB limit")
    claimed = file.content_type or ""
    validate_image_content(content, claimed)
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[claimed]
    original = Path(file.filename or f"evidence{extension}").name
    storage_key = save_bytes_file(
        "logbooks",
        content,
        content_type=claimed,
        allowed_content_types={claimed: extension},
        original_filename=original,
    )
    evidence = LogbookEvidence(
        instance_id=assignment.logbook_instance_id,
        assignment_id=assignment.id,
        item_id=item.id,
        response_id=response.id,
        uploaded_by=current.id,
        comment=comment,
        mime_type=claimed,
        file_size=len(content),
        original_filename=original,
        storage_key=storage_key,
        client_visible=item.client_visible_by_default,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    audit(
        db,
        current,
        "LOGBOOK_EVIDENCE_UPLOADED",
        "LogbookEvidence",
        evidence.id,
        event_id=assignment.instance.event_id,
        metadata={"mime_type": evidence.mime_type, "file_size": evidence.file_size},
    )
    return evidence


def _evidence(db, evidence_id):
    evidence = db.get(LogbookEvidence, evidence_id)
    if not evidence or evidence.deleted_at:
        fail(404, "Evidence not found")
    return evidence


def evidence_access(db, evidence_id, current):
    evidence = _evidence(db, evidence_id)
    instance = db.get(LogbookInstance, evidence.instance_id)
    if current.role == UserRole.CLIENT:
        event = db.get(Event, instance.event_id)
        allowed = (
            instance.client_visibility
            and evidence.client_visible
            and current.client_id == event.client_id
        )
    else:
        assignment = db.get(LogbookAssignment, evidence.assignment_id)
        allowed = can_access_event(current, instance.event_id, db) and (
            current.role not in {UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}
            or assignment.user_id == current.id
            or instance.assignment_mode == LogbookAssignmentMode.SHARED
            and any(a.user_id == current.id for a in instance.assignments)
        )
    if not allowed:
        fail(403, "Insufficient role")
    token = create_access_token(
        {"scope": "logbook_evidence", "evidence_id": str(evidence.id)},
        expires_delta=timedelta(minutes=5),
    )
    return {
        "url": f"/api/v1/logbook-evidences/{evidence.id}/content?token={token}",
        "expires_in": 300,
    }


def evidence_content(db, evidence_id, token):
    try:
        payload = decode_access_token(token)
    except ValueError:
        fail(401, "Invalid or expired evidence token")
    if payload.get("scope") != "logbook_evidence" or payload.get("evidence_id") != str(evidence_id):
        fail(403, "Invalid evidence token scope")
    evidence = _evidence(db, evidence_id)
    return (*read_stored_file(evidence.storage_key), evidence.original_filename)


def delete_evidence(db, evidence_id, current):
    evidence = _evidence(db, evidence_id)
    assignment = db.get(LogbookAssignment, evidence.assignment_id)
    if evidence.uploaded_by != current.id or assignment.user_id != current.id:
        fail(403, "Only the uploader can remove this evidence")
    if assignment.status not in {
        LogbookAssignmentStatus.PENDING,
        LogbookAssignmentStatus.IN_PROGRESS,
        LogbookAssignmentStatus.CHANGES_REQUESTED,
    }:
        fail(409, "Submitted assignments are locked")
    evidence.deleted_at = datetime.utcnow()
    db.commit()
    audit(
        db,
        current,
        "LOGBOOK_EVIDENCE_DELETED",
        "LogbookEvidence",
        evidence.id,
        event_id=assignment.instance.event_id,
        new={"deleted": True},
    )


def create_corrective_incident(db, response_id, payload, current):
    response = db.get(LogbookResponse, response_id)
    if not response:
        fail(404, "Response not found")
    assignment = response.assignment
    if not can_manage_event(current, assignment.instance.event_id, db):
        fail(403, "Insufficient role")
    if db.scalar(
        select(LogbookIncidentLink.id).where(LogbookIncidentLink.response_id == response.id)
    ):
        fail(409, "An incident already exists for this response")
    if payload.assigned_to:
        valid = db.scalar(
            select(EventStaff.id).where(
                EventStaff.event_id == assignment.instance.event_id,
                EventStaff.user_id == payload.assigned_to,
            )
        )
        if not valid:
            fail(422, "Assignee must belong to event staff")
    available_evidences = {e.id: e for e in response.evidences if not e.deleted_at}
    selected_evidence_ids = set(payload.evidence_ids) if payload.evidence_ids else set(
        available_evidences
    )
    if not selected_evidence_ids <= set(available_evidences):
        fail(422, "Every selected evidence must belong to the response")
    incident = Incident(
        event_id=assignment.instance.event_id,
        zone_id=assignment.instance.zone_id,
        reported_by=current.id,
        assigned_to=payload.assigned_to,
        title=payload.title,
        description=payload.description,
        incident_type=payload.incident_type,
        priority=payload.priority,
        status=IncidentStatus.ASSIGNED if payload.assigned_to else IncidentStatus.REPORTED,
        source="LOGBOOK",
    )
    db.add(incident)
    db.flush()
    link = LogbookIncidentLink(
        incident_id=incident.id,
        instance_id=assignment.instance.id,
        assignment_id=assignment.id,
        item_id=response.logbook_item_id,
        response_id=response.id,
        worker_id=response.completed_by,
        created_by=current.id,
    )
    db.add(link)
    db.flush()
    for evidence_id in selected_evidence_ids:
        db.add(
            LogbookCorrectiveEvidenceLink(
                logbook_evidence_id=evidence_id, incident_link_id=link.id
            )
        )
    db.commit()
    db.refresh(incident)
    audit(
        db,
        current,
        "LOGBOOK_INCIDENT_CREATED",
        "Incident",
        incident.id,
        event_id=incident.event_id,
        metadata={"response_id": response.id},
    )
    return incident


def create_corrective_task(db, response_id, payload, current):
    response = db.get(LogbookResponse, response_id)
    if not response:
        fail(404, "Response not found")
    assignment = response.assignment
    if not can_manage_event(current, assignment.instance.event_id, db):
        fail(403, "Insufficient role")
    if db.scalar(select(LogbookTaskLink.id).where(LogbookTaskLink.response_id == response.id)):
        fail(409, "A corrective task already exists for this response")
    valid = db.scalar(
        select(EventStaff.id).where(
            EventStaff.event_id == assignment.instance.event_id,
            EventStaff.user_id == payload.assigned_to,
        )
    )
    if not valid:
        fail(422, "Assignee must belong to event staff")
    available_evidences = {e.id: e for e in response.evidences if not e.deleted_at}
    selected_evidence_ids = set(payload.evidence_ids) if payload.evidence_ids else set(
        available_evidences
    )
    if not selected_evidence_ids <= set(available_evidences):
        fail(422, "Every selected evidence must belong to the response")
    task = Task(
        event_id=assignment.instance.event_id,
        zone_id=assignment.instance.zone_id,
        assigned_to=payload.assigned_to,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        scheduled_at=payload.scheduled_at,
        created_by=current.id,
    )
    db.add(task)
    db.flush()
    link = LogbookTaskLink(
        task_id=task.id,
        instance_id=assignment.instance.id,
        assignment_id=assignment.id,
        item_id=response.logbook_item_id,
        response_id=response.id,
        created_by=current.id,
    )
    db.add(link)
    db.flush()
    for evidence_id in selected_evidence_ids:
        db.add(
            LogbookCorrectiveEvidenceLink(logbook_evidence_id=evidence_id, task_link_id=link.id)
        )
    db.commit()
    db.refresh(task)
    audit(
        db,
        current,
        "LOGBOOK_CORRECTIVE_TASK_CREATED",
        "Task",
        task.id,
        event_id=task.event_id,
        metadata={"response_id": response.id},
    )
    return task


def client_summary(db, instance_id, current):
    if current.role != UserRole.CLIENT:
        fail(403, "Client role required")
    instance = _load_instance(db, instance_id)
    event = db.get(Event, instance.event_id)
    if not instance.client_visibility or current.client_id != event.client_id:
        fail(404, "Logbook summary not found")
    metrics = calculate_metrics(instance)
    public = [
        e
        for a in instance.assignments
        for r in a.responses
        for e in r.evidences
        if e.client_visible and not e.deleted_at
    ]
    return {
        "id": instance.id,
        "event_id": instance.event_id,
        "name": instance.name,
        "operational_stage": instance.operational_stage,
        "status": instance.status,
        "completion_percentage": metrics["completion_percentage"],
        "participation_percentage": metrics["participation_percentage"],
        "approval_percentage": metrics["approval_percentage"],
        "total_required_items": metrics["total_required_items"],
        "completed_items": metrics["completed_items"],
        "failed_items": metrics["failed_items"],
        "public_evidences": public,
    }
