from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import html
import hmac
import os
import re
import secrets
import uuid
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Integer, JSON, Numeric, String, Text, create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./utilitaria.db")
API_KEY = os.getenv("API_KEY", "")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    package_name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(50), default="android")
    category: Mapped[str] = mapped_column(String(50), default="other")
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_business: Mapped[bool] = mapped_column(Boolean, default=False)
    shared_with_family: Mapped[bool] = mapped_column(Boolean, default=False)
    external_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    parsed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)


class BalanceEntry(Base):
    __tablename__ = "balance_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notification_id: Mapped[int | None] = mapped_column(nullable=True)
    kind: Mapped[str] = mapped_column(String(30), default="adjustment")
    category: Mapped[str] = mapped_column(String(50), default="other")
    member: Mapped[str] = mapped_column(String(100), default="shared")
    currency: Mapped[str] = mapped_column(String(10), default="EUR")
    is_business: Mapped[bool] = mapped_column(Boolean, default=False)
    external_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    transfer_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class NotificationRule(Base):
    __tablename__ = "notification_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    package_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text_contains: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(30), default="exclude_share")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AlertTarget(Base):
    __tablename__ = "alert_targets"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    group_name: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="unknown")
    status_label: Mapped[str] = mapped_column(String(255), default="Pendiente")
    price: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AlertEvent(Base):
    __tablename__ = "alert_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(index=True)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(String(100), default="Android")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WhatsAppConfig(Base):
    __tablename__ = "whatsapp_config"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipients: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    transfer_received: Mapped[bool] = mapped_column(Boolean, default=True)
    transfer_sent: Mapped[bool] = mapped_column(Boolean, default=True)
    balance_changes: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApiCredential(Base):
    __tablename__ = "api_credentials"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30), default="member")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WhatsAppOutbox(Base):
    __tablename__ = "whatsapp_outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    recipient: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


Base.metadata.create_all(engine)


def ensure_schema():
    statements = [
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'other'",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS counterparty VARCHAR(255)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_business BOOLEAN DEFAULT FALSE",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS shared_with_family BOOLEAN DEFAULT FALSE",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS external_id VARCHAR(500)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS parsed_amount NUMERIC(12, 2)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS currency VARCHAR(10)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS synced_at TIMESTAMP WITH TIME ZONE",
        "UPDATE notifications SET synced_at = received_at WHERE synced_at IS NULL",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS kind VARCHAR(30) DEFAULT 'adjustment'",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'other'",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS member VARCHAR(100) DEFAULT 'shared'",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'EUR'",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS is_business BOOLEAN DEFAULT FALSE",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS external_id VARCHAR(500)",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS transfer_group_id VARCHAR(36)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_external_id ON notifications (external_id) WHERE external_id IS NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_balance_entries_external_id ON balance_entries (external_id) WHERE external_id IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS ix_balance_entries_transfer_group_id ON balance_entries (transfer_group_id)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                # SQLite and older installations may not support every ALTER form.
                pass


ensure_schema()
app = FastAPI(title="Utilitaria API", version=os.getenv("APP_VERSION", "0.9.0"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://utilitaria.eav-labs.com",
        "http://localhost:8125",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

_eltoque_cache: dict[str, object] | None = None


ROLE_PERMISSIONS = {
    "admin": {"read", "write", "capture", "settings", "devices"},
    "member": {"read"},
    "capture": {"capture"},
    "service": {"read", "write", "capture", "settings", "devices"},
}

MEMBER_NAMES = {
    "me": "Ernesto",
    "cousin": "Glender",
    "shared": "Saldo común",
}


def member_name(member: str) -> str:
    return MEMBER_NAMES.get(member, member)


def balance_snapshot(db: Session, currency: str = "EUR") -> tuple[dict[str, Decimal], Decimal]:
    balances = {member: Decimal("0.00") for member in MEMBER_NAMES}
    rows = db.scalars(
        select(BalanceEntry).where(
            BalanceEntry.is_business.is_(False),
            BalanceEntry.currency == currency,
        )
    )
    for row in rows:
        balances[row.member] = balances.get(row.member, Decimal("0.00")) + row.amount
    return balances, sum(balances.values(), Decimal("0.00"))


def balance_message(db: Session, members: list[str], currency: str = "EUR") -> str:
    balances, total = balance_snapshot(db, currency)
    lines: list[str] = []
    for member in dict.fromkeys(members):
        label = "Saldo común sin asignar" if member == "shared" else f"Saldo de {member_name(member)}"
        lines.append(f"{label}: {balances.get(member, Decimal('0.00')):.2f} {currency}")
    lines.append(f"Total común: {total:.2f} {currency}")
    return "\n".join(lines)


class Principal(BaseModel):
    credential_id: int | None = None
    label: str
    role: str
    permissions: set[str]
    legacy: bool = False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_service_credential():
    raw_token = os.getenv("SERVICE_API_TOKEN", "")
    if not raw_token:
        return
    digest = token_hash(raw_token)
    with SessionLocal() as db:
        existing = db.scalar(select(ApiCredential).where(ApiCredential.token_hash == digest))
        if existing:
            if not existing.enabled or existing.revoked_at is not None:
                existing.enabled = True
                existing.revoked_at = None
                db.commit()
            return
        db.add(
            ApiCredential(
                token_hash=digest,
                label="Backend monitor",
                role="service",
                enabled=True,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()


ensure_service_credential()


def auth(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> Principal:
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
        if raw_token:
            with SessionLocal() as db:
                credential = db.scalar(
                    select(ApiCredential).where(ApiCredential.token_hash == token_hash(raw_token))
                )
                if credential and credential.enabled and credential.revoked_at is None:
                    credential.last_seen_at = datetime.now(timezone.utc)
                    db.commit()
                    return Principal(
                        credential_id=credential.id,
                        label=credential.label,
                        role=credential.role,
                        permissions=ROLE_PERMISSIONS.get(credential.role, set()),
                    )
    allow_legacy = os.getenv("ALLOW_LEGACY_API_KEY", "false").lower() == "true"
    if allow_legacy and API_KEY and x_api_key and hmac.compare_digest(x_api_key, API_KEY):
        return Principal(
            label="legacy-api-key",
            role="service",
            permissions=ROLE_PERMISSIONS["service"],
            legacy=True,
        )
    raise HTTPException(status_code=401, detail="authentication required")


def require_permission(permission: str):
    def dependency(principal: Principal = Depends(auth)) -> Principal:
        if permission not in principal.permissions:
            raise HTTPException(status_code=403, detail="permission denied")
        return principal

    return dependency


class NotificationIn(BaseModel):
    package_name: str
    title: str | None = None
    body: str
    received_at: datetime | None = None
    category: str = "other"
    counterparty: str | None = None
    is_business: bool = False
    shared_with_family: bool = False
    external_id: str | None = Field(default=None, max_length=500)


class NotificationOut(NotificationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    received_at: datetime
    synced_at: datetime
    parsed_amount: Decimal | None = None
    currency: str | None = None


class BalanceIn(BaseModel):
    amount: Decimal = Field(description="Importe positivo o negativo")
    description: str = Field(min_length=1, max_length=500)
    notification_id: int | None = None
    kind: str = "adjustment"
    category: str = "other"
    member: str = "shared"
    currency: str = Field(default="EUR", pattern="^EUR$")
    is_business: bool = False
    created_at: datetime | None = None
    external_id: str | None = Field(default=None, max_length=500)


class BalanceTransferIn(BaseModel):
    amount: Decimal = Field(gt=0)
    description: str = Field(min_length=1, max_length=500)
    from_member: str = Field(pattern="^(me|cousin|shared)$")
    to_member: str = Field(pattern="^(me|cousin|shared)$")
    currency: str = Field(default="EUR", pattern="^EUR$")
    created_at: datetime | None = None


class BalanceTransferPatch(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    from_member: str | None = Field(default=None, pattern="^(me|cousin|shared)$")
    to_member: str | None = Field(default=None, pattern="^(me|cousin|shared)$")
    created_at: datetime | None = None


class BalanceOut(BalanceIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    transfer_group_id: str | None = None


class BalancePatch(BaseModel):
    amount: Decimal | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    kind: str | None = None
    category: str | None = None
    member: str | None = None
    is_business: bool | None = None
    created_at: datetime | None = None


def normalized_balance_amount(amount: Decimal, kind: str, category: str) -> Decimal:
    value = abs(amount)
    if kind in {"expense", "transfer"} or category == "expense":
        return -value
    if kind == "income" or category == "income":
        return value
    return amount


class NotificationPatch(BaseModel):
    category: str | None = None
    is_business: bool | None = None
    shared_with_family: bool | None = None


class RuleIn(BaseModel):
    package_name: str | None = None
    text_contains: str = Field(min_length=1, max_length=255)
    action: str = "exclude_share"


class RuleOut(RuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    enabled: bool


class DeviceTokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    name: str = Field(default="Android", min_length=1, max_length=100)


class WhatsAppConfigIn(BaseModel):
    recipients: list[str] = Field(default_factory=list)
    enabled: bool = True
    transfer_received: bool = True
    transfer_sent: bool = True
    balance_changes: bool = True


class WhatsAppConfigOut(WhatsAppConfigIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    updated_at: datetime


class WhatsAppTestIn(BaseModel):
    message: str = Field(
        default="Prueba de Utilitaria: OpenWA está conectado correctamente.",
        min_length=1,
        max_length=4096,
    )


class EnrollIn(BaseModel):
    code: str = Field(min_length=8, max_length=255)
    device_name: str = Field(min_length=1, max_length=120)


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
    role: str
    enabled: bool
    created_at: datetime
    last_seen_at: datetime | None = None
    revoked_at: datetime | None = None


class EnrollOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    credential: CredentialOut


class WhatsAppOutboxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_type: str
    recipient: str
    status: str
    attempts: int
    created_at: datetime
    next_attempt_at: datetime
    sent_at: datetime | None = None
    last_error: str | None = None


def serialize_alert_target(item: AlertTarget) -> dict:
    return {
        "id": item.id,
        "slug": item.slug,
        "group": item.group_name,
        "name": item.name,
        "url": item.url,
        "status": item.status,
        "status_label": item.status_label,
        "price": item.price,
        "enabled": item.enabled,
        "last_checked_at": item.last_checked_at,
        "last_changed_at": item.last_changed_at,
        "last_error": item.last_error,
        "details": item.details or {},
    }


def seed_alert_targets(db: Session) -> list[AlertTarget]:
    definitions = [
        {
            "slug": "gas-10kg-goniogas",
            "group_name": "gas",
            "name": "Cilindro de gas de 10 kg",
            "url": "https://goniogas.com/producto/cilindro-de-gas-de-10kg/",
        },
        {
            "slug": "tiendasolar-catalog",
            "group_name": "solar",
            "name": "Catálogo TiendaSolar",
            "url": "https://solar.eav-labs.com/",
        },
    ]
    existing = {item.slug: item for item in db.scalars(select(AlertTarget))}
    for definition in definitions:
        if definition["slug"] not in existing:
            item = AlertTarget(**definition)
            db.add(item)
            existing[item.slug] = item
    db.commit()
    return list(existing.values())


def send_alert_push(db: Session, event: AlertEvent, target: AlertTarget) -> dict:
    tokens = list(db.scalars(select(DeviceToken).where(DeviceToken.enabled.is_(True))))
    if not tokens:
        return {"sent": 0, "reason": "no-devices"}
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not credential_path:
                return {"sent": 0, "reason": "firebase-not-configured"}
            firebase_admin.initialize_app(credentials.Certificate(credential_path))
        message = messaging.MulticastMessage(
            tokens=[item.token for item in tokens],
            notification=messaging.Notification(title=event.title, body=event.message),
            data={
                "type": "availability_alert",
                "group": target.group_name,
                "target": target.slug,
                "status": target.status,
                "route": "/alerts",
            },
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(sound="default"),
            ),
        )
        result = messaging.send_each_for_multicast(message)
        for index, response in enumerate(result.responses):
            if not response.success and response.exception and any(
                marker in str(response.exception).lower()
                for marker in ("unregistered", "not found", "invalid argument")
            ):
                tokens[index].enabled = False
        db.commit()
        return {"sent": result.success_count, "failed": result.failure_count}
    except Exception as exc:
        return {"sent": 0, "reason": str(exc)[:300]}


def parse_decimal_amount(raw: str) -> Decimal:
    compact = raw.replace(" ", "")
    if "," in compact and "." in compact:
        decimal_separator = "," if compact.rfind(",") > compact.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        compact = compact.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif "," in compact:
        compact = compact.replace(".", "").replace(",", ".")
    return Decimal(compact)


def parse_outgoing_transfer_details(
    title: str | None, body: str
) -> tuple[str | None, str | None]:
    text_value = f"{title or ''} {body}"
    match = re.search(
        r"a la cuenta de\s+(.+?)\s+en concepto de\s+(.+?)"
        r"(?:\s+ya ha llegado(?:\s+a su destino)?|[.!]\s*$|$)",
        text_value,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(" ."), match.group(2).strip(" .")
    recipient_match = re.search(
        r"(?:transferencia|envío).{0,160}?\s+a\s+(.+?)(?:[.!]\s*$|$)",
        text_value,
        flags=re.IGNORECASE,
    )
    return (
        recipient_match.group(1).strip(" .") if recipient_match else None,
        None,
    )


def parse_bank_receipt(title: str | None, body: str) -> tuple[Decimal, str, str | None] | None:
    text_value = f"{title or ''} {body}"
    amount_match = re.search(
        r"(?:transferencia|bizum|abono|pago recibido|has recibido|ha recibido|"
        r"compra|pago realizado|has hecho un pago|has hecho una compra)"
        r".{0,180}?(?:de\s+)?(\d[\d., ]*)\s*(euros?|eur|usd|cup|mlc)\b",
        text_value,
        flags=re.IGNORECASE,
    )
    if not amount_match:
        return None
    amount = parse_decimal_amount(amount_match.group(1))
    currency_label = amount_match.group(2).upper()
    currency = "EUR" if currency_label.startswith("EURO") else currency_label
    counterparty_match = re.search(
        r"\bde\s+([\wÀ-ÿ][\wÀ-ÿ .'-]{1,100}?)(?:\s+por\b|[.!]\s*$|$)",
        text_value[amount_match.end():],
        flags=re.IGNORECASE,
    )
    counterparty = counterparty_match.group(1).strip() if counterparty_match else None
    outgoing_counterparty, _ = parse_outgoing_transfer_details(title, body)
    if outgoing_counterparty:
        counterparty = outgoing_counterparty
    return amount, currency, counterparty


def is_card_purchase(title: str | None, body: str) -> bool:
    text_value = f"{title or ''} {body}".lower()
    return any(
        marker in text_value
        for marker in (
            "has hecho una compra",
            "compra de",
            "pago realizado",
            "pago con tarjeta",
            "compra con tarjeta",
        )
    )


def is_outgoing_transfer(title: str | None, body: str) -> bool:
    text_value = f"{title or ''} {body}".lower()
    outgoing_markers = (
        "tu transferencia ya ha llegado",
        "transferencia que ordenaste",
        "transferencia realizada",
        "transferencia enviada",
        "transferencia emitida",
        "has enviado",
        "enviaste",
    )
    return any(marker in text_value for marker in outgoing_markers)


def is_bizum(title: str | None, body: str) -> bool:
    return "bizum" in f"{title or ''} {body}".lower()


def is_ing_bank_operation(package_name: str, title: str | None, body: str) -> bool:
    normalized_package = package_name.lower().strip()
    normalized_title = (title or "").lower().strip()
    is_ing = normalized_package in {"www.ingdirect.nativeframe", "com.ing.mobile"} or normalized_title == "ing"
    if not is_ing:
        return False
    text_value = f"{title or ''} {body}".lower()
    return any(
        marker in text_value
        for marker in (
            "transferencia",
            "bizum",
            "has recibido",
            "ha recibido",
            "ingreso",
            "abono",
            "pago",
            "pagado",
            "compra",
            "cargo",
            "recibo",
        )
    )


def notification_share_allowed(db: Session, payload: NotificationIn) -> bool:
    text_value = f"{payload.title or ''} {payload.body}".lower()
    allowed = True
    rules = db.scalars(select(NotificationRule).where(NotificationRule.enabled.is_(True)))
    for rule in rules:
        package_matches = not rule.package_name or rule.package_name.lower() == payload.package_name.lower()
        text_matches = rule.text_contains.lower() in text_value
        if not package_matches or not text_matches:
            continue
        if rule.action in {"exclude_share", "private", "drop"}:
            allowed = False
        elif rule.action in {"include_share", "share"}:
            allowed = True
    return allowed


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "version": app.version, "database": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {str(exc)[:120]}")


@app.post("/api/auth/enroll", response_model=EnrollOut)
def enroll_device(payload: EnrollIn):
    admin_code = os.getenv("ADMIN_ENROLLMENT_CODE", "")
    member_code = os.getenv("MEMBER_ENROLLMENT_CODE", "")
    capture_code = os.getenv("CAPTURE_ENROLLMENT_CODE", "")
    role = None
    for candidate, candidate_role in (
        (admin_code, "admin"),
        (member_code, "member"),
        (capture_code, "capture"),
    ):
        if candidate and hmac.compare_digest(payload.code, candidate):
            role = candidate_role
            break
    if role is None:
        raise HTTPException(status_code=401, detail="Código de activación inválido")
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        credential = ApiCredential(
            token_hash=token_hash(raw_token),
            label=payload.device_name,
            role=role,
            enabled=True,
            created_at=now,
            last_seen_at=now,
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)
        return EnrollOut(access_token=raw_token, credential=credential)


@app.get("/api/auth/me")
def auth_me(principal: Principal = Depends(auth)):
    return {
        "id": principal.credential_id,
        "label": principal.label,
        "role": principal.role,
        "permissions": sorted(principal.permissions),
        "legacy": principal.legacy,
    }


@app.get(
    "/api/auth/devices",
    response_model=list[CredentialOut],
    dependencies=[Depends(require_permission("devices"))],
)
def list_credentials():
    with SessionLocal() as db:
        return list(db.scalars(select(ApiCredential).order_by(ApiCredential.created_at.desc())))


@app.post(
    "/api/auth/devices/{credential_id}/revoke",
    dependencies=[Depends(require_permission("devices"))],
)
def revoke_credential(credential_id: int):
    with SessionLocal() as db:
        credential = db.get(ApiCredential, credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="device not found")
        credential.enabled = False
        credential.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return {"revoked": True, "id": credential.id}


@app.post(
    "/api/notifications",
    response_model=NotificationOut,
    dependencies=[Depends(require_permission("capture"))],
)
def create_notification(payload: NotificationIn):
    if not is_ing_bank_operation(payload.package_name, payload.title, payload.body):
        return Response(status_code=204)
    with SessionLocal() as db:
        if payload.external_id:
            existing = db.scalar(
                select(Notification).where(Notification.external_id == payload.external_id)
            )
            if existing:
                return existing
        parsed = parse_bank_receipt(payload.title, payload.body)
        purchase = is_card_purchase(payload.title, payload.body)
        outgoing_transfer = is_outgoing_transfer(payload.title, payload.body)
        bizum = is_bizum(payload.title, payload.body)
        outgoing = outgoing_transfer or purchase
        share_allowed = notification_share_allowed(db, payload)
        values = payload.model_dump(exclude={"received_at"}, exclude_none=True)
        values["shared_with_family"] = share_allowed
        if parsed:
            amount, currency, counterparty = parsed
            signed_amount = -amount if outgoing else amount
            values.update(
                parsed_amount=signed_amount,
                currency=currency,
                counterparty=payload.counterparty or counterparty,
                category=(
                    "transfer"
                    if outgoing_transfer
                    else "expense"
                    if purchase
                    else "income"
                ),
            )
        item = Notification(
            **values,
            received_at=payload.received_at or datetime.now(timezone.utc),
            synced_at=datetime.now(timezone.utc),
        )
        db.add(item)
        db.flush()
        if parsed and currency == "EUR":
            amount, currency, counterparty = parsed
            signed_amount = -amount if outgoing else amount
            kind = "transfer" if outgoing_transfer else "expense" if purchase else "income"
            _, transfer_concept = parse_outgoing_transfer_details(
                payload.title, payload.body
            )
            description = (
                f"{'Bizum enviado' if bizum else 'Transferencia bancaria realizada'}"
                f"{f' a {counterparty}' if counterparty else ''}"
                f"{f' · {transfer_concept}' if transfer_concept else ''}"
                if outgoing_transfer
                else "Compra con tarjeta"
                if purchase
                else (
                    f"{'Bizum' if bizum else 'Transferencia bancaria'} recibido"
                    f"{f' de {counterparty}' if counterparty else ''}"
                )
            )
            db.add(
                BalanceEntry(
                    amount=signed_amount,
                    description=description,
                    created_at=item.received_at,
                    notification_id=item.id,
                    kind=kind,
                    category=kind,
                    member="me" if purchase else "cousin",
                    currency=currency,
                    is_business=False,
                )
            )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if payload.external_id:
                existing = db.scalar(
                    select(Notification).where(Notification.external_id == payload.external_id)
                )
                if existing:
                    return existing
            raise
        db.refresh(item)
        if parsed and share_allowed:
            _, transfer_concept = parse_outgoing_transfer_details(
                payload.title, payload.body
            )
            description = (
                f"{'Bizum enviado' if bizum else 'Transferencia bancaria realizada'}"
                f"{f' a {counterparty}' if counterparty else ''}"
                f"{f' · {transfer_concept}' if transfer_concept else ''}"
                if outgoing_transfer
                else "Compra con tarjeta"
                if purchase
                else (
                    f"{'Bizum' if bizum else 'Transferencia bancaria'} recibido"
                    f"{f' de {counterparty}' if counterparty else ''}"
                )
            )
            affected_member = "me" if purchase else "cousin"
            balance_text = balance_message(db, [affected_member], currency)
            if purchase:
                event_type = "balance_changed"
                message = (
                    f"🧾 Utilitaria · Compra con tarjeta\n"
                    f"Importe: {amount:.2f} {currency}\n"
                    f"{balance_text}"
                )
            elif outgoing_transfer:
                event_type = "transfer_sent"
                details = []
                if counterparty:
                    details.append(f"Destinatario: {counterparty}")
                if transfer_concept:
                    details.append(f"Concepto: {transfer_concept}")
                detail_text = f"\n{'\n'.join(details)}" if details else ""
                message = (
                    f"{'📲' if bizum else '📤'} Utilitaria · "
                    f"{'Bizum enviado' if bizum else 'Transferencia bancaria realizada'}\n"
                    f"Medio: {'Bizum' if bizum else 'Transferencia bancaria'}\n"
                    f"Importe: {amount:.2f} {currency}{detail_text}\n"
                    f"{balance_text}"
                )
            else:
                event_type = "transfer_received"
                sender_text = f"\nDe: {counterparty}" if counterparty else ""
                message = (
                    f"{'📲' if bizum else '💰'} Utilitaria · "
                    f"{'Bizum recibido' if bizum else 'Transferencia bancaria recibida'}\n"
                    f"Medio: {'Bizum' if bizum else 'Transferencia bancaria'}\n"
                    f"Importe: {amount:.2f} {currency}{sender_text}\n"
                    f"{balance_text}"
                )
            notify_whatsapp(
                db,
                event_type,
                message,
                dedupe_key=f"notification:{item.id}:{event_type}",
            )
        return item


@app.get("/api/notifications", response_model=list[NotificationOut], dependencies=[Depends(require_permission("read"))])
def list_notifications(limit: int = 100):
    with SessionLocal() as db:
        candidates = list(
            db.scalars(
                select(Notification)
                .order_by(Notification.received_at.desc())
                .limit(500)
            )
        )
        return [
            item
            for item in candidates
            if is_ing_bank_operation(item.package_name, item.title, item.body)
        ][: min(limit, 500)]


@app.patch(
    "/api/notifications/{notification_id}",
    response_model=NotificationOut,
    dependencies=[Depends(require_permission("write"))],
)
def update_notification(notification_id: int, payload: NotificationPatch):
    with SessionLocal() as db:
        item = db.get(Notification, notification_id)
        if not item:
            raise HTTPException(status_code=404, detail="notification not found")
        for key, value in payload.model_dump(exclude_none=True).items():
            setattr(item, key, value)
        linked_entry = db.scalar(
            select(BalanceEntry).where(BalanceEntry.notification_id == notification_id)
        )
        if linked_entry:
            if payload.is_business is not None:
                linked_entry.is_business = payload.is_business
            if payload.shared_with_family is not None:
                linked_entry.member = "shared" if payload.shared_with_family else "me"
            if payload.category is not None:
                linked_entry.category = payload.category
        db.commit()
        db.refresh(item)
        return item


@app.post(
    "/api/balance/entries",
    response_model=BalanceOut,
    dependencies=[Depends(require_permission("write"))],
)
def add_balance_entry(payload: BalanceIn):
    with SessionLocal() as db:
        if payload.external_id:
            existing = db.scalar(
                select(BalanceEntry).where(BalanceEntry.external_id == payload.external_id)
            )
            if existing:
                return existing
        values = payload.model_dump(exclude={"created_at"}, exclude_none=True)
        values["amount"] = normalized_balance_amount(
            payload.amount, payload.kind, payload.category
        )
        item = BalanceEntry(
            **values,
            created_at=payload.created_at or datetime.now(timezone.utc),
        )
        db.add(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if payload.external_id:
                existing = db.scalar(
                    select(BalanceEntry).where(BalanceEntry.external_id == payload.external_id)
                )
                if existing:
                    return existing
            raise
        db.refresh(item)
        if not item.is_business:
            outgoing = item.amount < 0
            if item.kind == "transfer":
                event_type = "transfer_sent" if outgoing else "transfer_received"
                icon = "📤" if outgoing else "💰"
                title = "Transferencia realizada" if outgoing else "Transferencia recibida"
            elif item.amount < 0:
                event_type = "balance_changed"
                icon = "🧾"
                title = "Gasto"
            else:
                event_type = "balance_changed"
                icon = "💰"
                title = "Ingreso"
            notify_whatsapp(
                db,
                event_type,
                f"{icon} Utilitaria · {title}\n"
                f"Importe: {abs(item.amount):.2f} {item.currency}\n"
                f"Descripción: {item.description or 'Movimiento manual'}\n"
                f"{balance_message(db, [item.member], item.currency)}",
                dedupe_key=f"balance:{item.id}:unified",
            )
        return item


@app.post(
    "/api/balance/transfers",
    response_model=list[BalanceOut],
    dependencies=[Depends(require_permission("write"))],
)
def create_member_transfer(payload: BalanceTransferIn):
    if payload.from_member == payload.to_member:
        raise HTTPException(status_code=400, detail="Los participantes deben ser distintos")
    with SessionLocal() as db:
        timestamp = payload.created_at or datetime.now(timezone.utc)
        transfer_group_id = str(uuid.uuid4())
        debit = BalanceEntry(
            amount=-payload.amount,
            description=f"{payload.description} · sale de {member_name(payload.from_member)}",
            created_at=timestamp,
            kind="member_transfer",
            category="member_transfer",
            member=payload.from_member,
            currency=payload.currency,
            is_business=False,
            transfer_group_id=transfer_group_id,
        )
        credit = BalanceEntry(
            amount=payload.amount,
            description=f"{payload.description} · entra a {member_name(payload.to_member)}",
            created_at=timestamp,
            kind="member_transfer",
            category="member_transfer",
            member=payload.to_member,
            currency=payload.currency,
            is_business=False,
            transfer_group_id=transfer_group_id,
        )
        db.add_all([debit, credit])
        db.commit()
        db.refresh(debit)
        db.refresh(credit)
        notify_whatsapp(
            db,
            "balance_changed",
            f"🔄 Utilitaria · Ajuste entre personas\n{payload.amount:.2f} {payload.currency}\n"
            f"{member_name(payload.from_member)} → {member_name(payload.to_member)}\n"
            f"{balance_message(db, [payload.from_member, payload.to_member], payload.currency)}\n"
            f"Motivo: {payload.description}",
            dedupe_key=f"member-transfer:{transfer_group_id}",
        )
        return [debit, credit]


@app.patch(
    "/api/balance/transfers/{transfer_group_id}",
    response_model=list[BalanceOut],
    dependencies=[Depends(require_permission("write"))],
)
def update_member_transfer(transfer_group_id: str, payload: BalanceTransferPatch):
    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(BalanceEntry).where(BalanceEntry.transfer_group_id == transfer_group_id)
            )
        )
        if len(rows) != 2:
            raise HTTPException(status_code=404, detail="linked transfer not found")
        debit = next((row for row in rows if row.amount < 0), None)
        credit = next((row for row in rows if row.amount > 0), None)
        if not debit or not credit:
            raise HTTPException(status_code=409, detail="linked transfer is inconsistent")
        amount = payload.amount if payload.amount is not None else abs(debit.amount)
        from_member = payload.from_member or debit.member
        to_member = payload.to_member or credit.member
        if from_member == to_member:
            raise HTTPException(status_code=400, detail="Los participantes deben ser distintos")
        description = payload.description or debit.description.split(" · sale de ", 1)[0]
        debit.amount = -amount
        debit.member = from_member
        debit.description = f"{description} · sale de {member_name(from_member)}"
        credit.amount = amount
        credit.member = to_member
        credit.description = f"{description} · entra a {member_name(to_member)}"
        if payload.created_at is not None:
            debit.created_at = payload.created_at
            credit.created_at = payload.created_at
        db.commit()
        db.refresh(debit)
        db.refresh(credit)
        notify_whatsapp(
            db,
            "balance_changed",
            f"🔄 Utilitaria · Ajuste actualizado\n{amount:.2f} {debit.currency}\n"
            f"{member_name(from_member)} → {member_name(to_member)}\n"
            f"{balance_message(db, [from_member, to_member], debit.currency)}\n"
            f"Motivo: {description}",
            dedupe_key=f"member-transfer:{transfer_group_id}:update:{uuid.uuid4()}",
        )
        return [debit, credit]


@app.get("/api/balance", dependencies=[Depends(require_permission("read"))])
def current_balance():
    with SessionLocal() as db:
        rows = db.scalars(
            select(BalanceEntry).where(
                BalanceEntry.is_business.is_(False),
                BalanceEntry.currency == "EUR",
            )
        )
        total = sum((row.amount for row in rows), Decimal("0.00"))
        return {"amount": total, "currency": "EUR"}


@app.get("/api/balance/entries", response_model=list[BalanceOut], dependencies=[Depends(require_permission("read"))])
def list_balance_entries(limit: int = 200):
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(BalanceEntry)
                .order_by(BalanceEntry.created_at.desc(), BalanceEntry.id.desc())
                .limit(min(limit, 500))
            )
        )


@app.patch(
    "/api/balance/entries/{entry_id}",
    response_model=BalanceOut,
    dependencies=[Depends(require_permission("write"))],
)
def update_balance_entry(entry_id: int, payload: BalancePatch):
    with SessionLocal() as db:
        item = db.get(BalanceEntry, entry_id)
        if not item:
            raise HTTPException(status_code=404, detail="balance entry not found")
        if item.transfer_group_id or item.kind == "member_transfer":
            raise HTTPException(
                status_code=409,
                detail="Los ajustes entre personas deben editarse como una operación vinculada",
            )
        changes = payload.model_dump(exclude_none=True)
        future_kind = changes.get("kind", item.kind)
        future_category = changes.get("category", item.category)
        if "amount" in changes or "kind" in changes or "category" in changes:
            changes["amount"] = normalized_balance_amount(
                changes.get("amount", item.amount), future_kind, future_category
            )
        for key, value in changes.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item


@app.delete(
    "/api/balance/entries/{entry_id}",
    status_code=204,
    dependencies=[Depends(require_permission("write"))],
)
def delete_balance_entry(entry_id: int):
    with SessionLocal() as db:
        item = db.get(BalanceEntry, entry_id)
        if not item:
            raise HTTPException(status_code=404, detail="balance entry not found")
        if item.transfer_group_id or item.kind == "member_transfer":
            raise HTTPException(
                status_code=409,
                detail="Los ajustes entre personas deben eliminarse como una operación vinculada",
            )
        db.delete(item)
        db.commit()
        return Response(status_code=204)


@app.delete(
    "/api/balance/transfers/{transfer_group_id}",
    status_code=204,
    dependencies=[Depends(require_permission("write"))],
)
def delete_member_transfer(transfer_group_id: str):
    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(BalanceEntry).where(
                    BalanceEntry.transfer_group_id == transfer_group_id
                )
            )
        )
        if len(rows) != 2:
            raise HTTPException(status_code=404, detail="linked transfer not found")
        for row in rows:
            db.delete(row)
        db.commit()
        return Response(status_code=204)


@app.get("/api/finance/summary", dependencies=[Depends(require_permission("read"))])
def finance_summary():
    with SessionLocal() as db:
        rows = list(db.scalars(select(BalanceEntry).order_by(BalanceEntry.created_at.desc())))
        eur_rows = [row for row in rows if row.currency == "EUR"]
        total = sum((row.amount for row in eur_rows if not row.is_business), Decimal("0.00"))
        business = sum((row.amount for row in eur_rows if row.is_business), Decimal("0.00"))
        by_category: dict[str, Decimal] = {}
        by_member: dict[str, Decimal] = {
            "me": Decimal("0.00"),
            "cousin": Decimal("0.00"),
            "shared": Decimal("0.00"),
        }
        by_currency: dict[str, Decimal] = {}
        for row in rows:
            if not row.is_business:
                by_currency[row.currency] = by_currency.get(row.currency, Decimal("0.00")) + row.amount
            if row.currency != "EUR":
                continue
            by_category[row.category] = by_category.get(row.category, Decimal("0.00")) + row.amount
            if not row.is_business:
                member = row.member if row.member in by_member else "shared"
                by_member[member] += row.amount
        return {
            "balance": total,
            "business": business,
            "entries": len(rows),
            "by_category": by_category,
            "by_member": by_member,
            "by_currency": by_currency,
            "currency": "EUR",
        }


@app.post(
    "/api/notification-rules",
    response_model=RuleOut,
    dependencies=[Depends(require_permission("settings"))],
)
def create_rule(payload: RuleIn):
    with SessionLocal() as db:
        item = NotificationRule(**payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return item


@app.get(
    "/api/notification-rules",
    response_model=list[RuleOut],
    dependencies=[Depends(require_permission("settings"))],
)
def list_rules():
    with SessionLocal() as db:
        return list(db.scalars(select(NotificationRule).order_by(NotificationRule.id.desc())))


@app.get("/api/solar/catalog", dependencies=[Depends(require_permission("read"))])
async def solar_catalog():
    base_url = (os.getenv("TIENDASOLAR_BASE_URL") or "https://solar.eav-labs.com").rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{base_url}/api/catalog")
    response.raise_for_status()
    return response.json()


@app.get("/api/solar/image", dependencies=[Depends(require_permission("read"))])
async def solar_image(url: str):
    parsed = urlparse(url)
    allowed_hosts = {
        "tiendasolar.com",
        "www.tiendasolar.com",
        "solar.eav-labs.com",
        "www.solar.eav-labs.com",
    }
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed_hosts:
        raise HTTPException(status_code=400, detail="Origen de imagen no permitido")
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "Utilitaria/0.8"})
    response.raise_for_status()
    media_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
    return Response(
        content=response.content,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/alerts", dependencies=[Depends(require_permission("read"))])
def list_alerts():
    with SessionLocal() as db:
        targets = seed_alert_targets(db)
        events = list(
            db.scalars(select(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(30))
        )
        return {
            "groups": [
                {
                    "id": group,
                    "label": "Gas" if group == "gas" else "TiendaSolar",
                    "items": [serialize_alert_target(item) for item in targets if item.group_name == group],
                }
                for group in ("gas", "solar")
            ],
            "events": [
                {
                    "id": item.id,
                    "target_id": item.target_id,
                    "previous_status": item.previous_status,
                    "status": item.status,
                    "title": item.title,
                    "message": item.message,
                    "created_at": item.created_at,
                    "details": item.details or {},
                }
                for item in events
            ],
        }


async def check_alert_target(db: Session, target: AlertTarget) -> dict:
    from app.alerts import CHECKERS

    if not target.enabled or target.slug not in CHECKERS:
        raise HTTPException(status_code=404, detail="alert target not available")
    try:
        result = await CHECKERS[target.slug]()
        checked_at = datetime.now(timezone.utc)
        previous_status = target.status
        changed = target.fingerprint is not None and target.fingerprint != result["fingerprint"]
        target.status = result["status"]
        target.status_label = result["status_label"]
        target.price = result.get("price")
        target.fingerprint = result["fingerprint"]
        target.details = result.get("details") or {}
        target.last_checked_at = checked_at
        target.last_error = None
        push_result = None
        if changed:
            target.last_changed_at = checked_at
            if target.group_name == "gas" and target.status == "available":
                title = "¡Hay bombonas de gas disponibles!"
            elif target.group_name == "gas":
                title = "Cambió el estado de la bombona de gas"
            else:
                title = "Cambios en TiendaSolar"
            message = f"{target.name}: {target.status_label}"
            event = AlertEvent(
                target_id=target.id,
                previous_status=previous_status,
                status=target.status,
                title=title,
                message=message,
                created_at=checked_at,
                details=target.details,
            )
            db.add(event)
            db.flush()
            push_result = send_alert_push(db, event, target)
        db.commit()
        return {
            "slug": target.slug,
            "ok": True,
            "changed": changed,
            "checked_at": checked_at,
            "push": push_result,
        }
    except Exception as exc:
        checked_at = datetime.now(timezone.utc)
        target.last_checked_at = checked_at
        target.last_error = str(exc)[:1000]
        db.commit()
        return {
            "slug": target.slug,
            "ok": False,
            "checked_at": checked_at,
            "error": target.last_error,
        }


@app.post("/api/alerts/check", dependencies=[Depends(require_permission("settings"))])
async def check_alerts():
    results = []
    with SessionLocal() as db:
        targets = seed_alert_targets(db)
        for target in targets:
            if not target.enabled:
                continue
            results.append(await check_alert_target(db, target))
    return {"checked_at": datetime.now(timezone.utc), "results": results}


@app.post(
    "/api/alerts/{slug}/check",
    dependencies=[Depends(require_permission("settings"))],
)
async def check_single_alert(slug: str):
    with SessionLocal() as db:
        seed_alert_targets(db)
        target = db.scalar(select(AlertTarget).where(AlertTarget.slug == slug))
        if not target:
            raise HTTPException(status_code=404, detail="alert target not found")
        return await check_alert_target(db, target)


@app.post("/api/devices/register", dependencies=[Depends(require_permission("read"))])
def register_device(payload: DeviceTokenIn):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        item = db.scalar(select(DeviceToken).where(DeviceToken.token == payload.token))
        if item:
            item.name = payload.name
            item.enabled = True
            item.last_seen_at = now
        else:
            item = DeviceToken(
                token=payload.token,
                name=payload.name,
                enabled=True,
                created_at=now,
                last_seen_at=now,
            )
            db.add(item)
        db.commit()
        return {"registered": True, "id": item.id}


@app.get("/api/rates/eltoque", dependencies=[Depends(require_permission("read"))])
async def eltoque_rates():
    global _eltoque_cache
    page_url = os.getenv("ELTOQUE_PAGE_URL", "https://eltoque.com/tasas-de-cambio-cuba")
    cache_minutes = int(os.getenv("ELTOQUE_CACHE_MINUTES", "15"))
    now = datetime.now(timezone.utc)

    if _eltoque_cache:
        cached_at = _eltoque_cache.get("fetched_at")
        if isinstance(cached_at, datetime) and (now - cached_at).total_seconds() < cache_minutes * 60:
            return {**_eltoque_cache, "cached": True}

    errors: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(
                page_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                    "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Mobile Safari/537.36",
                },
            )
            response.raise_for_status()
        page_text = html.unescape(re.sub(r"<[^>]+>", " ", response.text))
        page_text = re.sub(r"\s+", " ", page_text)
        section_match = re.search(
            r"Mercado Informal de Divisas en Cuba\s*\(Tiempo Real\)(.*?)"
            r"Los valores de REFERENCIA",
            page_text,
            flags=re.IGNORECASE,
        )
        if not section_match:
            raise ValueError("no se encontró el bloque del mercado informal")
        market_text = section_match.group(1)
        currencies = {
            "USD": "Dólar estadounidense",
            "EUR": "Euro",
            "MLC": "Saldo en cuenta bancaria",
            "CAD": "Dólar canadiense",
            "MXN": "Peso mexicano",
            "ZELLE": "Zelle",
            "CLA": "Clásica",
        }
        rates: dict[str, float] = {}
        items: list[dict] = []
        for currency, name in currencies.items():
            match = re.search(
                rf"\b{currency}\b.{{0,120}}?(\d{{2,}}(?:[.,]\d{{1,2}})?)\s*CUP"
                rf"\s*([+-]\s*\d+(?:[.,]\d{{1,2}})?)?",
                market_text,
                flags=re.IGNORECASE,
            )
            if match:
                value = float(match.group(1).replace(",", "."))
                change = (
                    float(match.group(2).replace(" ", "").replace(",", "."))
                    if match.group(2)
                    else 0.0
                )
                rates[currency] = value
                items.append(
                    {
                        "code": currency,
                        "name": name,
                        "unit": f"1 {currency}",
                        "value": value,
                        "quote": "CUP",
                        "change": change,
                        "trend": "up" if change > 0 else "down" if change < 0 else "flat",
                    }
                )
        if not rates:
            raise ValueError("no se encontraron tasas en el HTML de elTOQUE")
        updated_match = re.search(
            r"(\d{1,2}\s+de\s+[a-záéíóúñ]+\s+de\s+\d{4}\s+a\s+las\s+"
            r"\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?)",
            page_text,
            flags=re.IGNORECASE,
        )
        _eltoque_cache = {
            "source": "eltoque-html",
            "source_url": page_url,
            "fetched_at": now,
            "market": "Mercado Informal de Divisas en Cuba",
            "subtitle": "Tiempo Real",
            "source_updated_at": updated_match.group(1) if updated_match else None,
            "rates": rates,
            "items": items,
            "cached": False,
        }
        return _eltoque_cache
    except Exception as exc:
        errors.append(f"scraping: {exc}")

    api_key = os.getenv("ELTOQUE_API_KEY")
    if api_key:
        try:
            api_url = os.getenv("ELTOQUE_API_URL", "https://tasas.eltoque.com/v1/trmi")
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    api_url,
                    headers={"X-API-Key": api_key, "Accept": "application/json"},
                )
                response.raise_for_status()
            return {
                "source": "eltoque-api",
                "source_url": api_url,
                "fetched_at": now,
                "rates": response.json(),
                "cached": False,
            }
        except Exception as exc:
            errors.append(f"api: {exc}")

    if _eltoque_cache:
        return {**_eltoque_cache, "cached": True, "stale": True, "warning": "; ".join(errors)}
    raise HTTPException(status_code=503, detail="No se pudieron obtener las tasas de elTOQUE: " + "; ".join(errors))


WHATSAPP_DEFAULT_GROUP = "120363420329472237@g.us"


def get_whatsapp_config(db: Session) -> WhatsAppConfig:
    config = db.get(WhatsAppConfig, 1)
    if config:
        return config
    config = WhatsAppConfig(
        id=1,
        recipients=[WHATSAPP_DEFAULT_GROUP],
        updated_at=datetime.now(timezone.utc),
    )
    db.add(config)
    db.flush()
    return config


def send_openwa_text(to: str, message: str) -> dict:
    base_url = os.getenv("OPENWA_BASE_URL")
    token = os.getenv("OPENWA_TOKEN") or os.getenv("API_MASTER_KEY")
    session_id = os.getenv("OPENWA_SESSION_ID")
    if not base_url or not token or not session_id:
        raise HTTPException(status_code=503, detail="OpenWA is not configured")
    phone = re.sub(r"\D", "", to)
    chat_id = to if "@" in to else f"{phone}@c.us"
    with httpx.Client(timeout=20) as client:
        response = client.post(
            f"{base_url.rstrip('/')}/api/sessions/{session_id}/messages/send-text",
            headers={"X-API-Key": token},
            json={"chatId": chat_id, "text": message},
        )
    response.raise_for_status()
    return {"sent": True, "provider_response": response.json()}


def notify_whatsapp(
    db: Session,
    event_type: str,
    message: str,
    dedupe_key: str | None = None,
) -> dict:
    config = get_whatsapp_config(db)
    enabled = {
        "transfer_received": config.transfer_received,
        "transfer_sent": config.transfer_sent,
        "balance_changed": config.balance_changes,
    }.get(event_type, False)
    recipients = [str(item).strip() for item in (config.recipients or []) if str(item).strip()]
    if not config.enabled or not enabled or not recipients:
        return {"sent": 0, "skipped": True}
    queued = 0
    for recipient in recipients:
        recipient_key = f"{dedupe_key}:{recipient}" if dedupe_key else None
        if recipient_key and db.scalar(
            select(WhatsAppOutbox).where(WhatsAppOutbox.dedupe_key == recipient_key)
        ):
            continue
        db.add(
            WhatsAppOutbox(
                event_type=event_type,
                recipient=recipient,
                message=message,
                dedupe_key=recipient_key,
                status="pending",
                attempts=0,
                next_attempt_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
        )
        queued += 1
    db.commit()
    return {"queued": queued, "skipped": queued == 0}


def process_whatsapp_outbox_once(limit: int = 20) -> dict:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        jobs = list(
            db.scalars(
                select(WhatsAppOutbox)
                .where(
                    WhatsAppOutbox.status.in_(["pending", "retry"]),
                    WhatsAppOutbox.next_attempt_at <= now,
                )
                .order_by(WhatsAppOutbox.id)
                .limit(limit)
            )
        )
        sent = 0
        failed = 0
        for job in jobs:
            job.status = "processing"
            job.attempts += 1
            db.commit()
            try:
                send_openwa_text(job.recipient, job.message)
                job.status = "sent"
                job.sent_at = datetime.now(timezone.utc)
                job.last_error = None
                sent += 1
            except Exception as exc:
                job.last_error = str(exc)[:1000]
                if job.attempts >= 8:
                    job.status = "failed"
                else:
                    job.status = "retry"
                    delay_seconds = min(3600, 15 * (2 ** (job.attempts - 1)))
                    job.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                failed += 1
            db.commit()
        return {"processed": len(jobs), "sent": sent, "failed": failed}


@app.get(
    "/api/whatsapp/config",
    response_model=WhatsAppConfigOut,
    dependencies=[Depends(require_permission("settings"))],
)
def whatsapp_config():
    with SessionLocal() as db:
        config = get_whatsapp_config(db)
        db.commit()
        db.refresh(config)
        return config


@app.patch(
    "/api/whatsapp/config",
    response_model=WhatsAppConfigOut,
    dependencies=[Depends(require_permission("settings"))],
)
def update_whatsapp_config(payload: WhatsAppConfigIn):
    with SessionLocal() as db:
        config = get_whatsapp_config(db)
        config.recipients = [item.strip() for item in payload.recipients if item.strip()]
        config.enabled = payload.enabled
        config.transfer_received = payload.transfer_received
        config.transfer_sent = payload.transfer_sent
        config.balance_changes = payload.balance_changes
        config.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(config)
        return config


@app.post("/api/whatsapp/test", dependencies=[Depends(require_permission("settings"))])
def test_whatsapp(payload: WhatsAppTestIn):
    with SessionLocal() as db:
        result = notify_whatsapp(
            db,
            "balance_changed",
            payload.message,
            dedupe_key=f"test:{uuid.uuid4()}",
        )
        return {"queued": result.get("queued", 0)}


@app.get(
    "/api/whatsapp/outbox",
    response_model=list[WhatsAppOutboxOut],
    dependencies=[Depends(require_permission("settings"))],
)
def whatsapp_outbox(limit: int = 100):
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(WhatsAppOutbox)
                .order_by(WhatsAppOutbox.created_at.desc())
                .limit(min(limit, 500))
            )
        )


@app.post("/api/whatsapp/send", dependencies=[Depends(require_permission("settings"))])
def send_whatsapp(to: str, message: str):
    with SessionLocal() as db:
        job = WhatsAppOutbox(
            event_type="manual",
            recipient=to,
            message=message,
            status="pending",
            attempts=0,
            next_attempt_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        return {"queued": True, "id": job.id}
