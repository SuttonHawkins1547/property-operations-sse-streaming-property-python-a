from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class MaintenanceRequest(BaseModel):
    request_id: str
    unit: str
    summary: str
    emergency: bool = False


class TenantDocument(BaseModel):
    document_id: str
    unit: str
    kind: str
    expires_on: date


class InspectionReminder(BaseModel):
    inspection_id: str
    unit: str
    due_on: date


class PropertyUpdate(BaseModel):
    as_of: date
    maintenance_requests: list[MaintenanceRequest] = Field(default_factory=list)
    tenant_documents: list[TenantDocument] = Field(default_factory=list)
    inspection_reminders: list[InspectionReminder] = Field(default_factory=list)


class AttentionItem(BaseModel):
    kind: str
    item_id: str
    unit: str
    reason: str
    priority: int


def select_attention(update: PropertyUpdate) -> list[AttentionItem]:
    """Return actionable records in stable priority order."""
    items: list[AttentionItem] = []

    for request in update.maintenance_requests:
        items.append(
            AttentionItem(
                kind="maintenance",
                item_id=request.request_id,
                unit=request.unit,
                reason=request.summary,
                priority=0 if request.emergency else 3,
            )
        )

    for document in update.tenant_documents:
        days_left = (document.expires_on - update.as_of).days
        if days_left <= 30:
            items.append(
                AttentionItem(
                    kind="tenant_document",
                    item_id=document.document_id,
                    unit=document.unit,
                    reason=f"{document.kind} expires in {days_left} days",
                    priority=1 if days_left < 0 else 2,
                )
            )

    for reminder in update.inspection_reminders:
        days_left = (reminder.due_on - update.as_of).days
        if days_left <= 7:
            items.append(
                AttentionItem(
                    kind="inspection",
                    item_id=reminder.inspection_id,
                    unit=reminder.unit,
                    reason=f"inspection due in {days_left} days",
                    priority=1 if days_left < 0 else 2,
                )
            )

    return sorted(items, key=lambda item: (item.priority, item.unit, item.item_id))
