#!/usr/bin/env python3
"""Importa el extracto ING entregado por el usuario desde el 17/09/2026."""

from __future__ import annotations

import json
from pathlib import Path
import urllib.request


SOURCE_ID = "1kaKIFgbD0xiJtXM2s8R4OibXLWqSE7si"
API_URL = "https://utilitaria-api.eav-labs.com"

# Orden del extracto (más reciente primero). La hora no existe en el Excel.
ROWS = [
    (3, "2026-09-26", "Otros ingresos", "Ingreso Bizum", "Bizum recibido de Jany Barrientos Deny Bizum de Jany", 130.00),
    (4, "2026-09-26", "Otros ingresos", "Ingreso Bizum", "Bizum recibido de DEBORA JAMA MALDONADO OCAMPOS Bizum de DEBORA JAMA", 20.00),
    (5, "2026-09-26", "Inversión", "Fondos de inversión", "Pago en DBA*04675 SuenaCU DAVIE US", -23.57),
    (6, "2026-09-25", "Otros gastos", "Transferencias", "Transferencia emitida a TITANES TELECOMUNICACIONES 237294 Movimiento ING", -400.00),
    (7, "2026-09-25", "Otros ingresos", "Ingresos de otras entidades", "Transferencia recibida de DOLORES ALCANTARA TETILLA Jessica Garcia", 105.00),
    (8, "2026-09-24", "Otros ingresos", "Ingreso Bizum", "Bizum recibido de Jany Barrientos Deny Bizum de Jany", 150.00),
    (9, "2026-09-24", "Otros gastos", "Transferencias", "Transferencia emitida a TITANES TELECOMUNICACIONES 237294 Movimiento ING", -900.00),
    (10, "2026-09-23", "Otros ingresos", "Ingresos de otras entidades", "Transferencia recibida .", 110.00),
    (11, "2026-09-23", "Otros ingresos", "Ingresos de otras entidades", "Transferencia recibida Para Vicky", 330.00),
    (12, "2026-09-23", "Otros ingresos", "Ingreso Bizum", "Bizum recibido de SUREIYA GONZALEZ TORRES Sin concepto", 88.00),
    (13, "2026-09-22", "Otros ingresos", "Ingreso Bizum", "Bizum recibido de JOSE LUIS MERINO VILLALOBO Sin concepto", 200.00),
    (14, "2026-09-22", "Otros ingresos", "Ingreso Bizum", "Bizum recibido de GRISMEL AGUILERA GONZALEZ Bizum de Grismel", 10.00),
    (15, "2026-09-22", "Otros ingresos", "Ingreso Bizum", "Bizum recibido de GRISMEL AGUILERA GONZALEZ Bizum de Grismel", 80.00),
    (16, "2026-09-22", "Otros ingresos", "Ingresos de otras entidades", "Transferencia recibida recarga", 160.00),
    (17, "2026-09-22", "Compras", "Compras (otros)", "Pago en AMAZON MKTPL*5R8A728Q0 SEATTLE US", -32.60),
    (18, "2026-09-21", "Compras", "Ropa y complementos", "Pago en DEALTRADE ABEDULES ES", -43.75),
    (19, "2026-09-20", "Otros ingresos", "Ingreso Bizum", "Bizum recibido de LUIS YOAN BATISTA PAEZ Sin concepto", 120.00),
    (20, "2026-09-17", "Otros ingresos", "Ingresos de otras entidades", "Transferencia recibida Para Vicky", 110.00),
]


def read_api_key() -> str:
    env_path = Path(__file__).resolve().parents[1] / "backend" / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("API_KEY="):
            return line.partition("=")[2]
    raise RuntimeError("API_KEY no encontrada")


def main() -> None:
    api_key = read_api_key()
    imported = 0
    business = 0
    common_total = 0.0
    for row, date, source_category, subcategory, description, amount in reversed(ROWS):
        is_business = source_category in {"Compras", "Inversión"}
        category = (
            "purchase" if source_category == "Compras"
            else "investment" if source_category == "Inversión"
            else "income" if amount > 0
            else "expense"
        )
        payload = {
            "amount": amount,
            "description": description,
            "kind": "income" if amount > 0 else "expense",
            "category": category,
            "member": "me" if is_business else "cousin",
            "currency": "EUR",
            "is_business": is_business,
            "created_at": f"{date}T00:00:00+02:00",
            "external_id": f"ing-xlsx:{SOURCE_ID}:row-{row}",
        }
        request = urllib.request.Request(
            f"{API_URL}/api/balance/entries",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "User-Agent": "UtilitariaImporter/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f"Fila {row}: HTTP {response.status}")
            saved = json.load(response)
        if saved.get("member") != payload["member"] or saved.get("is_business") != is_business:
            patch_request = urllib.request.Request(
                f"{API_URL}/api/balance/entries/{saved['id']}",
                data=json.dumps(
                    {"member": payload["member"], "is_business": is_business}
                ).encode(),
                method="PATCH",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": api_key,
                    "User-Agent": "UtilitariaImporter/1.0",
                },
            )
            with urllib.request.urlopen(patch_request, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError(f"Fila {row}: PATCH HTTP {response.status}")
        imported += 1
        business += int(is_business)
        if not is_business:
            common_total += amount
    print(f"imported={imported} business_excluded={business} common_total={common_total:.2f}")


if __name__ == "__main__":
    main()
