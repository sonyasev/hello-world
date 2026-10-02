# luxdeals

Finds deals on top-30 luxury brands (women's clothes, shoes, bags) in your sizes across online stores and
pre-loved marketplaces that ship to Bulgaria. Output: a web page of deals with browser notifications
(WhatsApp / email messages are built in but switched off – see `notify` in `config.yaml`).
100% open source, no paid services.

## How it works
1. **Scrape** each store in `stores.yaml` (polite: robots.txt, rate-limited; generic schema.org JSON-LD parser, per-store subclass when needed).
2. **Landed cost in EUR** = price + shipping (per-store rule) + import duty/VAT for non-EU stores.
3. **Deal test** – an item is a deal if any signal fires (all thresholds in `config.yaml`):
   - **pre-loved**: ≤105% of the median landed price of similar pre-loved items (≥3 comps); pre-loved listings themselves at ≤70%
   - **price history**: ≥10% below the lowest price ever seen for this item
   - **cross-store**: same product (manufacturer code) ≥15% cheaper than at any other store
   - **rare discount for the brand**: discount in the brand's top 10% (and ≥30%) – 40% off Loro Piana counts, 40% off Versace doesn't
   - **brand price**: ≤50% of the brand's usual landed price for that category
   - **fallback**: ≥50% off retail while a brand has too little history

   Every top-brand item is stored, so history-based signals get better after a week or two of daily runs.
4. **Sizes**: only items available in your sizes (`config.yaml`) are kept; sizes are fetched from the product page for deal candidates only.
5. **Output**: `site/index.html` – filterable, sortable table; click a row for the photo, full price breakdown
   (listed → EUR → shipping → import costs → delivered), every reason it is a deal, all sizes and price history.
   Deals added since your last visit are marked **NEW**.

## Run
```bash
pip install -e .            # add `.[browser]` + `playwright install chromium` for JS-heavy stores
luxdeals serve              # page at http://localhost:8000, re-scrapes every 6 h (--every 12, --port 8080)
luxdeals run                # one scrape, then rebuild site/index.html (open it straight from disk)
luxdeals run --only mytheresa --browser
luxdeals report             # just rebuild the page from the DB
pytest
```

## Browser notifications
With `luxdeals serve` running, open http://localhost:8000 and click **Turn on browser notifications**. While that tab is
open (it can be in the background), the page checks for new deals every 5 minutes and pops up a notification.
There is no notification when the tab or the computer is closed – that would need a push server.

## Secrets (environment variables)
Never put passwords in `config.yaml` or commit them. Two options, depending on where it runs:

- **On your computer**: `cp .env.example .env` and fill it in. `.env` is gitignored and loaded automatically.
- **GitHub Actions** (`.github/workflows/scrape.yml`, daily): GitHub repo → **Settings → Secrets and variables → Actions →
  New repository secret**, one per name in `.env.example`. Download the page from the run's *deals-page* artifact.

| Variable | What |
|---|---|
| `WHATSAPP_PHONE`, `CALLMEBOT_APIKEY` | WhatsApp via [CallMeBot](https://www.callmebot.com/blog/free-api-whatsapp-messages/) (free; one-time activation from your phone gives the key) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `NOTIFY_EMAIL_TO` | Email fallback. Gmail: `smtp.gmail.com`, port 465, and an [App Password](https://myaccount.google.com/apppasswords) (needs 2-step verification) |
| `BESTSECRET_EMAIL`, `BESTSECRET_PASSWORD` | BestSecret login (needs `pip install .[browser]`) |

`notify.mode` in `config.yaml`: `whatsapp_then_email` (default), `both`, `whatsapp`, `email`.

## Status / known limits (please read)
- **Store scraping is unverified.** It was developed in a sandbox with no access to the shops, so the listing URLs in
  `stores.yaml` and the generic JSON-LD parser have not been tried against the real sites. Expect to adjust URLs and add a
  `Scraper` subclass in `scrapers/base.py::CUSTOM` for stores that don't expose JSON-LD (Farfetch, YOOX, Vestiaire often need `--browser`).
- **BestSecret** logs in with a headless browser (`scrapers/bestsecret.py`) and saves the session in `data/`. Login selectors and the
  listing URL in `stores.yaml` are guesses – replace the URL with a sale page you browse when logged in. Automated access may be against
  BestSecret's terms; it runs slowly once a day to limit the risk of the account being flagged.
- **GitHub Actions** runs from datacenter IPs, which some stores (Farfetch, YOOX) may block; running on your own computer is more reliable.
- **CallMeBot** is a free third-party service with no uptime guarantee – that's why email is the fallback.
- Shipping rules and duty rates are **indicative defaults** – verify each store's Bulgaria shipping page and edit `stores.yaml` / `pricing.py`.
  FX rates in `config.yaml` are static.
- Pre-loved "similar item" matching is title-token based; it is a heuristic, review top deals by eye.
