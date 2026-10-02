"""WhatsApp messages to yourself via CallMeBot (free, https://www.callmebot.com/blog/free-api-whatsapp-messages/).

One-time setup: follow the page above (add CallMeBot's current number to your contacts and send it the
activation message on WhatsApp); it replies with your personal API key.
"""
from __future__ import annotations

import os
import time

import httpx

API = "https://api.callmebot.com/whatsapp.php"


def send(rows: list, fmt, cfg: dict) -> list[str]:
    phone, key = os.environ.get(cfg["phone_env"]), os.environ.get(cfg["apikey_env"])
    if not phone or not key:
        print(f"whatsapp: set {cfg['phone_env']} and {cfg['apikey_env']} to enable")
        return []
    sent = []
    with httpx.Client(timeout=30) as c:
        for r in rows[: cfg.get("max_per_run", 10)]:
            try:
                resp = c.get(API, params={"phone": phone, "text": fmt(r), "apikey": key})
            except httpx.HTTPError as e:
                print(f"whatsapp: {e!r}")
                break
            if resp.status_code != 200 or "error" in resp.text.lower()[:300]:
                print(f"whatsapp: failed ({resp.status_code}) {resp.text[:150]}")
                break
            sent.append(r["url"])
            time.sleep(cfg.get("delay_seconds", 3))  # CallMeBot rate-limits bursts
    return sent
