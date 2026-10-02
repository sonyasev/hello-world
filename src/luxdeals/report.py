"""Deals page: a static index.html with the data embedded, plus deals.json for live refresh.

Opened as a file it shows the data it was built with. Served over HTTP (`luxdeals serve`) it polls
deals.json and raises a browser notification for deals that appear while the page is open.
"""
from __future__ import annotations

import json
from pathlib import Path

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Luxury Deals</title>
<style>
:root{--bg:#fbfaf7;--card:#fff;--fg:#1c1b19;--mut:#6f6b63;--line:#e7e3da;--acc:#8a5a00;--accbg:#f6eedc;--new:#1f7a4d;--newbg:#e3f3ea}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#121211;--card:#1b1a18;--fg:#ecebe7;--mut:#a29d93;--line:#2f2d29;--acc:#e3b55a;--accbg:#2c2416;--new:#6fd3a0;--newbg:#16291f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:24px 16px 8px;max-width:1200px;margin:auto}h1{margin:0;font-size:24px;letter-spacing:-.01em}
.sub{color:var(--mut);font-size:13px}.bar{display:flex;gap:8px;flex-wrap:wrap;padding:10px 16px;max-width:1200px;margin:auto;align-items:center}
input,select,button{font:inherit;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg)}
button{cursor:pointer}button.primary{background:var(--acc);border-color:var(--acc);color:var(--bg)}
input[type=search]{flex:1;min-width:180px}.spacer{flex:1}
main{max-width:1200px;margin:auto;padding:0 16px 48px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);text-align:left;padding:10px;border-bottom:1px solid var(--line);font-weight:600}
td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top}tr.row{cursor:pointer}@media (hover:hover){tr.row:hover td{background:var(--accbg)}}
.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
img.th{width:56px;height:72px;object-fit:cover;border-radius:6px;background:var(--line)}
.brand{font-weight:650}.chip{display:inline-block;background:var(--accbg);color:var(--acc);border-radius:5px;padding:1px 7px;font-size:12px;margin:2px 3px 0 0}
.badge{display:inline-block;background:var(--newbg);color:var(--new);font-size:11px;font-weight:700;border-radius:5px;padding:1px 6px;margin-left:6px;vertical-align:1px}
.why{color:var(--acc);font-size:13px}.big{font-size:17px;font-weight:650}
tr.detail td{background:var(--bg);padding:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
.box h3{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
.kv{display:flex;justify-content:space-between;gap:12px;padding:2px 0;font-variant-numeric:tabular-nums}.kv.total{border-top:1px solid var(--line);margin-top:4px;padding-top:6px;font-weight:650}
.big-img{width:100%;max-width:220px;max-height:260px;object-fit:cover;border-radius:8px;display:block}a.btn{display:inline-block;margin-top:10px;padding:8px 14px;border-radius:8px;background:var(--acc);color:var(--bg);text-decoration:none;font-weight:600}
.empty{padding:40px;text-align:center;color:var(--mut)}
@media (max-width:720px){thead{display:none}table,tbody,tr,td{display:block;width:100%}tr.row{display:grid;grid-template-columns:64px 1fr auto;gap:0 10px;padding:10px}
 tr.row td{border:0;padding:0}tr.row td.c-img{grid-column:1;grid-row:1/5}tr.row td.c-info{grid-column:2;grid-row:1}
 tr.row td.c-price{grid-column:3;grid-row:1}tr.row td.c-store,tr.row td.c-size,tr.row td.c-why{grid-column:2/4}tr.row{border-bottom:1px solid var(--line)}
 tr.detail td{display:block}}
</style></head><body>
<header><h1>Luxury deals · delivered to Bulgaria</h1>
<div class="sub" id="meta"></div></header>
<div class="bar">
 <input type="search" id="q" placeholder="Search brand or item">
 <select id="st"><option value="">All stores</option></select>
 <select id="ct"><option value="">All categories</option></select>
 <select id="ty"><option value="">New + pre-loved</option><option value="new">New</option><option value="preloved">Pre-loved</option></select>
 <select id="so"><option value="score">Best deal first</option><option value="new">Newest first</option><option value="price">Price: low to high</option><option value="price-desc">Price: high to low</option></select>
 <label class="sub"><input type="checkbox" id="onlynew"> only new</label>
 <span class="spacer"></span><button id="notif" hidden>Turn on browser notifications</button>
</div>
<main><table><thead><tr><th></th><th>Item</th><th>Store</th><th>Your size</th><th class="n">Delivered</th><th>Why it's a deal</th></tr></thead>
<tbody id="tb"></tbody></table><div class="empty" id="empty" hidden>No deals match.</div></main>
<script type="application/json" id="data">__DATA__</script>
<script>
let D = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id), open = new Set();
const store = {get(k){try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
const prevSeen = new Set(store.get('luxdeals.seen') || []), firstVisit = !store.get('luxdeals.seen');
const isNew = r => !firstVisit && !prevSeen.has(r.url);
const eur = v => v == null ? '–' : '€' + Math.round(v).toLocaleString('en');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = v => v == null ? '–' : Math.round(v * 100) + '%';

function fillSelect(id, values){const s=$(id),cur=s.value;s.length=1;[...new Set(values)].filter(Boolean).sort().forEach(v=>s.add(new Option(v,v)));s.value=cur}
function detail(r){
  const hist=(r.history||[]).map(h=>`<div class="kv"><span>${esc(h[0].slice(0,10))}</span><span>${eur(h[1])}</span></div>`).join('')||'<div class="sub">First time seen</div>';
  return `<tr class="detail"><td colspan="6"><div class="grid">
   <div class="box">${r.image?`<img class="big-img" src="${esc(r.image)}" alt="">`:''}<br><a class="btn" href="${esc(r.url)}" target="_blank" rel="noopener">Open at ${esc(r.store_name)} ↗</a></div>
   <div class="box"><h3>Price to your door</h3>
    <div class="kv"><span>Listed</span><span>${r.price.toLocaleString('en')} ${esc(r.currency)}</span></div>
    <div class="kv"><span>In EUR</span><span>${eur(r.price_eur)}</span></div>
    <div class="kv"><span>Shipping to BG</span><span>${r.shipping_eur?eur(r.shipping_eur):'free'}</span></div>
    ${r.duties_eur?`<div class="kv"><span>Import duty + VAT</span><span>${eur(r.duties_eur)}</span></div>`:''}
    <div class="kv total"><span>Delivered</span><span>${eur(r.landed_eur)}</span></div>
    ${r.original_price?`<div class="kv sub"><span>Original price</span><span>${r.original_price.toLocaleString('en')} ${esc(r.currency)} (−${pct(r.discount)})</span></div>`:''}
    ${r.ref_price_eur?`<div class="kv sub"><span>Similar pre-loved (median)</span><span>${eur(r.ref_price_eur)}</span></div>`:''}</div>
   <div class="box"><h3>Why it's a deal</h3>${r.reason.split(' · ').map(x=>`<div>• ${esc(x)}</div>`).join('')}
    <h3 style="margin-top:12px">Sizes</h3>${(r.sizes||[]).map(s=>`<span class="chip" style="${r.matched.includes(s)?'':'opacity:.45'}">${esc(s)}</span>`).join('')||'<span class="sub">one size</span>'}
    ${r.condition?`<h3 style="margin-top:12px">Condition</h3>${esc(r.condition)}`:''}</div>
   <div class="box"><h3>Price history</h3>${hist}<div class="sub" style="margin-top:6px">First seen ${esc((r.first_seen||'').slice(0,10))}</div></div>
  </div></td></tr>`;
}
function render(){
  const q=$('q').value.toLowerCase(),st=$('st').value,ct=$('ct').value,ty=$('ty').value,so=$('so').value,on=$('onlynew').checked;
  let rows=D.rows.filter(r=>(!q||(r.brand+' '+r.title).toLowerCase().includes(q))&&(!st||r.store_name===st)&&(!ct||r.category===ct)&&(!ty||r.source_type===ty)&&(!on||isNew(r)));
  const by={score:(a,b)=>b.score-a.score,new:(a,b)=>(b.first_seen||'').localeCompare(a.first_seen||''),price:(a,b)=>a.landed_eur-b.landed_eur,'price-desc':(a,b)=>b.landed_eur-a.landed_eur}[so];
  rows.sort(by);
  $('tb').innerHTML=rows.map(r=>`<tr class="row" data-url="${esc(r.url)}">
   <td class="c-img">${r.image?`<img class="th" loading="lazy" src="${esc(r.image)}" alt="">`:''}</td>
   <td class="c-info"><span class="brand">${esc(r.brand)}</span>${isNew(r)?'<span class="badge">NEW</span>':''}<br>${esc(r.title)}<div class="sub">${esc(r.category||'')}${r.source_type==='preloved'?' · pre-loved':''}</div></td>
   <td class="c-store">${esc(r.store_name)}</td>
   <td class="c-size">${r.matched.map(s=>`<span class="chip">${esc(s)}</span>`).join('')}</td>
   <td class="n c-price"><span class="big">${eur(r.landed_eur)}</span>${r.discount?`<div class="sub">−${pct(r.discount)} off</div>`:''}</td>
   <td class="why c-why">${esc(r.reason.split(' · ')[0])}${r.reason.includes(' · ')?' <span class="sub">+ more</span>':''}</td></tr>`+(open.has(r.url)?detail(r):'')).join('');
  $('empty').hidden=rows.length>0;
  const nNew=D.rows.filter(isNew).length;
  $('meta').textContent=`${D.rows.length} deals in your sizes · ${firstVisit?'first visit':nNew+' new since your last visit'} · updated ${D.updated} · prices include shipping and import costs`;
}
$('tb').addEventListener('click',e=>{const tr=e.target.closest('tr.row');if(!tr||e.target.closest('a'))return;const u=tr.dataset.url;open.has(u)?open.delete(u):open.add(u);render()});
['q','st','ct','ty','so','onlynew'].forEach(id=>$(id).addEventListener('input',render));
function init(){fillSelect('st',D.rows.map(r=>r.store_name));fillSelect('ct',D.rows.map(r=>r.category));render()}
init();
// remember what was on the page so the next visit can mark new deals
window.addEventListener('pagehide',()=>store.set('luxdeals.seen',[...new Set([...prevSeen,...D.rows.map(r=>r.url)])]));
if(firstVisit)store.set('luxdeals.seen',D.rows.map(r=>r.url));

// live refresh + browser notifications (only when served over http, e.g. `luxdeals serve`)
const live=location.protocol.startsWith('http');
if(live&&'Notification' in window){
  const b=$('notif');
  const sync=()=>{b.hidden=Notification.permission!=='default'};
  b.onclick=()=>Notification.requestPermission().then(sync);sync();
}
if(live)setInterval(async()=>{
  try{
    const n=await (await fetch('deals.json?'+Date.now(),{cache:'no-store'})).json();
    if(n.updated===D.updated)return;
    const known=new Set(D.rows.map(r=>r.url)),fresh=n.rows.filter(r=>!known.has(r.url));
    D=n;init();
    if(fresh.length&&'Notification' in window&&Notification.permission==='granted'){
      const top=fresh.sort((a,b)=>b.score-a.score)[0];
      const note=new Notification(fresh.length===1?`${top.brand} – ${eur(top.landed_eur)}`:`${fresh.length} new luxury deals`,
        {body:`${top.title} · ${top.store_name}\\n${top.reason.split(' · ')[0]}`,icon:top.image||undefined,tag:'luxdeals'});
      note.onclick=()=>{window.focus();open.add(top.url);render()};
    }
  }catch(e){}
},5*60*1000);
</script></body></html>"""


def _prepare(rows: list, store_names: dict[str, str], history: dict[str, list]) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        d["store_name"] = store_names.get(d["store"], d["store"])
        d["matched"] = json.loads(d.pop("matched_sizes", None) or "[]")
        d["sizes"] = json.loads(d.get("sizes") or "[]")
        d["reason"] = d.get("reason") or ""
        d["score"] = d.get("score") or 0
        d["history"] = history.get(d["url"], [])
        for k in ("is_deal", "notified", "product_code"):
            d.pop(k, None)
        out.append(d)
    return out


def render(rows: list, store_names: dict[str, str], updated: str, out: str | Path,
           history: dict[str, list] | None = None) -> Path:
    data = {"updated": updated, "rows": _prepare(rows, store_names, history or {})}
    blob = json.dumps(data, ensure_ascii=False)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PAGE.replace("__DATA__", blob.replace("</", "<\\/")))
    (out.parent / "deals.json").write_text(blob)
    return out
