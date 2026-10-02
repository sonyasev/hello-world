"""Send new deals: WhatsApp first, email as fallback (or both, see config `notify.mode`)."""
from __future__ import annotations

import json

from . import email, whatsapp


def format_deal(r) -> str:
    sizes = ", ".join(json.loads(r["matched_sizes"] or "[]"))
    tag = "pre-loved" if r["source_type"] == "preloved" else "new"
    return (f"💎 {r['brand']} – {r['title']}\n{r['store']} ({tag}) · size {sizes}\n"
            f"€{r['landed_eur']:.0f} delivered to BG · {r['reason']}\n{r['url']}")


def send(rows: list, cfg: dict) -> list[str]:
    """Returns URLs that were delivered by at least one channel."""
    if not rows:
        return []
    mode = cfg.get("mode", "whatsapp_then_email")
    sent: list[str] = []
    if mode in ("whatsapp_then_email", "both", "whatsapp"):
        sent = whatsapp.send(rows, format_deal, cfg["whatsapp"])
    missing = [r for r in rows if r["url"] not in sent]
    if mode == "both" or mode == "email" or (mode == "whatsapp_then_email" and missing):
        targets = rows if mode != "whatsapp_then_email" else missing
        if email.send(targets, format_deal, cfg["email"]):
            sent = list({*sent, *(r["url"] for r in targets)})
    return sent
