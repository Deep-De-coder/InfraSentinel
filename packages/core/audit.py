from uuid import uuid4

from packages.core.models import AuditEvent


def make_audit_event(
    *,
    change_id: str,
    event_type: str,
    step_id: str | None = None,
    payload: dict | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id=str(uuid4()),
        change_id=change_id,
        step_id=step_id,
        event_type=event_type,
        payload=payload or {},
    )
