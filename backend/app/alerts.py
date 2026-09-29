from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import html
import json
import os
import re

import httpx


GAS_URL = os.getenv(
    "GONIOGAS_PRODUCT_URL",
    "https://goniogas.com/producto/cilindro-de-gas-de-10kg/",
)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _extract_quantity(page: str, plain: str) -> tuple[int | float | None, str | None]:
    """Read the shop's stock quantity when WooCommerce exposes it."""
    patterns = (
        r"(?:stock[_ -]?quantity|inventory[_ -]?quantity|quantity|data-stock|data-quantity)"
        r"\s*[=:]\s*[\"']?(\d+(?:[.,]\d+)?)",
        r"(?:max|maximum)\s*=\s*[\"'](\d+(?:[.,]\d+)?)[\"']",
        r"(\d+(?:[.,]\d+)?)\s*(?:unidades|uds?\.?|disponibles|en stock)",
    )
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, page if index < 2 else plain, re.I)
        if not match:
            continue
        raw = match.group(1).replace(",", ".")
        value = float(raw) if "." in raw else int(raw)
        return value, "página del producto"
    return None, None


async def check_goniogas() -> dict:
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "es-ES,es;q=0.9",
        "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    }
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
        response = await client.get(GAS_URL)
        if response.status_code == 202:
            cookie = re.search(r'''document\.cookie\s*=\s*['\"]([^;'\"]+)''', response.text)
            if cookie:
                name, value = cookie.group(1).split("=", 1)
                client.cookies.set(name, value, domain="goniogas.com", path="/")
                response = await client.get(GAS_URL)
        response.raise_for_status()

    page = response.text
    plain = _clean_text(page)
    quantity, quantity_source = _extract_quantity(page, plain)
    unavailable = bool(re.search(r"\boutofstock\b|sin existencias|agotado", page, re.I))
    available = bool(re.search(r"\binstock\b|añadir al carrito|add_to_cart_button", page, re.I)) and not unavailable
    if unavailable:
        status, label = "unavailable", "Sin existencias"
    elif available:
        status, label = "available", "Disponible"
    else:
        status, label = "unknown", "Estado no reconocido"
    price_match = re.search(r"(\d+[.,]\d{2})\s*€", plain, re.I)
    price = f"{price_match.group(1)} €" if price_match else None
    quantity_label = (
        f"{quantity:g} unidades"
        if isinstance(quantity, float)
        else f"{quantity} unidades"
        if quantity is not None
        else None
    )
    if status == "available" and quantity_label:
        label = f"Disponible · {quantity_label}"
    relevant = f"{status}|{price or ''}|{quantity_label or ''}"
    return {
        "status": status,
        "status_label": label,
        "price": price,
        "fingerprint": hashlib.sha256(relevant.encode()).hexdigest(),
        "details": {
            "available": available,
            "quantity": quantity,
            "quantity_label": quantity_label,
            "quantity_source": quantity_source,
        },
    }


async def check_solar() -> dict:
    base_url = os.getenv("TIENDASOLAR_BASE_URL") or "https://solar.eav-labs.com"
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        response = await client.get(f"{base_url.rstrip('/')}/api/catalog")
        response.raise_for_status()
    catalog = response.json()
    products = catalog.get("products", [])
    snapshot = []
    available_count = 0
    for product in products:
        locations = product.get("locations") or {}
        normalized_locations = {}
        for location, value in sorted(locations.items()):
            normalized_locations[location] = {
                "state": value.get("state"),
                "available": value.get("available"),
                "quantity": value.get("quantity"),
            }
            if value.get("available"):
                available_count += 1
        snapshot.append({
            "id": product.get("id"),
            "prices": product.get("prices") or {},
            "locations": normalized_locations,
        })
    fingerprint = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    monitor = catalog.get("monitor") or {}
    stale = bool(monitor.get("stale"))
    return {
        "status": "degraded" if stale else "active",
        "status_label": "Datos atrasados" if stale else "Monitor activo",
        "price": None,
        "fingerprint": fingerprint,
        "details": {
            "products": len(products),
            "available_locations": available_count,
            "last_success_at": monitor.get("lastSuccessAt") or catalog.get("updatedAt"),
            "catalog_url": f"{base_url.rstrip('/')}/",
        },
    }


CHECKERS = {"gas-10kg-goniogas": check_goniogas, "tiendasolar-catalog": check_solar}
