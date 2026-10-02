"""Landed cost to Bulgaria: price + shipping + import VAT/duty where applicable."""
from __future__ import annotations

from .models import Item

BG_VAT = 0.20
DUTY = {"shoes": 0.08, "bags": 0.03, "default": 0.12}  # clothing duty ~12%, footwear ~8% (indicative)


def to_eur(amount: float, currency: str, fx: dict) -> float:
    if currency not in fx:
        raise KeyError(f"no FX rate for {currency}")
    return amount * fx[currency]


def landed(item: Item, store, fx: dict) -> Item:
    """Fill price_eur, shipping_eur, duties_eur, landed_eur on the item."""
    price = to_eur(item.price, item.currency, fx)
    rule = store.shipping or {}
    free_over = rule.get("free_over")
    shipping = 0.0 if (free_over is not None and free_over > 0 and price >= free_over) else float(rule.get("flat", 0.0))
    duties = 0.0
    total = price + shipping
    if store.ships_from == "non-EU":
        duty_pct = DUTY.get(item.category or "", DUTY["default"])
        duty = (price + shipping) * duty_pct
        vat = (price + shipping + duty) * BG_VAT
        # Goods listed with UK VAT already stripped at checkout: add BG import VAT + duty.
        duties = duty + vat
        total = price + shipping + duties
    item.price_eur = round(price, 2)
    item.shipping_eur = round(shipping, 2)
    item.duties_eur = round(duties, 2)
    item.landed_eur = round(total, 2)
    if item.original_price:
        orig = to_eur(item.original_price, item.currency, fx)
        item.discount = max(0.0, 1 - price / orig) if orig > 0 else None
    return item
