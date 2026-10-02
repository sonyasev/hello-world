from __future__ import annotations

import argparse
import functools
import threading
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config as cfgmod
from . import notify
from .db import DB
from .envfile import load_env
from .pipeline import run
from .report import render


def build_page(cfg, db: DB) -> Path:
    rows = db.deals(cfg["report"]["max_rows"])
    out = render(rows, {s.id: s.name for s in cfg.stores},
                 datetime.now().astimezone().strftime("%d %b %Y, %H:%M"), cfg["report"]["output"],
                 history=db.price_history([r["url"] for r in rows]))
    print(f"wrote {out} ({len(rows)} deals)")
    return out


def scrape_and_build(cfg, a) -> None:
    db = DB(a.db)  # own connection: may run in a background thread
    deals = run(cfg, db, a.only, a.browser, a.delay)
    print(f"{len(deals)} deals this run")
    build_page(cfg, db)
    if not a.no_notify and cfg["notify"]["enabled"]:
        rows = db.unnotified_deals(cfg["notify"]["max_per_run"])
        db.mark_notified(notify.send(rows, cfg["notify"]))
        db.commit()


def serve(cfg, a) -> None:
    site = Path(cfg["report"]["output"]).parent
    build_page(cfg, DB(a.db))

    def loop():
        while True:
            try:
                scrape_and_build(cfg, a)
            except Exception as e:  # keep serving even if a run fails
                print(f"run failed: {e!r}")
            time.sleep(a.every * 3600)

    if a.every > 0:
        threading.Thread(target=loop, daemon=True).start()
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site))
    httpd = ThreadingHTTPServer(("127.0.0.1", a.port), handler)
    print(f"open http://localhost:{a.port}  (Ctrl+C to stop; re-scraping every {a.every}h)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv=None):
    p = argparse.ArgumentParser(prog="luxdeals")
    p.add_argument("command", choices=["run", "report", "serve", "notify", "test-notify"],
                   help="run = scrape + build page; report = rebuild page; serve = local page + scrape on a timer")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--stores", default="stores.yaml")
    p.add_argument("--db", default="data/luxdeals.db")
    p.add_argument("--only", nargs="*", help="store ids to scrape")
    p.add_argument("--browser", action="store_true", help="use headless Chromium (pip install .[browser])")
    p.add_argument("--delay", type=float, default=3.0, help="seconds between requests")
    p.add_argument("--every", type=float, default=6, help="serve: hours between scrapes (0 = never)")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-notify", action="store_true")
    a = p.parse_args(argv)
    load_env()
    cfg = cfgmod.load(a.config, a.stores)

    if a.command == "test-notify":
        sample = {"url": "https://example.com/test", "brand": "Max Mara", "title": "Test message – setup works",
                  "store": "luxdeals", "source_type": "new", "matched_sizes": '["M"]', "landed_eur": 0.0,
                  "reason": "notification test"}
        print("sent" if notify.send([sample], cfg["notify"]) else "NOT sent – see messages above")
    elif a.command == "run":
        scrape_and_build(cfg, a)
    elif a.command == "report":
        build_page(cfg, DB(a.db))
    elif a.command == "serve":
        serve(cfg, a)
    elif a.command == "notify":
        db = DB(a.db)
        db.mark_notified(notify.send(db.unnotified_deals(cfg["notify"]["max_per_run"]), cfg["notify"]))
        db.commit()


if __name__ == "__main__":
    main()
