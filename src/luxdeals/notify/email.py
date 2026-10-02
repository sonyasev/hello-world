"""Email digest over SMTP (works with Gmail using an App Password, or any mail provider)."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from html import escape


def send(rows: list, fmt, cfg: dict) -> bool:
    env = {k: os.environ.get(cfg[f"{k}_env"]) for k in ("host", "user", "password", "to")}
    if not all(env.values()):
        print("email: set " + ", ".join(cfg[f"{k}_env"] for k in env) + " to enable")
        return False
    msg = EmailMessage()
    msg["Subject"] = f"💎 {len(rows)} new luxury deal{'s' if len(rows) != 1 else ''} in your size"
    msg["From"], msg["To"] = env["user"], env["to"]
    msg.set_content("\n\n".join(fmt(r) for r in rows))
    msg.add_alternative("".join(
        f'<p><b>{escape(r["brand"])}</b> – <a href="{escape(r["url"])}">{escape(r["title"])}</a><br>'
        f'€{r["landed_eur"]:.0f} delivered · {escape(r["reason"])}</p>' for r in rows), subtype="html")
    port = int(os.environ.get(cfg.get("port_env", ""), 0) or 465)
    try:
        if port == 465:
            with smtplib.SMTP_SSL(env["host"], port, timeout=30) as s:
                s.login(env["user"], env["password"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(env["host"], port, timeout=30) as s:
                s.starttls()
                s.login(env["user"], env["password"])
                s.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        print(f"email: failed {e!r}")
        return False
    return True
