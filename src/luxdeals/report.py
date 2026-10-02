from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, select_autoescape

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Luxury Deals</title>
<style>
 :root{--bg:#fff;--fg:#1a1a1a;--mut:#6b6b6b;--line:#e5e5e5;--acc:#8a5a00;--chip:#f3efe6}
 @media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--mut:#9a9a9a;--line:#2e2e2e;--acc:#e0b050;--chip:#2a251b}}
 body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,sans-serif}
 header{padding:20px 16px 8px}h1{margin:0;font-size:22px}.sub{color:var(--mut);font-size:13px}
 .bar{display:flex;gap:8px;flex-wrap:wrap;padding:8px 16px}
 input,select{padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
 .wrap{overflow-x:auto;padding:0 16px 40px}table{border-collapse:collapse;width:100%;min-width:900px}
 th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
 th{cursor:pointer;position:sticky;top:0;background:var(--bg);font-size:12px;text-transform:uppercase;color:var(--mut)}
 td.n{text-align:right;font-variant-numeric:tabular-nums}.chip{background:var(--chip);border-radius:4px;padding:1px 6px;font-size:12px;margin-right:3px}
 .why{color:var(--acc);font-size:13px}a{color:inherit}img{width:48px;height:60px;object-fit:cover;border-radius:4px}
</style></head><body>
<header><h1>Luxury deals for Bulgaria</h1><div class="sub">Updated {{ updated }} · {{ rows|length }} deals · prices are landed (item + shipping + import costs) in EUR</div></header>
<div class="bar">
 <input id="q" placeholder="Search brand / item" oninput="f()">
 <select id="st" onchange="f()"><option value="">All stores</option>{% for s in stores %}<option>{{ s }}</option>{% endfor %}</select>
 <select id="ct" onchange="f()"><option value="">All categories</option>{% for c in cats %}<option>{{ c }}</option>{% endfor %}</select>
 <select id="ty" onchange="f()"><option value="">New + pre-loved</option><option value="new">New</option><option value="preloved">Pre-loved</option></select>
</div>
<div class="wrap"><table id="t"><thead><tr>
 <th></th><th>Brand / item</th><th>Store</th><th>Category</th><th>Your size</th>
 <th class="n" data-num>Landed €</th><th class="n" data-num>Ref €</th><th class="n" data-num>Ratio</th><th>Why</th>
</tr></thead><tbody>
{% for r in rows %}<tr data-type="{{ r.source_type }}" data-store="{{ r.store_name }}" data-cat="{{ r.category }}">
 <td>{% if r.image %}<img loading="lazy" src="{{ r.image }}" alt="">{% endif %}</td>
 <td><b>{{ r.brand }}</b><br><a href="{{ r.url }}" target="_blank" rel="noopener">{{ r.title }}</a>{% if r.condition %}<br><span class="sub">{{ r.condition }}</span>{% endif %}</td>
 <td>{{ r.store_name }}{% if r.source_type == 'preloved' %}<br><span class="sub">pre-loved</span>{% endif %}</td>
 <td>{{ r.category }}</td>
 <td>{% for s in r.matched %}<span class="chip">{{ s }}</span>{% endfor %}</td>
 <td class="n" data-v="{{ r.landed_eur }}">{{ '%.0f'|format(r.landed_eur) }}<br><span class="sub">{{ '%.0f'|format(r.price) }} {{ r.currency }} listed</span></td>
 <td class="n" data-v="{{ r.ref_price_eur or 0 }}">{{ '%.0f'|format(r.ref_price_eur) if r.ref_price_eur else '–' }}</td>
 <td class="n" data-v="{{ r.ratio or 9 }}">{{ '%.0f%%'|format(r.ratio*100) if r.ratio else '–' }}</td>
 <td class="why">{{ r.reason }}</td></tr>{% endfor %}
</tbody></table></div>
<script>
const tb=document.querySelector('#t tbody');
function f(){const q=document.getElementById('q').value.toLowerCase(),s=document.getElementById('st').value,c=document.getElementById('ct').value,y=document.getElementById('ty').value;
 for(const r of tb.rows){r.hidden=!((!q||r.innerText.toLowerCase().includes(q))&&(!s||r.dataset.store===s)&&(!c||r.dataset.cat===c)&&(!y||r.dataset.type===y));}}
document.querySelectorAll('th').forEach((th,i)=>th.onclick=()=>{const num=th.hasAttribute('data-num'),d=th._d=!th._d;
 const rows=[...tb.rows].sort((a,b)=>{const x=num?+a.cells[i].dataset.v:a.cells[i].innerText,y=num?+b.cells[i].dataset.v:b.cells[i].innerText;return(x>y?1:x<y?-1:0)*(d?1:-1)});rows.forEach(r=>tb.append(r));});
</script></body></html>"""


def render(rows: list, store_names: dict[str, str], updated: str, out: str | Path) -> Path:
    prepared = []
    for r in rows:
        d = dict(r)
        d["store_name"] = store_names.get(d["store"], d["store"])
        d["matched"] = json.loads(d.get("matched_sizes") or "[]")
        prepared.append(d)
    env = Environment(autoescape=select_autoescape(default=True, default_for_string=True))
    html = env.from_string(TEMPLATE).render(
        rows=prepared, updated=updated, stores=sorted({d["store_name"] for d in prepared}),
        cats=sorted({d["category"] for d in prepared if d["category"]}))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out
