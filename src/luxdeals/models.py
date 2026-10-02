from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Item:
    store: str
    source_type: str  # "new" or "preloved"
    url: str
    title: str
    price: float  # in `currency`, as listed
    currency: str = "EUR"
    brand: str | None = None
    category: str | None = None  # tops, bottoms, dresses, outerwear, shoes, bags
    sizes: list[str] = field(default_factory=list)  # available sizes, raw strings
    original_price: float | None = None  # retail / pre-discount price
    condition: str | None = None  # preloved only
    image: str | None = None
    product_code: str | None = None  # manufacturer code (mpn), for cross-store matching
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    # filled by the pipeline
    price_eur: float | None = None
    shipping_eur: float = 0.0
    duties_eur: float = 0.0
    landed_eur: float | None = None
    matched_sizes: list[str] = field(default_factory=list)
    ref_price_eur: float | None = None  # median landed price of comparables
    comps: int = 0
    ratio: float | None = None  # landed / ref
    discount: float | None = None  # 0..1 vs original price
    score: float = 0.0  # higher = better deal
    reason: str = ""
