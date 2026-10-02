from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Store:
    id: str
    name: str
    type: str
    ships_from: str = "EU"
    shipping: dict | None = None
    currency: str = "EUR"
    listing_urls: list[str] | None = None
    max_pages: int = 3
    status: str = "unverified"
    requires_login: bool = False


@dataclass
class Config:
    raw: dict
    stores: list[Store]

    def __getitem__(self, k):
        return self.raw[k]


def load(config_path: str | Path = "config.yaml", stores_path: str | Path = "stores.yaml") -> Config:
    raw = yaml.safe_load(Path(config_path).read_text())
    s = yaml.safe_load(Path(stores_path).read_text())
    stores = [Store(**{**e, "listing_urls": e.get("listing_urls") or []}) for e in s["stores"]]
    return Config(raw, stores)
