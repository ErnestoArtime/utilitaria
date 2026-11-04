import html
import json

from app.alerts import parse_goniogas, gas_refill_notice


def product(variants):
    data = html.escape(json.dumps(variants), quote=True)
    return (
        '<main class="product instock"><form data-product_variations="'
        + data + '"></form><section class="related"><p class="outofstock">Agotado</p></section></main>'
    )


def variant(name, quantity, price, identifier):
    return {
        "variation_id": identifier, "attributes": {"attribute_tipo-de-compra": name},
        "is_in_stock": quantity > 0, "is_purchasable": True,
        "availability_html": f'<p class="stock">{quantity} disponibles</p>',
        "display_price": price, "max_qty": 1,
    }


def test_variants_ignore_related_stock_and_order_limit():
    recarga = variant("Recarga", 18, 42, 1)
    completo = variant("Cilindro completo", 0, 70, 2)
    result = parse_goniogas(product([recarga, completo]))
    assert result["status"] == "available"
    assert result["details"]["variants"][0]["quantity"] == 18
    assert "Cilindro completo: Sin existencias" in result["status_label"]
    assert result["details"]["quantity"] is None
    assert parse_goniogas(product([completo, recarga]))["fingerprint"] == result["fingerprint"]
    recarga["availability_html"] = '<p class="stock">17 disponibles</p>'
    assert parse_goniogas(product([recarga, completo]))["fingerprint"] != result["fingerprint"]


def test_all_variants_unavailable_and_legacy_product():
    assert parse_goniogas(product([variant("Recarga", 0, 42, 1)]))["status"] == "unavailable"
    result = parse_goniogas('<main class="product instock"><p>25,00 €</p><p>8 disponibles</p><section class="related">Agotado</section></main>')
    assert result["status"] == "available"
    assert result["details"]["quantity"] == 8


def test_pickup_locations_and_changes_are_tracked_independently():
    variants = [variant("Recarga", 0, 42, 7551), variant("Cilindro completo", 0, 70, 7552), variant("Cilindro completo", 61, 70, 9099)]
    for item in variants:
        item["attributes"]["attribute_punto-de-recogida"] = "Siboney" if item["variation_id"] == 9099 else "La Coronella"
    first = parse_goniogas(product(variants))
    assert "Cilindro completo / Siboney: 61 disponibles" in first["status_label"]
    assert "Recarga / La Coronella: Sin existencias" in first["status_label"]
    assert len(first["price"]) > 50
    variants[2]["availability_html"] = '<p>60 disponibles</p>'
    assert parse_goniogas(product(variants))["fingerprint"] != first["fingerprint"]


def test_notify_only_when_refills_available_and_refills_change():
    def snapshot(refill_quantity, complete_quantity):
        return parse_goniogas(product([
            variant("Recarga", refill_quantity, 42, 1),
            variant("Cilindro completo", complete_quantity, 70, 2),
        ]))["details"]

    empty = snapshot(0, 0)
    complete_only = snapshot(0, 61)
    refill = snapshot(10, 61)
    assert gas_refill_notice(complete_only, empty) is None
    assert gas_refill_notice(empty, refill) is None
    assert gas_refill_notice(refill, refill) is None
    assert gas_refill_notice(snapshot(10, 60), refill) is None
    notice = gas_refill_notice(refill, complete_only)
    assert "Recarga: 10 disponibles" in notice
    assert "Cilindro completo" not in notice
    assert gas_refill_notice(snapshot(9, 61), refill) is not None
