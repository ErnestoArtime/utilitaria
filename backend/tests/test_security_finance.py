import importlib
import os
import sys
from decimal import Decimal

from fastapi.testclient import TestClient


def load_app(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'utilitaria-test.db'}"
    os.environ["ADMIN_ENROLLMENT_CODE"] = "admin-test-code"
    os.environ["MEMBER_ENROLLMENT_CODE"] = "member-test-code"
    os.environ["CAPTURE_ENROLLMENT_CODE"] = "capture-test-code"
    os.environ["ALLOW_LEGACY_API_KEY"] = "false"
    module = (
        importlib.reload(sys.modules["app.main"])
        if "app.main" in sys.modules
        else importlib.import_module("app.main")
    )
    return module, TestClient(module.app)


def enroll(client, code, name):
    response = client.post(
        "/api/auth/enroll",
        json={"code": code, "device_name": name},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_enrollment_permissions_idempotency_and_privacy(tmp_path):
    module, client = load_app(tmp_path)
    admin = enroll(client, "admin-test-code", "Admin")
    member = enroll(client, "member-test-code", "Member")
    capture = enroll(client, "capture-test-code", "Capture")

    assert client.get("/api/finance/summary", headers=member).status_code == 200
    assert client.get("/api/finance/summary", headers=capture).status_code == 403
    assert client.post(
        "/api/balance/entries",
        headers=member,
        json={"amount": 10, "description": "No permitido"},
    ).status_code == 403

    rule = client.post(
        "/api/notification-rules",
        headers=admin,
        json={"text_contains": "PRIVADO", "action": "exclude_share"},
    )
    assert rule.status_code == 200

    payload = {
        "external_id": "ing-unique-1",
        "package_name": "com.ing.mobile",
        "title": "ING",
        "body": "Has recibido una transferencia de 25 EUR de PRIVADO",
        "received_at": "2026-10-03T13:28:01Z",
    }
    first = client.post("/api/notifications", headers=capture, json=payload)
    second = client.post("/api/notifications", headers=capture, json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["shared_with_family"] is False
    assert first.json()["received_at"].startswith("2026-10-03T13:28:01")
    assert first.json()["synced_at"] is not None

    with module.SessionLocal() as db:
        notifications = list(db.scalars(module.select(module.Notification)))
        entries = list(db.scalars(module.select(module.BalanceEntry)))
        outbox = list(db.scalars(module.select(module.WhatsAppOutbox)))
    assert len(notifications) == 1
    assert len(entries) == 1
    assert outbox == []


def test_currency_is_not_mixed_and_linked_transfer_is_atomic(tmp_path):
    module, client = load_app(tmp_path)
    admin = enroll(client, "admin-test-code", "Admin")

    with module.SessionLocal() as db:
        now = module.datetime.now(module.timezone.utc)
        db.add_all(
            [
                module.BalanceEntry(
                    amount=Decimal("10"), description="EUR", created_at=now, currency="EUR"
                ),
                module.BalanceEntry(
                    amount=Decimal("20"), description="USD", created_at=now, currency="USD"
                ),
            ]
        )
        db.commit()

    summary = client.get("/api/finance/summary", headers=admin)
    assert summary.status_code == 200
    assert Decimal(summary.json()["balance"]) == Decimal("10")
    assert Decimal(summary.json()["by_currency"]["USD"]) == Decimal("20")

    created = client.post(
        "/api/balance/transfers",
        headers=admin,
        json={
            "amount": 15,
            "description": "Efectivo",
            "from_member": "cousin",
            "to_member": "me",
            "currency": "EUR",
        },
    )
    assert created.status_code == 200
    rows = created.json()
    assert sum(Decimal(row["amount"]) for row in rows) == Decimal("0")
    with module.SessionLocal() as db:
        transfer_notice = db.scalar(
            module.select(module.WhatsAppOutbox)
            .where(module.WhatsAppOutbox.dedupe_key.like("member-transfer:%"))
        )
        assert "Glender → Ernesto" in transfer_notice.message
    assert client.patch(
        f"/api/balance/entries/{rows[0]['id']}",
        headers=admin,
        json={"amount": -99},
    ).status_code == 409

    group_id = rows[0]["transfer_group_id"]
    updated = client.patch(
        f"/api/balance/transfers/{group_id}",
        headers=admin,
        json={"amount": 22},
    )
    assert updated.status_code == 200
    assert sum(Decimal(row["amount"]) for row in updated.json()) == Decimal("0")
