from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import html
import json
import os
import re
from html.parser import HTMLParser

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


class _GasProductHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.variations = None
        self.product_class = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "main":
            self.product_class = attrs.get("class", "")
        if tag == "form" and "data-product_variations" in attrs:
            self.variations = json.loads(attrs["data-product_variations"])


def parse_goniogas(page: str) -> dict:
    parser = _GasProductHTML()
    parser.feed(page)
    if parser.variations is not None and not isinstance(parser.variations, list):
        raise ValueError("Goniogas no incluyó los datos de las modalidades")
    if "product-type-variable" in parser.product_class and not parser.variations:
        raise ValueError("Goniogas no incluyó existencias de las modalidades")
    variants = []
    if isinstance(parser.variations, list):
        for variant in parser.variations:
            stock_html = variant.get("availability_html") or ""
            quantity, source = _extract_quantity(stock_html, _clean_text(stock_html))
            # max_qty is an order limit, not necessarily the physical inventory.
            available = (
                variant.get("is_in_stock") is True
                and variant.get("is_purchasable") is not False
                and variant.get("variation_is_active") is not False
                and quantity != 0
            )
            variants.append({
                "id": variant.get("variation_id"),
                "name": " / ".join(str(v) for v in (variant.get("attributes") or {}).values()),
                "available": available,
                "quantity": quantity,
                "quantity_source": source,
                "price": variant.get("display_price"),
            })
        variants.sort(key=lambda item: str(item["id"]))
        available = any(item["available"] for item in variants)
        status = "available" if available else "unavailable"
        quantity = None  # Variants may draw from the same stock; never add them.
        price = " · ".join(
            f"{item['name']}: {item['price']:.2f} €"
            for item in variants if isinstance(item["price"], (int, float))
        ) or None
        labels = [
            f"{item['name']}: " + (
                f"{item['quantity']:g} disponibles" if item['available'] and item['quantity'] is not None
                else "Disponible" if item['available'] else "Sin existencias"
            ) for item in variants
        ]
        label = " · ".join(labels)
        relevant = json.dumps(variants, sort_keys=True, ensure_ascii=False)
        return {
            "status": status, "status_label": label, "price": price,
            "fingerprint": hashlib.sha256(relevant.encode()).hexdigest(),
            "details": {
                "available": available, "quantity": quantity,
                "quantity_label": label, "quantity_source": "modalidades del producto",
                "variants": variants,
            },
        }
    # Scope legacy products to the main content, excluding related products and scripts.
    main = re.search(r"<main\b[^>]*>(.*?)</main>", page, re.I | re.S)
    if main:
        page = re.split(r'<section\b[^>]*class=["\'][^"\']*related', main[1], maxsplit=1, flags=re.I)[0]
    page = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", page, flags=re.I | re.S)
    plain = _clean_text(page)
    quantity, quantity_source = _extract_quantity(page, plain)
    unavailable = bool(re.search(r"\boutofstock\b", parser.product_class, re.I))
    available = bool(re.search(r"\binstock\b", parser.product_class, re.I)) and not unavailable
    if not parser.product_class:
        unavailable = bool(re.search(r"sin existencias|agotado|out-of-stock", plain, re.I))
        available = bool(re.search(r"añadir al carrito|in-stock", plain, re.I)) and not unavailable
    status = "unavailable" if unavailable else "available" if available else "unknown"
    label = "Sin existencias" if unavailable else "Disponible" if available else "Estado no reconocido"
    price_match = re.search(r"(\d+[.,]\d{2})\s*€", plain)
    price = f"{price_match[1]} €" if price_match else None
    quantity_label = f"{quantity:g} unidades" if quantity is not None else None
    if available and quantity_label:
        label += f" · {quantity_label}"
    return {
        "status": status, "status_label": label, "price": price,
        "fingerprint": hashlib.sha256(f"{status}|{price or ''}|{quantity_label or ''}".encode()).hexdigest(),
        "details": {"available": available, "quantity": quantity, "quantity_label": quantity_label, "quantity_source": quantity_source},
    }


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
        if response.status_code == 202:
            raise ValueError("Goniogas devolvió una página de espera; se conserva la última lectura")

    return parse_goniogas(response.text)


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
