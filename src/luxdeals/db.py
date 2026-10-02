from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Item

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  url TEXT PRIMARY KEY, store TEXT, source_type TEXT, brand TEXT, category TEXT, title TEXT, product_code TEXT,
  sizes TEXT, matched_sizes TEXT, price REAL, currency TEXT, original_price REAL, discount REAL,
  landed_eur REAL, ref_price_eur REAL, ratio REAL, score REAL, reason TEXT,
  condition TEXT, image TEXT, first_seen TEXT, last_seen TEXT, is_deal INTEGER DEFAULT 0, notified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS price_history (url TEXT, seen TEXT, landed_eur REAL);
CREATE INDEX IF NOT EXISTS ph_url ON price_history(url);
"""

_COLS = ["url", "store", "source_type", "brand", "category", "title", "product_code", "sizes", "matched_sizes", "price",
         "currency", "original_price", "discount", "landed_eur", "ref_price_eur", "ratio", "score", "reason",
         "condition", "image", "first_seen", "last_seen", "is_deal"]
_UPDATE = [c for c in _COLS if c not in ("url", "first_seen")]


class DB:
    def __init__(self, path: str | Path = "data/luxdeals.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        have = {r[1] for r in self.con.execute("PRAGMA table_info(items)")}
        for col in _COLS:  # add columns introduced after the DB was created
            if col not in have:
                self.con.execute(f"ALTER TABLE items ADD COLUMN {col}")

    def upsert(self, it: Item, is_deal: bool, now: str):
        prev = self.con.execute("SELECT landed_eur FROM items WHERE url=?", (it.url,)).fetchone()
        vals = {**{c: getattr(it, c, None) for c in _COLS}, "sizes": json.dumps(it.sizes),
                "matched_sizes": json.dumps(it.matched_sizes), "last_seen": now, "is_deal": int(is_deal)}
        self.con.execute(
            f"INSERT INTO items ({','.join(_COLS)}) VALUES ({','.join('?' * len(_COLS))}) "
            f"ON CONFLICT(url) DO UPDATE SET {','.join(f'{c}=excluded.{c}' for c in _UPDATE)}",
            [vals[c] for c in _COLS])
        if not prev or prev["landed_eur"] != it.landed_eur:
            self.con.execute("INSERT INTO price_history VALUES (?,?,?)", (it.url, now, it.landed_eur))

    def expire(self, store_ids: list[str], now: str):
        """Items of successfully scraped stores not seen this run are gone (sold / removed)."""
        q = ",".join("?" * len(store_ids))
        self.con.execute(f"UPDATE items SET is_deal=0 WHERE store IN ({q}) AND last_seen<?", (*store_ids, now))

    def recent(self, days: int = 30) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM items WHERE last_seen>=date('now', ?)", (f"-{days} day",)).fetchall()

    def lowest_prices(self) -> dict[str, float]:
        return {r[0]: r[1] for r in self.con.execute("SELECT url, MIN(landed_eur) FROM price_history GROUP BY url")}

    def deals(self, limit: int):
        return self.con.execute("SELECT * FROM items WHERE is_deal=1 ORDER BY score DESC LIMIT ?", (limit,)).fetchall()

    def unnotified_deals(self, limit: int):
        return self.con.execute(
            "SELECT * FROM items WHERE is_deal=1 AND notified=0 ORDER BY score DESC LIMIT ?", (limit,)).fetchall()

    def mark_notified(self, urls: list[str]):
        self.con.executemany("UPDATE items SET notified=1 WHERE url=?", [(u,) for u in urls])

    def commit(self):
        self.con.commit()
