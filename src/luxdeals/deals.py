"""Compare items to pre-loved comparables and flag good deals."""
from __future__ import annotations

import re
import statistics
from collections import defaultdict

from .models import Item

_STOP = {"the", "a", "and", "with", "in", "of", "for", "women", "womens", "woman", "new", "size", "leather"}


def title_tokens(item: Item) -> set[str]:
    t = re.sub(r"[^a-z0-9 ]+", " ", item.title.lower())
    brand = (item.brand or "").lower().split()
    return {w for w in t.split() if w not in _STOP and w not in brand and not w.isdigit() and len(w) > 2}


def similarity(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


class Pool:
    """Pre-loved items indexed by (brand, category) for comparable lookup."""

    def __init__(self, items: list[Item]):
        self.index: dict[tuple, list[tuple[Item, set[str]]]] = defaultdict(list)
        for it in items:
            if it.landed_eur and it.brand and it.category:
                self.index[(it.brand, it.category)].append((it, title_tokens(it)))

    def comparables(self, item: Item, min_sim: float) -> list[Item]:
        toks = title_tokens(item)
        return [
            c for c, ct in self.index.get((item.brand, item.category), [])
            if c is not item and c.url != item.url and similarity(toks, ct) >= min_sim
        ]


def evaluate(item: Item, pool: Pool, rules: dict) -> bool:
    """Set ref/ratio/reason on `item`; return True if it is a deal."""
    comps = pool.comparables(item, rules["min_title_similarity"])
    item.comps = len(comps)
    if len(comps) >= rules["min_comps"]:
        item.ref_price_eur = round(statistics.median(c.landed_eur for c in comps), 2)
        item.ratio = round(item.landed_eur / item.ref_price_eur, 3)
        limit = rules["max_ratio_vs_preloved"] if item.source_type == "new" else rules["preloved_max_ratio"]
        if item.ratio <= limit:
            item.reason = f"{item.ratio:.0%} of pre-loved median (€{item.ref_price_eur:.0f}, {item.comps} comps)"
            return True
        return False
    if item.source_type == "new" and item.discount is not None and item.discount >= rules["min_discount_vs_retail"]:
        item.reason = f"{item.discount:.0%} off retail (no pre-loved comps)"
        return True
    return False


def within_price_band(item: Item, rules: dict) -> bool:
    return item.landed_eur is not None and rules["min_price_eur"] <= item.landed_eur <= rules["max_price_eur"]
