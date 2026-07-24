from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image

from app.models.enums import (
    LogbookAssignmentMode,
    LogbookAssignmentStatus,
    LogbookResultStatus,
)
from app.schemas.logbook_schema import (
    ClientLogbookSummary,
    InstanceCreate,
    ItemIn,
    ParticipantsIn,
    SectionIn,
    TemplateCreate,
)
from app.services.logbook_service import (
    _clear_response_values,
    calculate_metrics,
    validate_image_content,
)


def image_bytes(fmt: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), "green").save(output, format=fmt)
    return output.getvalue()


@pytest.mark.parametrize(
    ("fmt", "mime"), [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")]
)
def test_real_image_mime_is_accepted(fmt, mime):
    validate_image_content(image_bytes(fmt), mime)


def test_spoofed_or_corrupt_image_is_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_image_content(b"\xff\xd8\xffnot-a-real-image", "image/jpeg")
    assert exc.value.status_code == 422


def test_status_select_requires_options():
    with pytest.raises(ValueError):
        ItemIn(
            title="Estado",
            position=0,
            item_type="STATUS_SELECT",
            evidence_policy="NONE",
        )


def test_duplicate_participants_are_rejected():
    from uuid import uuid4

    user_id = uuid4()
    with pytest.raises(ValueError):
        ParticipantsIn(user_ids=[user_id, user_id])


def test_duplicate_section_positions_are_rejected():
    with pytest.raises(ValueError):
        TemplateCreate(
            name="Control",
            operational_stage="OPERATION",
            default_assignment_mode="INDIVIDUAL",
            sections=[
                SectionIn(title="Uno", position=0),
                SectionIn(title="Dos", position=0),
            ],
        )


def test_duplicate_item_positions_are_rejected():
    item = {
        "position": 0,
        "item_type": "CHECKBOX",
        "evidence_policy": "NONE",
    }
    with pytest.raises(ValueError):
        SectionIn(
            title="Control",
            position=0,
            items=[
                ItemIn(title="Uno", **item),
                ItemIn(title="Dos", **item),
            ],
        )


def test_client_summary_contract_contains_no_internal_identity_fields():
    fields = set(ClientLogbookSummary.model_fields)
    assert not fields & {
        "assignments",
        "supervisor_id",
        "user_id",
        "user_name",
        "review_comment",
        "history",
        "storage_key",
    }


def test_invalid_instance_dates_are_rejected():
    from datetime import datetime
    from uuid import uuid4

    now = datetime.utcnow()
    with pytest.raises(ValueError):
        InstanceCreate(
            template_version_id=uuid4(),
            assignment_mode="INDIVIDUAL",
            participant_ids=[uuid4()],
            opens_at=now,
            due_at=now,
        )


def test_individual_metrics_keep_completion_participation_and_approval_separate():
    required = SimpleNamespace(id="item", is_required=True)
    version = SimpleNamespace(sections=[SimpleNamespace(items=[required])])
    assignments = [
        SimpleNamespace(
            status=LogbookAssignmentStatus.APPROVED,
            responses=[
                SimpleNamespace(logbook_item_id="item", result_status=LogbookResultStatus.COMPLETED)
            ],
        ),
        SimpleNamespace(status=LogbookAssignmentStatus.PENDING, responses=[]),
    ]
    instance = SimpleNamespace(
        assignment_mode=LogbookAssignmentMode.INDIVIDUAL,
        assignments=assignments,
        version=version,
    )
    metrics = calculate_metrics(instance)
    assert metrics["completion_percentage"] == 50
    assert metrics["participation_percentage"] == 50
    assert metrics["approval_percentage"] == 50


def test_clear_response_keeps_record_and_version_but_removes_values():
    from uuid import uuid4

    actor_id = uuid4()
    response = SimpleNamespace(
        selected_option_id=uuid4(),
        boolean_value=False,
        numeric_value=0,
        text_value="respuesta",
        is_not_applicable=True,
        result_status=LogbookResultStatus.COMPLETED,
        comment="observación",
        completed_by=None,
        completed_at=None,
        version=3,
    )
    _clear_response_values(response, actor_id)
    assert response.selected_option_id is None
    assert response.boolean_value is None
    assert response.numeric_value is None
    assert response.text_value is None
    assert response.is_not_applicable is False
    assert response.result_status == LogbookResultStatus.PENDING
    assert response.comment is None
    assert response.completed_by == actor_id
    assert response.completed_at is not None
    assert response.version == 4
