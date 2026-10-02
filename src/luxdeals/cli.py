from __future__ import annotations

import argparse
from datetime import datetime, timezone

from . import config as cfgmod
from .db import DB
from .notify import viber
from .pipeline import run
from .report import render


def main(argv=None):
    p = argparse.ArgumentParser(prog="luxdeals")
    p.add_argument("command", choices=["run", "report", "notify"], help="run = scrape+report+notify")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--stores", default="stores.yaml")
    p.add_argument("--db", default="data/luxdeals.db")
    p.add_argument("--only", nargs="*", help="store ids to scrape")
    p.add_argument("--browser", action="store_true", help="use headless Chromium (pip install .[browser])")
    p.add_argument("--delay", type=float, default=3.0, help="seconds between requests")
    p.add_argument("--no-notify", action="store_true")
    a = p.parse_args(argv)

    cfg = cfgmod.load(a.config, a.stores)
    db = DB(a.db)
    if a.command == "run":
        deals = run(cfg, db, a.only, a.browser, a.delay)
        print(f"{len(deals)} deals this run")
    if a.command in ("run", "report"):
        rows = db.deals(cfg["report"]["max_rows"])
        out = render(rows, {s.id: s.name for s in cfg.stores},
                     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), cfg["report"]["output"])
        print(f"wrote {out} ({len(rows)} rows)")
    if a.command in ("run", "notify") and not a.no_notify and cfg["viber"]["enabled"]:
        rows = db.unnotified_deals(cfg["viber"]["max_per_run"])
        db.mark_notified(viber.send(rows, cfg["viber"]))
        db.commit()


if __name__ == "__main__":
    main()
