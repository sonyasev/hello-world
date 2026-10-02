from __future__ import annotations

from ..brands import find_brand_in_title, normalize_brand
from ..categories import infer_category
from ..config import Config, Store
from ..models import Item
from .extract import jsonld_products
from .fetch import Fetcher


class Scraper:
    """Generic listing scraper. Subclass and override `parse` for stores without usable JSON-LD."""

    def __init__(self, store: Store, fetcher: Fetcher):
        self.store = store
        self.fetcher = fetcher

    def parse(self, html: str, url: str) -> list[dict]:
        return jsonld_products(html, url)

    @classmethod
    def has_credentials(cls) -> bool:
        return False

    def close(self):
        pass

    def fetch_sizes(self, url: str) -> list[str]:
        """Available sizes from the product page (listing pages rarely carry them)."""
        html = self.fetcher.get(url)
        if not html:
            return []
        sizes: list[str] = []
        for r in self.parse(html, url):
            sizes.extend(r.get("sizes", []))
        return sorted(set(sizes))

    def scrape(self) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()
        for template in self.store.listing_urls:
            for page in range(1, self.store.max_pages + 1):
                url = template.format(page=page)
                html = self.fetcher.get(url)
                if not html:
                    break
                rows = [r for r in self.parse(html, url) if r["url"] not in seen]
                if not rows:
                    break  # ran off the end of pagination
                for r in rows:
                    seen.add(r["url"])
                    brand = normalize_brand(r.get("brand")) or find_brand_in_title(r["title"])
                    if not brand:  # only the top-30 brands
                        continue
                    items.append(Item(
                        store=self.store.id, source_type=self.store.type, url=r["url"], title=r["title"],
                        price=r["price"], currency=r.get("currency") or self.store.currency, brand=brand,
                        category=infer_category(r["title"], r.get("category")), sizes=r.get("sizes", []),
                        original_price=r.get("original_price"), condition=r.get("condition"), image=r.get("image"),
                        product_code=r.get("product_code"),
                    ))
        return items


def _custom() -> dict[str, type[Scraper]]:
    """Store-specific subclasses, keyed by store id (see README: "Adding / fixing a store")."""
    from .bestsecret import BestSecretScraper

    return {"bestsecret": BestSecretScraper}


def build_scrapers(cfg: Config, fetcher: Fetcher, only: list[str] | None = None) -> list[Scraper]:
    out = []
    for s in cfg.stores:
        if only and s.id not in only:
            continue
        if not s.listing_urls:
            print(f"skipping {s.id}: no listing URLs")
            continue
        cls = _custom().get(s.id, Scraper)
        if s.requires_login and not cls.has_credentials():
            print(f"skipping {s.id}: login required, credentials not set")
            continue
        out.append(cls(s, fetcher))
    return out
