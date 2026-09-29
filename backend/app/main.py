from datetime import datetime, timezone
from decimal import Decimal
import html
import os
import re
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, JSON, Numeric, String, Text, create_engine, select, text
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
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS kind VARCHAR(30) DEFAULT 'adjustment'",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'other'",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS member VARCHAR(100) DEFAULT 'shared'",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'EUR'",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS is_business BOOLEAN DEFAULT FALSE",
        "ALTER TABLE balance_entries ADD COLUMN IF NOT EXISTS external_id VARCHAR(500)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                # SQLite and older installations may not support every ALTER form.
                pass


ensure_schema()
app = FastAPI(title="Utilitaria API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://utilitaria.eav-labs.com",
        "http://localhost:8125",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

_eltoque_cache: dict[str, object] | None = None


def auth(x_api_key: str | None = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


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
    parsed_amount: Decimal | None = None
    currency: str | None = None


class BalanceIn(BaseModel):
    amount: Decimal = Field(description="Importe positivo o negativo")
    description: str = Field(min_length=1, max_length=500)
    notification_id: int | None = None
    kind: str = "adjustment"
    category: str = "other"
    member: str = "shared"
    currency: str = "EUR"
    is_business: bool = False
    created_at: datetime | None = None
    external_id: str | None = Field(default=None, max_length=500)


class BalanceOut(BalanceIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class BalancePatch(BaseModel):
    amount: Decimal | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    kind: str | None = None
    category: str | None = None
    member: str | None = None
    is_business: bool | None = None


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


def parse_bank_receipt(title: str | None, body: str) -> tuple[Decimal, str, str | None] | None:
    text_value = f"{title or ''} {body}"
    amount_match = re.search(
        r"(?:transferencia|bizum|abono|pago recibido|has recibido|ha recibido)"
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
    return amount, currency, counterparty


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/notifications", response_model=NotificationOut, dependencies=[Depends(auth)])
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
        outgoing = is_outgoing_transfer(payload.title, payload.body)
        values = payload.model_dump(exclude={"received_at"}, exclude_none=True)
        if parsed:
            amount, currency, counterparty = parsed
            signed_amount = -amount if outgoing else amount
            values.update(
                parsed_amount=signed_amount,
                currency=currency,
                counterparty=payload.counterparty or counterparty,
                category="transfer" if outgoing else "income",
            )
        item = Notification(**values, received_at=payload.received_at or datetime.now(timezone.utc))
        db.add(item)
        db.flush()
        if parsed:
            amount, currency, counterparty = parsed
            signed_amount = -amount if outgoing else amount
            kind = "transfer" if outgoing else "income"
            description = (
                "Transferencia realizada"
                if outgoing
                else f"Ingreso recibido{f' de {counterparty}' if counterparty else ''}"
            )
            db.add(
                BalanceEntry(
                    amount=signed_amount,
                    description=description,
                    created_at=item.received_at,
                    notification_id=item.id,
                    kind=kind,
                    category=kind,
                    member="shared" if outgoing else "me",
                    currency=currency,
                    is_business=False,
                )
            )
        db.commit()
        db.refresh(item)
        return item


@app.get("/api/notifications", response_model=list[NotificationOut], dependencies=[Depends(auth)])
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


@app.patch("/api/notifications/{notification_id}", response_model=NotificationOut, dependencies=[Depends(auth)])
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


@app.post("/api/balance/entries", response_model=BalanceOut, dependencies=[Depends(auth)])
def add_balance_entry(payload: BalanceIn):
    with SessionLocal() as db:
        if payload.external_id:
            existing = db.scalar(
                select(BalanceEntry).where(BalanceEntry.external_id == payload.external_id)
            )
            if existing:
                return existing
        values = payload.model_dump(exclude={"created_at"}, exclude_none=True)
        item = BalanceEntry(
            **values,
            created_at=payload.created_at or datetime.now(timezone.utc),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item


@app.get("/api/balance", dependencies=[Depends(auth)])
def current_balance():
    with SessionLocal() as db:
        rows = db.scalars(select(BalanceEntry).where(BalanceEntry.is_business.is_(False)))
        total = sum((row.amount for row in rows), Decimal("0.00"))
        return {"amount": total, "currency": "EUR"}


@app.get("/api/balance/entries", response_model=list[BalanceOut], dependencies=[Depends(auth)])
def list_balance_entries(limit: int = 200):
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(BalanceEntry)
                .order_by(BalanceEntry.created_at.desc(), BalanceEntry.id.desc())
                .limit(min(limit, 500))
            )
        )


@app.patch("/api/balance/entries/{entry_id}", response_model=BalanceOut, dependencies=[Depends(auth)])
def update_balance_entry(entry_id: int, payload: BalancePatch):
    with SessionLocal() as db:
        item = db.get(BalanceEntry, entry_id)
        if not item:
            raise HTTPException(status_code=404, detail="balance entry not found")
        for key, value in payload.model_dump(exclude_none=True).items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item


@app.get("/api/finance/summary", dependencies=[Depends(auth)])
def finance_summary():
    with SessionLocal() as db:
        rows = list(db.scalars(select(BalanceEntry).order_by(BalanceEntry.created_at.desc())))
        total = sum((row.amount for row in rows if not row.is_business), Decimal("0.00"))
        business = sum((row.amount for row in rows if row.is_business), Decimal("0.00"))
        by_category: dict[str, Decimal] = {}
        by_member: dict[str, Decimal] = {
            "me": Decimal("0.00"),
            "cousin": Decimal("0.00"),
            "shared": Decimal("0.00"),
        }
        for row in rows:
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
        }


@app.post("/api/notification-rules", response_model=RuleOut, dependencies=[Depends(auth)])
def create_rule(payload: RuleIn):
    with SessionLocal() as db:
        item = NotificationRule(**payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return item


@app.get("/api/notification-rules", response_model=list[RuleOut], dependencies=[Depends(auth)])
def list_rules():
    with SessionLocal() as db:
        return list(db.scalars(select(NotificationRule).order_by(NotificationRule.id.desc())))


@app.get("/api/solar/catalog", dependencies=[Depends(auth)])
async def solar_catalog():
    base_url = (os.getenv("TIENDASOLAR_BASE_URL") or "https://solar.eav-labs.com").rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{base_url}/api/catalog")
    response.raise_for_status()
    return response.json()


@app.get("/api/solar/image", dependencies=[Depends(auth)])
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


@app.get("/api/alerts", dependencies=[Depends(auth)])
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


@app.post("/api/alerts/check", dependencies=[Depends(auth)])
async def check_alerts():
    from app.alerts import CHECKERS

    results = []
    with SessionLocal() as db:
        targets = seed_alert_targets(db)
        for target in targets:
            if not target.enabled or target.slug not in CHECKERS:
                continue
            checked_at = datetime.now(timezone.utc)
            try:
                result = await CHECKERS[target.slug]()
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
                results.append({"slug": target.slug, "ok": True, "changed": changed, "push": push_result})
            except Exception as exc:
                target.last_checked_at = checked_at
                target.last_error = str(exc)[:1000]
                db.commit()
                results.append({"slug": target.slug, "ok": False, "error": target.last_error})
    return {"checked_at": datetime.now(timezone.utc), "results": results}


@app.post("/api/devices/register", dependencies=[Depends(auth)])
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


@app.get("/api/rates/eltoque", dependencies=[Depends(auth)])
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


@app.post("/api/whatsapp/send", dependencies=[Depends(auth)])
async def send_whatsapp(to: str, message: str):
    base_url = os.getenv("OPENWA_BASE_URL")
    token = os.getenv("OPENWA_TOKEN") or os.getenv("API_MASTER_KEY")
    session_id = os.getenv("OPENWA_SESSION_ID")
    if not base_url or not token or not session_id:
        raise HTTPException(status_code=503, detail="OpenWA is not configured")
    phone = re.sub(r"\D", "", to)
    chat_id = to if "@" in to else f"{phone}@c.us"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/api/sessions/{session_id}/messages/send-text",
            headers={"X-API-Key": token},
            json={"chatId": chat_id, "text": message},
        )
    response.raise_for_status()
    return {"sent": True, "provider_response": response.json()}
