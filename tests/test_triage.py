from datetime import date

from property_stream.triage import PropertyUpdate, select_attention


def test_emergency_and_overdue_records_lead_the_stream_snapshot() -> None:
    update = PropertyUpdate.model_validate(
        {
            "as_of": "2026-10-02",
            "maintenance_requests": [
                {"request_id": "mr-8", "unit": "4B", "summary": "No hot water"},
                {
                    "request_id": "mr-2",
                    "unit": "1A",
                    "summary": "Active water leak",
                    "emergency": True,
                },
            ],
            "tenant_documents": [
                {
                    "document_id": "doc-3",
                    "unit": "2C",
                    "kind": "insurance certificate",
                    "expires_on": "2026-09-30",
                },
                {
                    "document_id": "doc-9",
                    "unit": "3D",
                    "kind": "parking agreement",
                    "expires_on": "2027-01-01",
                },
            ],
            "inspection_reminders": [
                {"inspection_id": "in-4", "unit": "5A", "due_on": "2026-10-06"}
            ],
        }
    )

    attention = select_attention(update)

    assert [item.item_id for item in attention] == ["mr-2", "doc-3", "in-4", "mr-8"]
    assert attention[1].reason == "insurance certificate expires in -2 days"
    assert all(item.item_id != "doc-9" for item in attention)
    assert update.as_of == date(2026, 10, 2)
