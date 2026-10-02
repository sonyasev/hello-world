# luxdeals

Finds deals on top-30 luxury brands (women's clothes, shoes, bags) in your sizes across online stores and
pre-loved marketplaces that ship to Bulgaria. Output: a sortable web page + Viber notifications.
100% open source, no paid services.

## How it works
1. **Scrape** each store in `stores.yaml` (polite: robots.txt, rate-limited; generic schema.org JSON-LD parser, per-store subclass when needed).
2. **Landed cost in EUR** = price + shipping (per-store rule) + import duty/VAT for non-EU stores.
3. **Deal test**: new items are compared with the median landed price of similar pre-loved items (same brand + category + title similarity, min 3 comps). A deal is ≤105% of that median, or ≥50% off retail when no comps exist. Pre-loved items are flagged when ≤70% of similar pre-loved. Tune in `config.yaml`.
4. **Sizes**: only items available in your sizes (`config.yaml`) are kept; sizes are fetched from the product page for deal candidates only.
5. **Output**: `site/index.html` (sortable/filterable table) and Viber messages for deals not yet notified.

## Run
```bash
pip install -e .            # add `.[browser]` + `playwright install chromium` for JS-heavy stores
luxdeals run                # scrape + report + notify
luxdeals run --only mytheresa --browser --no-notify
luxdeals report             # just rebuild the page from the DB
pytest
```

## Viber
Create a Viber bot account (https://partners.viber.com), then `export VIBER_AUTH_TOKEN=... VIBER_RECEIVER_ID=...`.
Your Viber user must have started a chat with the bot. Without these variables notifications are skipped.

## Status / known limits (please read)
- **Store scraping is unverified.** It was developed in a sandbox with no access to the shops, so the listing URLs in
  `stores.yaml` and the generic JSON-LD parser have not been tried against the real sites. Expect to adjust URLs and add a
  `Scraper` subclass in `scrapers/base.py::CUSTOM` for stores that don't expose JSON-LD (Farfetch, YOOX, Vestiaire often need `--browser`).
- **BestSecret** is a members-only club (login required); it is skipped. Login support could be added with Playwright.
- Shipping rules and duty rates are **indicative defaults** – verify each store's Bulgaria shipping page and edit `stores.yaml` / `pricing.py`.
  FX rates in `config.yaml` are static.
- Pre-loved "similar item" matching is title-token based; it is a heuristic, review top deals by eye.
