"""Viber notifications via the Viber Bot API (https://developers.viber.com/docs/api/rest-bot-api/).

The receiver must have started a conversation with your bot (subscribed) before it can message them.
"""
from __future__ import annotations

import os

import httpx

API = "https://chatapi.viber.com/pa/send_message"


def format_deal(r) -> str:
    sizes = ", ".join(__import__("json").loads(r["matched_sizes"] or "[]"))
    tag = "pre-loved" if r["source_type"] == "preloved" else "new"
    return (f"💎 {r['brand']} – {r['title']}\n{r['store']} ({tag}) · size {sizes}\n"
            f"€{r['landed_eur']:.0f} landed · {r['reason']}\n{r['url']}")


def send(rows: list, cfg: dict) -> list[str]:
    """Send one message per deal. Returns URLs successfully sent."""
    token = os.environ.get(cfg["auth_token_env"])
    receiver = os.environ.get(cfg["receiver_env"])
    if not token or not receiver:
        print(f"viber: set {cfg['auth_token_env']} and {cfg['receiver_env']} to enable notifications")
        return []
    sent = []
    with httpx.Client(timeout=20) as c:
        for r in rows[: cfg.get("max_per_run", 10)]:
            resp = c.post(API, headers={"X-Viber-Auth-Token": token}, json={
                "receiver": receiver, "min_api_version": 1, "type": "text",
                "sender": {"name": cfg["sender_name"]}, "text": format_deal(r)})
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if resp.status_code == 200 and body.get("status") == 0:
                sent.append(r["url"])
            else:
                print(f"viber: failed ({resp.status_code}) {body.get('status_message', resp.text[:120])}")
                break
    return sent
