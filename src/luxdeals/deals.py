"""Deal detection. An item is a deal when any signal fires; the strongest signal sets its score.

Signals:
  preloved     landed price vs median of similar pre-loved items
  history      price dropped below the lowest landed price we have seen for this item
  cross_store  same product (manufacturer code) is cheaper here than at every other store
  brand_disc   discount is unusually deep for this brand (vs the brand's own discount distribution)
  brand_price  landed price far below the brand's usual price for this category
  retail_disc  fallback: deep discount vs the store's original price
"""
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


def _quantile(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


class Market:
    """Everything known about recent prices, used as the reference for every signal."""

    def __init__(self, items: list[Item], prev_low: dict[str, float] | None = None):
        self.prev_low = prev_low or {}
        self.preloved: dict[tuple, list[tuple[Item, set[str]]]] = defaultdict(list)
        self.brand_discounts: dict[str, list[float]] = defaultdict(list)
        self.brand_cat_prices: dict[tuple, list[float]] = defaultdict(list)
        self.by_code: dict[str, list[Item]] = defaultdict(list)
        for it in {i.url: i for i in items}.values():  # later items (this run) override history
            if not (it.landed_eur and it.brand):
                continue
            if it.source_type == "preloved":
                if it.category:
                    self.preloved[(it.brand, it.category)].append((it, title_tokens(it)))
                continue
            if it.discount is not None:
                self.brand_discounts[it.brand].append(it.discount)
            if it.category:
                self.brand_cat_prices[(it.brand, it.category)].append(it.landed_eur)
            if it.product_code:
                self.by_code[it.product_code].append(it)

    def comparables(self, item: Item, min_sim: float) -> list[Item]:
        toks = title_tokens(item)
        return [c for c, ct in self.preloved.get((item.brand, item.category), [])
                if c.url != item.url and similarity(toks, ct) >= min_sim]


def evaluate(item: Item, m: Market, r: dict) -> bool:
    """Fill ref/ratio/score/reason on `item`; return True if it is a deal."""
    hits: list[tuple[float, str]] = []  # (strength 0..1, reason)

    comps = m.comparables(item, r["min_title_similarity"])
    item.comps = len(comps)
    if len(comps) >= r["min_comps"]:
        item.ref_price_eur = round(statistics.median(c.landed_eur for c in comps), 2)
        item.ratio = round(item.landed_eur / item.ref_price_eur, 3)
        limit = r["max_ratio_vs_preloved"] if item.source_type == "new" else r["preloved_max_ratio"]
        if item.ratio <= limit:
            hits.append((1 - item.ratio, f"{item.ratio:.0%} of pre-loved median €{item.ref_price_eur:.0f} ({item.comps} comps)"))

    low = m.prev_low.get(item.url)
    if low and item.landed_eur <= low * (1 - r["min_price_drop"]):
        drop = 1 - item.landed_eur / low
        hits.append((drop, f"price drop {drop:.0%} – lowest seen (was €{low:.0f})"))

    if item.source_type == "new":
        if item.product_code:
            others = [o for o in m.by_code.get(item.product_code, []) if o.store != item.store]
            if others:
                best = min(others, key=lambda o: o.landed_eur)
                saving = 1 - item.landed_eur / best.landed_eur
                if saving >= r["min_cross_store_saving"]:
                    hits.append((saving, f"{saving:.0%} cheaper than {best.store} (€{best.landed_eur:.0f})"))

        discs = m.brand_discounts.get(item.brand, [])
        if item.discount is not None and len(discs) >= r["min_brand_samples"]:
            typical = _quantile(discs, r["brand_discount_quantile"])
            if item.discount >= max(typical, r["min_discount_floor"]) and item.discount > statistics.median(discs):
                hits.append((item.discount - statistics.median(discs),
                             f"{item.discount:.0%} off – rare for {item.brand} (usually ≤{typical:.0%})"))
        elif item.discount is not None and item.discount >= r["min_discount_vs_retail"]:
            hits.append((item.discount - 0.3, f"{item.discount:.0%} off retail"))

        prices = m.brand_cat_prices.get((item.brand, item.category), [])
        if len(prices) >= r["min_brand_samples"]:
            med = statistics.median(prices)
            if item.landed_eur <= med * r["max_ratio_vs_brand_median"]:
                hits.append((1 - item.landed_eur / med,
                             f"{item.landed_eur / med:.0%} of usual {item.brand} {item.category} price (€{med:.0f})"))

    if not hits:
        item.score, item.reason = 0.0, ""
        return False
    hits.sort(reverse=True)
    item.score = round(hits[0][0] + 0.1 * (len(hits) - 1), 3)  # small bonus for multiple signals
    item.reason = " · ".join(h[1] for h in hits)
    return True


def within_price_band(item: Item, rules: dict) -> bool:
    return item.landed_eur is not None and rules["min_price_eur"] <= item.landed_eur <= rules["max_price_eur"]
