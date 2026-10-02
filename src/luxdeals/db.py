from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Item

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  url TEXT PRIMARY KEY, store TEXT, source_type TEXT, brand TEXT, category TEXT, title TEXT,
  sizes TEXT, matched_sizes TEXT, price REAL, currency TEXT, original_price REAL,
  landed_eur REAL, ref_price_eur REAL, ratio REAL, discount REAL, reason TEXT,
  condition TEXT, image TEXT, first_seen TEXT, last_seen TEXT, is_deal INTEGER DEFAULT 0, notified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS price_history (url TEXT, seen TEXT, landed_eur REAL);
"""


class DB:
    def __init__(self, path: str | Path = "data/luxdeals.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    def upsert(self, it: Item, is_deal: bool, now: str):
        prev = self.con.execute("SELECT first_seen, landed_eur FROM items WHERE url=?", (it.url,)).fetchone()
        first_seen = prev["first_seen"] if prev else it.first_seen
        self.con.execute(
            """INSERT INTO items (url,store,source_type,brand,category,title,sizes,matched_sizes,price,currency,
               original_price,landed_eur,ref_price_eur,ratio,discount,reason,condition,image,first_seen,last_seen,is_deal)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(url) DO UPDATE SET price=excluded.price, original_price=excluded.original_price,
                 sizes=excluded.sizes, matched_sizes=excluded.matched_sizes, landed_eur=excluded.landed_eur,
                 ref_price_eur=excluded.ref_price_eur, ratio=excluded.ratio, discount=excluded.discount,
                 reason=excluded.reason, last_seen=excluded.last_seen, is_deal=excluded.is_deal""",
            (it.url, it.store, it.source_type, it.brand, it.category, it.title, json.dumps(it.sizes),
             json.dumps(it.matched_sizes), it.price, it.currency, it.original_price, it.landed_eur,
             it.ref_price_eur, it.ratio, it.discount, it.reason, it.condition, it.image, first_seen, now, int(is_deal)),
        )
        if not prev or prev["landed_eur"] != it.landed_eur:
            self.con.execute("INSERT INTO price_history VALUES (?,?,?)", (it.url, now, it.landed_eur))

    def expire(self, store_ids: list[str], now: str):
        """Items of successfully scraped stores not seen this run are gone (sold / removed)."""
        q = ",".join("?" * len(store_ids))
        self.con.execute(f"UPDATE items SET is_deal=0 WHERE store IN ({q}) AND last_seen<?", (*store_ids, now))

    def preloved(self) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM items WHERE source_type='preloved' AND last_seen>=date('now','-14 day')").fetchall()

    def deals(self, limit: int):
        return self.con.execute(
            "SELECT * FROM items WHERE is_deal=1 ORDER BY COALESCE(ratio, 1.0 - COALESCE(discount,0)) ASC LIMIT ?", (limit,)
        ).fetchall()

    def unnotified_deals(self, limit: int):
        return self.con.execute(
            "SELECT * FROM items WHERE is_deal=1 AND notified=0 ORDER BY COALESCE(ratio, 1.0 - COALESCE(discount,0)) ASC LIMIT ?",
            (limit,)).fetchall()

    def mark_notified(self, urls: list[str]):
        self.con.executemany("UPDATE items SET notified=1 WHERE url=?", [(u,) for u in urls])

    def commit(self):
        self.con.commit()
