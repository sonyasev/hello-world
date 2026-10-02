import json

import pytest

from luxdeals import config as cfgmod
from luxdeals.brands import find_brand_in_title, normalize_brand
from luxdeals.categories import infer_category
from luxdeals.db import DB
from luxdeals.models import Item
from luxdeals.pipeline import process
from luxdeals.report import render
from luxdeals.scrapers.base import Scraper
from luxdeals.scrapers.extract import jsonld_products
from luxdeals.sizes import SizeProfile, parse_size

CFG = cfgmod.load()
PROFILE = SizeProfile(CFG["sizes"])


def test_brand_aliases():
    assert normalize_brand("YSL") == "Saint Laurent"
    assert normalize_brand("Céline") == "Celine"
    assert normalize_brand("Hermes") == "Hermès"
    assert normalize_brand("Zara") is None
    assert find_brand_in_title("Loro Piana cashmere cardigan") == "Loro Piana"


def test_categories():
    assert infer_category("Leather ankle boots") == "shoes"
    assert infer_category("Wide-leg wool trousers") == "bottoms"
    assert infer_category("Silk slip dress") == "dresses"
    assert infer_category("Cashmere sweater") == "tops"


@pytest.mark.parametrize("raw,cat,expected", [
    ("IT 42", None, ("IT", 42)), ("42 IT", None, ("IT", 42)), ("UK10", None, ("UK", 10)),
    ("m", None, ("INTL", "M")), ("38,5", "shoes", ("EU", 38.5)), ("EU 39", "shoes", ("EU", 39)),
    ("W29", None, ("W", 29)), ("29/32", None, ("W", 29)), ("40", "bottoms", ("EU", 40)),
    ("42", "tops", None), ("40", "tops", None),
])
def test_parse_size(raw, cat, expected):
    assert parse_size(raw, cat, CFG["sizes"]["bare_numbers"]) == expected


def test_size_matching():
    assert PROFILE.matches("tops", ["XS", "S", "IT 44"]) == ["S"]
    assert PROFILE.matches("bottoms", ["IT 40", "IT 44", "29"]) == ["IT 44", "29"]
    assert PROFILE.matches("shoes", ["37", "38.5", "40"]) == ["38.5"]
    assert PROFILE.matches("shoes", ["EU 41"]) == []
    assert PROFILE.matches("bags", []) == ["one size"]


LD = """<script type="application/ld+json">{"@type":"ItemList","itemListElement":[
{"@type":"ListItem","item":{"@type":"Product","name":"Wool coat","brand":{"name":"Max Mara"},"url":"/p/1",
 "offers":{"price":"890.00","priceCurrency":"EUR"}}},
{"@type":"Product","name":"Zara top","brand":"Zara","url":"/p/2","offers":{"price":10,"priceCurrency":"EUR"}}]}</script>"""


def test_jsonld_and_brand_filter():
    prods = jsonld_products(LD, "https://x.com")
    assert [p["url"] for p in prods] == ["https://x.com/p/1", "https://x.com/p/2"]

    class F:
        def get(self, url):
            return LD if url.endswith("1") else None

    store = CFG.stores[0]
    store.listing_urls = ["https://x.com/sale?page={page}"]
    items = Scraper(store, F()).scrape()
    assert len(items) == 1 and items[0].brand == "Max Mara" and items[0].category == "outerwear"


def mk(store, typ, title, price, **kw):
    return Item(store=store, source_type=typ, url=f"https://{store}/{title.replace(' ', '-')}-{price}", title=title,
                price=price, brand="Max Mara", category="outerwear", **kw)


def test_landed_cost_and_deal_pipeline():
    # preloved comps ~ €500 landed (Vestiaire: flat 15 shipping)
    comps = [mk("vestiaire", "preloved", f"Max Mara camel wool coat {i}", p, sizes=["S"]) for i, p in enumerate([430, 470, 485, 520])]
    cheap = mk("mytheresa", "new", "Max Mara camel wool coat", 380, sizes=["S", "XL"])      # 380 + 15 = 395 < ~490
    pricey = mk("mytheresa", "new", "Max Mara camel wool coat black", 900, sizes=["M"])
    wrong_size = mk("mytheresa", "new", "Max Mara camel wool coat grey", 400, sizes=["XXL"])
    uk = mk("theoutnet", "new", "Max Mara camel wool coat navy", 400, sizes=["IT 42"])      # non-EU: duties push it up
    res = process(CFG, [*comps, cheap, pricey, wrong_size, uk], [], PROFILE)
    urls = {i.url: i for i, _ in res}
    assert cheap.url in urls and urls[cheap.url].matched_sizes == ["S"]
    assert pricey.url not in urls and wrong_size.url not in urls
    assert uk.landed_eur > 400 * 1.2  # VAT + duty applied
    assert cheap.shipping_eur == 15 and cheap.landed_eur == 395


def test_fallback_discount_without_comps():
    it = mk("mytheresa", "new", "Max Mara rare coat", 300, sizes=["M"], original_price=900)
    res = process(CFG, [it], [], PROFILE)
    assert res and "off retail" in res[0][0].reason


def test_report_and_db(tmp_path):
    it = mk("mytheresa", "new", "Max Mara <b>coat</b>", 300, sizes=["M"], original_price=900)
    (i, _), = process(CFG, [it], [], PROFILE)
    db = DB(tmp_path / "t.db")
    db.upsert(i, True, "2026-10-02T00:00:00")
    db.commit()
    out = render(db.deals(10), {"mytheresa": "Mytheresa"}, "now", tmp_path / "s" / "index.html")
    html = out.read_text()
    assert "Mytheresa" in html and "<b>coat</b>" not in html  # escaped
    assert len(db.unnotified_deals(10)) == 1
    db.mark_notified([i.url])
    assert db.unnotified_deals(10) == []
