"""Generic product extraction from listing pages: schema.org JSON-LD and Next.js/embedded JSON."""
from __future__ import annotations

import json
import re
from typing import Any, Iterator
from urllib.parse import urljoin

_LD = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)


def _walk(node: Any) -> Iterator[dict]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _first(v):
    return v[0] if isinstance(v, list) and v else v


def _price(offer: Any) -> tuple[float | None, str | None, float | None]:
    offer = _first(offer)
    if not isinstance(offer, dict):
        return None, None, None
    spec = _first(offer.get("priceSpecification"))
    price = offer.get("price") or offer.get("lowPrice")
    cur = offer.get("priceCurrency")
    orig = None
    if isinstance(spec, dict) and spec.get("price"):
        orig = _to_float(spec.get("price")) if spec.get("priceType", "").endswith("ListPrice") else None
    return _to_float(price), cur, orig


def _to_float(v) -> float | None:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def jsonld_products(html: str, base_url: str = "") -> list[dict]:
    """Return normalised dicts: title, brand, url, price, currency, original_price, sizes, image, condition."""
    out = []
    for block in _LD.findall(html):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for node in _walk(data):
            t = node.get("@type")
            if t not in ("Product", ["Product"]) and "Product" not in (t if isinstance(t, list) else [t]):
                continue
            price, cur, orig = _price(node.get("offers"))
            if price is None or not node.get("name"):
                continue
            brand = node.get("brand")
            brand = brand.get("name") if isinstance(brand, dict) else brand
            offer = _first(node.get("offers")) or {}
            size = node.get("size")
            sizes = [str(s) for s in size] if isinstance(size, list) else ([str(size)] if size else [])
            offers = node.get("offers")
            for o in offers if isinstance(offers, list) else []:  # one offer per size variant
                label = o.get("size") or o.get("name")
                if label and "OutOfStock" not in str(o.get("availability", "")):
                    sizes.append(str(label))
            cond = str(offer.get("itemCondition", "")).rsplit("/", 1)[-1] or None
            out.append({
                "title": node["name"], "brand": brand, "url": urljoin(base_url, node.get("url") or offer.get("url") or ""),
                "price": price, "currency": cur, "original_price": orig, "sizes": sizes,
                "image": _first(node.get("image")) if not isinstance(_first(node.get("image")), dict) else None,
                "condition": cond,
            })
    return out
