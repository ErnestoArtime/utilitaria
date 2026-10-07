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

    expense = client.post(
        "/api/balance/entries",
        headers=admin,
        json={
            "amount": 55.63,
            "description": "Gastos",
            "kind": "expense",
            "category": "expense",
            "member": "me",
        },
    )
    assert expense.status_code == 200
    assert Decimal(expense.json()["amount"]) == Decimal("-55.63")
    edited_expense = client.patch(
        f"/api/balance/entries/{expense.json()['id']}",
        headers=admin,
        json={
            "amount": -12.5,
            "description": "Ingreso corregido",
            "kind": "income",
            "category": "income",
            "member": "cousin",
            "created_at": "2026-10-07T10:57:00Z",
        },
    )
    assert edited_expense.status_code == 200
    assert Decimal(edited_expense.json()["amount"]) == Decimal("12.50")
    assert edited_expense.json()["member"] == "cousin"
    assert edited_expense.json()["created_at"].startswith("2026-10-07T10:57:00")
    assert client.delete(
        f"/api/balance/entries/{expense.json()['id']}", headers=admin
    ).status_code == 204

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
        assert "Saldo de Glender: -15.00 EUR" in transfer_notice.message
        assert "Saldo de Ernesto: 15.00 EUR" in transfer_notice.message
        assert "Total común: 10.00 EUR" in transfer_notice.message
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
    with module.SessionLocal() as db:
        update_notice = db.scalar(
            module.select(module.WhatsAppOutbox)
            .where(module.WhatsAppOutbox.message.like("%Utilitaria · Ajuste actualizado%"))
        )
        assert "Saldo de Glender: -22.00 EUR" in update_notice.message
        assert "Saldo de Ernesto: 22.00 EUR" in update_notice.message
        assert "Total común: 10.00 EUR" in update_notice.message
    assert client.delete(
        f"/api/balance/transfers/{group_id}", headers=admin
    ).status_code == 204
    with module.SessionLocal() as db:
        assert list(
            db.scalars(
                module.select(module.BalanceEntry).where(
                    module.BalanceEntry.transfer_group_id == group_id
                )
            )
        ) == []


def test_bank_notification_creates_one_rich_whatsapp_message(tmp_path):
    module, client = load_app(tmp_path)
    capture = enroll(client, "capture-test-code", "Capture")

    outgoing = client.post(
        "/api/notifications",
        headers=capture,
        json={
            "external_id": "ing-outgoing-rich-1",
            "package_name": "com.ing.mobile",
            "title": "Tu transferencia ya ha llegado",
            "body": (
                "Melissa, la transferencia que ordenaste por importe de 800 eur "
                "a la cuenta de TITANES TELECOMUNICACIONES 237294 en concepto de "
                "Movimiento ING ya ha llegado a su destino."
            ),
        },
    )
    assert outgoing.status_code == 200
    incoming = client.post(
        "/api/notifications",
        headers=capture,
        json={
            "external_id": "ing-incoming-rich-1",
            "package_name": "com.ing.mobile",
            "title": "Has recibido una transferencia",
            "body": "Acabas de recibir en tu cuenta una transferencia de 110 euros de MARCO SILVESTRI.",
        },
    )
    assert incoming.status_code == 200

    with module.SessionLocal() as db:
        messages = list(
            db.scalars(
                module.select(module.WhatsAppOutbox).order_by(
                    module.WhatsAppOutbox.id
                )
            )
        )
    assert len(messages) == 2
    assert messages[0].event_type == "transfer_sent"
    assert "📤 Utilitaria · Transferencia realizada" in messages[0].message
    assert "Destinatario: TITANES TELECOMUNICACIONES 237294" in messages[0].message
    assert "Concepto: Movimiento ING" in messages[0].message
    assert "Saldo de Glender: -800.00 EUR" in messages[0].message
    assert "Total común: -800.00 EUR" in messages[0].message
    assert messages[1].event_type == "transfer_received"
    assert "💰 Utilitaria · Transferencia recibida" in messages[1].message
    assert "De: MARCO SILVESTRI" in messages[1].message
    assert "Saldo de Glender: -690.00 EUR" in messages[1].message
    assert "Total común: -690.00 EUR" in messages[1].message
