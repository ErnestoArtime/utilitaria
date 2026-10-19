import html
import json

from app.alerts import parse_goniogas


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
