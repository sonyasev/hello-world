from __future__ import annotations

import json
from datetime import datetime, timezone

from .config import Config
from .db import DB
from .deals import Market, evaluate, within_price_band
from .models import Item
from .pricing import landed
from .scrapers import build_scrapers
from .scrapers.fetch import Fetcher
from .sizes import SizeProfile


def row_to_item(r) -> Item:
    return Item(store=r["store"], source_type=r["source_type"], url=r["url"], title=r["title"], price=r["price"],
                currency=r["currency"], brand=r["brand"], category=r["category"], sizes=json.loads(r["sizes"] or "[]"),
                original_price=r["original_price"], condition=r["condition"], landed_eur=r["landed_eur"],
                discount=r["discount"], product_code=r["product_code"])


def process(cfg: Config, items: list[Item], history: list[Item], profile: SizeProfile, sizer=None,
            prev_low: dict[str, float] | None = None) -> list[tuple[Item, bool]]:
    """Cost, deal-evaluate and size-filter items. `sizer(item) -> list[str]` fetches sizes when the listing had none.

    Returns (item, is_deal) for every in-band item; is_deal also requires one of your sizes to be available.
    """
    rules = cfg["deals"]
    stores = {s.id: s for s in cfg.stores}
    for it in items:
        landed(it, stores[it.store], cfg["fx"])
    items = [i for i in items if within_price_band(i, rules)]
    market = Market([*history, *items], prev_low)

    out = []
    for it in items:
        is_deal = evaluate(it, market, rules)
        if is_deal:  # fetch product pages only for candidates
            it.sizes = it.sizes or (sizer(it) if sizer else [])
            it.matched_sizes = profile.matches(it.category, it.sizes)
            is_deal = bool(it.matched_sizes)
        out.append((it, is_deal))
    return out


def run(cfg: Config, db: DB, only: list[str] | None = None, use_browser: bool = False, delay: float = 3.0) -> list[Item]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fetcher = Fetcher(use_browser=use_browser, delay=delay)
    profile = SizeProfile(cfg["sizes"])
    scrapers = build_scrapers(cfg, fetcher, only)
    try:
        by_store = {s.store.id: s for s in scrapers}
        items: list[Item] = []
        ok_stores = []
        for sc in scrapers:
            print(f"scraping {sc.store.name} ...")
            try:
                got = sc.scrape()
            except Exception as e:  # one broken store must not kill the run
                print(f"  FAILED: {e!r}")
                continue
            print(f"  {len(got)} top-brand items")
            if got:
                ok_stores.append(sc.store.id)
            items.extend(got)

        history = [row_to_item(r) for r in db.recent()]
        results = process(cfg, items, history, profile, prev_low=db.lowest_prices(),
                          sizer=lambda it: by_store[it.store].fetch_sizes(it.url))
        for it, is_deal in results:  # every item is kept: it builds price history and brand baselines
            db.upsert(it, is_deal, now)
        if ok_stores:
            db.expire(ok_stores, now)
        db.commit()
        return [i for i, d in results if d]
    finally:
        for sc in scrapers:
            sc.close()
        fetcher.close()
