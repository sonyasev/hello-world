from __future__ import annotations

import json
from datetime import datetime, timezone

from .config import Config
from .db import DB
from .deals import Pool, evaluate, within_price_band
from .models import Item
from .pricing import landed
from .scrapers import build_scrapers
from .scrapers.fetch import Fetcher
from .sizes import SizeProfile


def row_to_item(r) -> Item:
    return Item(store=r["store"], source_type=r["source_type"], url=r["url"], title=r["title"], price=r["price"],
                currency=r["currency"], brand=r["brand"], category=r["category"], sizes=json.loads(r["sizes"] or "[]"),
                original_price=r["original_price"], condition=r["condition"], landed_eur=r["landed_eur"])


def process(cfg: Config, items: list[Item], history: list[Item], profile: SizeProfile, sizer=None) -> list[tuple[Item, bool]]:
    """Cost, deal-evaluate and size-filter items. `sizer(item) -> list[str]` fetches sizes when the listing had none.

    Returns (item, is_deal) for every item that is in the price band and fits the sizes.
    """
    rules = cfg["deals"]
    stores = {s.id: s for s in cfg.stores}
    for it in items:
        landed(it, stores[it.store], cfg["fx"])
    items = [i for i in items if within_price_band(i, rules)]
    pool = Pool([*history, *[i for i in items if i.source_type == "preloved"]])

    out = []
    for it in items:
        is_deal = evaluate(it, pool, rules)
        if not is_deal:
            continue
        sizes = it.sizes or (sizer(it) if sizer else [])
        it.sizes = sizes
        it.matched_sizes = profile.matches(it.category, sizes)
        if it.matched_sizes:
            out.append((it, True))
    return out


def run(cfg: Config, db: DB, only: list[str] | None = None, use_browser: bool = False, delay: float = 3.0) -> list[Item]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fetcher = Fetcher(use_browser=use_browser, delay=delay)
    profile = SizeProfile(cfg["sizes"])
    try:
        scrapers = build_scrapers(cfg, fetcher, only)
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

        history = [row_to_item(r) for r in db.preloved()]
        results = process(cfg, items, history, profile, sizer=lambda it: by_store[it.store].fetch_sizes(it.url))
        deals = [i for i, _ in results]
        for it in deals:
            db.upsert(it, True, now)
        # keep every preloved item as pricing history, even non-deals
        for it in items:
            if it.source_type == "preloved" and it.landed_eur and it not in deals:
                db.upsert(it, False, now)
        if ok_stores:
            db.expire(ok_stores, now)
        db.commit()
        return deals
    finally:
        fetcher.close()
