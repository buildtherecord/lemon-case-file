#!/usr/bin/env python3
# Generates docs/index.html — the FICTIONAL demo case file for GitHub Pages.
# Every name, party, document, number, and image is invented. The page exists to
# show the SHAPE of a finished case file produced by the prompts in this repo.
import base64, html, os, datetime

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.makedirs("docs", exist_ok=True)

# ---- placeholder thumbnails: tiny inline SVGs as data URIs ----
def svg_thumb(kind, label):
    icon = {"video": "&#9654;", "photo": "&#9679;", "doc": "&#9636;"}[kind]
    bg = {"video": "#3a4a5a", "photo": "#4a5a4a", "doc": "#efece3"}[kind]
    fg = "#6b675e" if kind == "doc" else "#ffffff"
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">'
         f'<rect width="120" height="120" fill="{bg}"/>'
         f'<text x="60" y="56" font-size="30" fill="{fg}" text-anchor="middle">{icon}</text>'
         f'<text x="60" y="86" font-size="11" fill="{fg}" text-anchor="middle" '
         f'font-family="sans-serif">{label}</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(s.encode()).decode()

# ---- fictional catalogue sample for the grid (24 of the "61") ----
GRID = [
    ("2024", None, None, None),
    ("2024-03-09", "doc", "Purchase", "Retail Purchase Agreement — Deal #4821 · Ex. A-1"),
    ("2024-07-06", "photo", "displays", "#008 — Cluster and center screen dark at 40 mph · Ex. C-8"),
    ("2024-07-08", "doc", "RO", "RO410221 — displays: 'could not verify' · Ex. A-2"),
    ("2024-08-14", "video", "displays", "#012 — Cluster dark at speed; infotainment rebooting (34s) · Ex. C-12"),
    ("2024-08-28", "doc", "TSB", "TSB LT-24-07 — rear door latch sticking · Ex. A-3"),
    ("2024-09-18", "video", "door latch", "#016 — Driver-rear latch: handle pulls, door stays shut (11s) · Ex. C-16"),
    ("2024-09-20", "doc", "RO", "RO412876 — latch: 'working as designed' · Ex. A-4"),
    ("2024-10-02", "video", "door latch", "#019 — Latch failure again, passenger present (9s) · Ex. C-19"),
    ("2024-12-08", "photo", "charging", "#025 — Charging stopped at 31%, fault message · Ex. C-25"),
    ("2024-12-11", "doc", "RO", "RO415502 — charge-port latch replaced: 'concern verified, fault codes stored' · Ex. A-5"),
    ("2024-12-21", "video", "charging", "#027 — Connector locked in port, 10 days after replacement (41s) · Ex. C-27"),
    ("2025", None, None, None),
    ("2025-05-06", "doc", "Recall", "Federal recall 25V-987 filed — display software · Ex. A-7"),
    ("2025-06-12", "doc", "Dealer comm", "'No repair available' — dealers instructed to wait for remedy · Ex. A-8"),
    ("2025-07-30", "video", "displays", "#033 — Both screens dark on highway entrance ramp (22s) · Ex. C-33"),
    ("2025-08-20", "doc", "RO", "RO421339 opened — vehicle remains at dealer awaiting remedy · Ex. A-9"),
    ("2025-11-12", "doc", "RO", "RO421339 closed — recall software performed, day 84 · Ex. A-9"),
    ("2026", None, None, None),
    ("2026-02-03", "video", "displays", "#048 — Cluster blackout, 83 days after recall remedy (17s) · Ex. C-48"),
    ("2026-03-06", "doc", "RO", "RO427710 — latch assembly replaced: 'internal malfunction' · Ex. A-11"),
    ("2026-03-24", "doc", "Position", "Manufacturer's written position — 'does not substantially impair' · Ex. A-12"),
    ("2026-04-18", "video", "door latch", "#059 — Same latch, 43 days after replacement (13s) · Ex. C-59"),
    ("2026-04-27", "doc", "Demand", "Written demand for repurchase · Ex. B-4"),
]

CATS = {"displays": "Displays", "door latch": "Door latch", "charging": "Charging",
        "Purchase": "Paper", "RO": "Paper", "TSB": "Paper", "Recall": "Paper",
        "Dealer comm": "Paper", "Position": "Paper", "Demand": "Paper"}

cells = []
for date, kind, tag, cap in GRID:
    if kind is None:
        cells.append(f'<div class="gyear">{date}</div>')
        continue
    cat = "paper" if CATS.get(tag) == "Paper" else tag.replace(" ", "_")
    k = "doc" if CATS.get(tag) == "Paper" else kind
    thumb = svg_thumb(k, date)
    if k == "doc":
        cells.append(
            f'<a class="gcell gdoc" href="placeholder-document.pdf" target="_blank" data-cat="{cat}" '
            f'title="{html.escape(cap)} — placeholder; a real case file links the full original here">'
            f'<img src="{thumb}" alt=""><span class="gd">{html.escape(tag[:12])}</span></a>')
    else:
        badge = '<span class="gv">&#9654;</span>' if k == "video" else ""
        cells.append(
            f'<span class="gcell" data-cat="{cat}" title="{html.escape(cap)}">'
            f'<img src="{thumb}" alt="">{badge}</span>')

# ---- timeline strip (simplified) ----
def dnum(q): return datetime.date.fromisoformat(q).toordinal()
X0, X1 = dnum("2024-02-01"), dnum("2026-07-01")
def x(dt): return round(16 + 968 * (dnum(dt) - X0) / (X1 - X0), 1)
def days(a, b): return dnum(b) - dnum(a)
assert days("2025-08-20", "2025-11-12") == 84
assert days("2025-08-20", "2025-10-10") == 51 and days("2025-10-10", "2025-11-12") == 33

TT = []
def tt(d, t, u=None, ul=None, sub=None):
    TT.append({"d": d, "t": t, "u": u, "ul": ul, "sub": sub or []})
    return len(TT) - 1

S = []
LANES = [(30, "Safety recall — federal filing &#8594; work on this car", "#a3271f"),
         (86, "Vehicle at the dealership", "#7a766c"),
         (142, "Manufacturer publications", "#6b675e"),
         (198, "Owner — reports &amp; evidence", "#1a4d8f")]
for yy, lab, col in LANES:
    S.append(f'<text x="16" y="{yy-6}" font-size="10.5" fill="{col}">{lab}</text>')
for yr in ("2025", "2026"):
    S.append(f'<line x1="{x(yr+"-01-01")}" y1="22" x2="{x(yr+"-01-01")}" y2="230" stroke="#e3e0d8"/>'
             f'<text x="{x(yr+"-01-01")}" y="244" text-anchor="middle" font-size="10" fill="#6b675e">{yr}</text>')

def bar(y, d0, d1, col, tip, title, light=False, marks=(), u=None, ul=None):
    i = tt(tip, title, u, ul)
    S.append(f'<rect class="tlp" data-i="{i}" x="{x(d0)}" y="{y}" width="{max(4, round(x(d1)-x(d0),1))}" '
             f'height="13" rx="2.5" fill="{col}" fill-opacity="{".35" if light else ".85"}"/>')
    for m in marks:
        S.append(f'<rect x="{x(m)-1.1}" y="{y+1.5}" width="2.2" height="10" fill="#fff" fill-opacity=".95" pointer-events="none"/>')

def tick(y, d, col, tip, title, h=20, u=None, ul=None):
    i = tt(tip, title, u, ul)
    S.append(f'<rect class="tlp" data-i="{i}" x="{x(d)-1.2}" y="{y}" width="2.4" height="{h}" fill="{col}" fill-opacity=".8"/>')

PD, PDL = "placeholder-document.pdf", "Open the full document (placeholder PDF)"
bar(30, "2025-05-06", "2025-11-12", "#a3271f",
    "2025-05-06 &#8594; 2025-11-12",
    "Recall 25V-987 — display software. Filed May 6, 2025. White mark: remedy available to dealers "
    "October 10, 2025. Performed on this car November 12, 2025 — 190 days after filing.",
    marks=("2025-10-10",), u=PD, ul=PDL)
bar(86, "2025-08-20", "2025-11-12", "#7a766c",
    "84 days", "At the dealership Aug 20 &#8594; Nov 12, 2025 — 84 days. 51 days waiting for a remedy "
    "to exist ('no repair available'); 33 days once work could begin.", light=True)
for ro, d0, d1 in (("RO410221", "2024-07-08", "2024-07-09"), ("RO412876", "2024-09-20", "2024-09-20"),
                   ("RO415502", "2024-12-09", "2024-12-11"), ("RO427710", "2026-03-03", "2026-03-06")):
    bar(86, d0, d1, "#55524a", f"{d0} &#8594; {d1}", f"{ro} — in the shop.", u=PD, ul=PDL)
tick(142, "2024-08-28", "#6b675e", "2024-08-28 · Technical bulletin", "TSB LT-24-07 — rear door latch sticking", u=PD, ul=PDL)
tick(142, "2025-06-12", "#6b675e", "2025-06-12 · Dealer notice", "'No repair available' — dealers told to wait for remedy", u=PD, ul=PDL)
tick(142, "2026-03-24", "#6b675e", "2026-03-24 · Written position", "Manufacturer: defect 'does not substantially impair'", u=PD, ul=PDL)
for d, t in (("2024-07-06", "First written report — displays dark while driving"),
             ("2024-08-14", "#012 — cluster dark at speed (video)"),
             ("2024-09-18", "#016 — latch failure (video)"), ("2024-12-08", "#025 — charging stopped (photo)"),
             ("2024-12-21", "#027 — connector locked, 10 days after replacement (video)"),
             ("2025-07-30", "#033 — both screens dark on ramp (video)"),
             ("2026-02-03", "#048 — blackout 83 days after recall remedy (video)"),
             ("2026-04-18", "#059 — same latch, 43 days after replacement (video)"),
             ("2026-04-27", "Written demand for repurchase")):
    tick(198, d, "#1a4d8f", d, t)

LEDGER = [
    ("Jul 8–9, 2024", "RO410221", "Displays / instrument cluster", "Inspected; software reset",
     "&#8220;could not verify customer concern&#8221;", "Yes — Aug 14, 2024 (#012)"),
    ("Sep 20, 2024", "RO412876", "Door latch, driver rear", "Inspected",
     "&#8220;working as designed&#8221;", "Yes — Oct 2, 2024 (#019)"),
    ("Dec 9–11, 2024", "RO415502", "Charge-port latch", "Replaced",
     "&#8220;concern verified, fault codes stored&#8221;", "Yes — Dec 21, 2024 (#027)"),
    ("Aug 20 – Nov 12, 2025", "RO421339", "Displays — recall 25V-987", "Recall software performed (day 84)",
     "&#8220;remedy per recall bulletin&#8221;", "Yes — Feb 3, 2026 (#048)"),
    ("Mar 3–6, 2026", "RO427710", "Door latch, driver rear", "Latch assembly replaced",
     "&#8220;internal malfunction&#8221;", "Yes — Apr 18, 2026 (#059)"),
]
lrows = "".join(
    f"<tr><td>{d}</td><td>{ro}</td><td><b>{c}</b> — {a}<br><span class='basis'>Their stated basis: {b}</span></td>"
    f"<td class='rec'>{r}</td></tr>" for d, ro, c, a, b, r in LEDGER)

players = ""
for pk, (title, date, sub) in {
    "#012": ("Cluster dark at speed; infotainment rebooting", "August 14, 2024",
             "38 days after the first written displays report — RO410221 closed 'could not verify'"),
    "#027": ("Connector locked in charge port", "December 21, 2024",
             "10 days after RO415502 replaced the charge-port latch"),
    "#048": ("Cluster blackout while driving", "February 3, 2026",
             "83 days after the recall 25V-987 remedy was performed"),
}.items():
    players += (f'<figure class="player"><div class="poster"><img src="{svg_thumb("video", pk)}" alt="">'
                f'<span class="pv">&#9654;</span><span class="pnote">placeholder — a real case file streams the actual clip here</span></div>'
                f'<figcaption><b>{html.escape(title)}</b><span>{date} · {html.escape(sub)}</span></figcaption></figure>')

TTJS = "var TT=" + str(TT).replace("None", "null") + ";"

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Demo case file — fictional — lemon-case-file</title>
<style>
:root{{--ink:#23211c;--mut:#6b675e;--line:#e3e0d8;--blue:#1a4d8f;--paper:#faf9f6;}}
body{{font:15px/1.6 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:var(--ink);margin:0;background:var(--paper);}}
.fiction{{background:#1f1d18;color:#ffd34d;text-align:center;padding:10px 16px;font-size:13.5px;letter-spacing:.02em;}}
.fiction b{{color:#fff;}}
.wrap{{max-width:1040px;margin:0 auto;padding:28px 20px 60px;}}
h1{{font-size:26px;margin:18px 0 2px;}}
.sub{{color:var(--mut);font-size:13px;margin-bottom:18px;}}
.banner{{border:1px solid var(--line);background:#f4f3ee;border-radius:8px;padding:10px 16px;font-size:13.5px;margin-bottom:22px;}}
.abstract{{border-left:3px solid var(--blue);background:#f6f7fa;padding:14px 18px;margin:0 0 26px;}}
.ab-label{{font-size:11px;letter-spacing:.08em;color:var(--blue);text-transform:uppercase;font-weight:700;}}
.ab-ask{{margin-top:10px;font-weight:600;color:var(--blue);}}
h2{{font-size:15px;letter-spacing:.06em;text-transform:uppercase;color:#8a5a1f;margin:34px 0 10px;}}
table.ledger{{width:100%;border-collapse:collapse;font-size:13.5px;}}
.ledger th{{text-align:left;border-bottom:2px solid #b9b4a6;padding:6px 8px;font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);}}
.ledger td{{border-bottom:1px solid var(--line);padding:8px;vertical-align:top;}}
.basis{{color:var(--mut);font-size:12.5px;}}
td.rec{{color:#a3271f;font-weight:600;white-space:nowrap;}}
svg text{{font-family:inherit;}}
.tlp{{cursor:pointer;}}
#tip{{position:fixed;display:none;background:#1f1d18;color:#fff;font-size:12.5px;padding:7px 10px;border-radius:6px;max-width:340px;z-index:50;pointer-events:none;line-height:1.45;}}
#evm{{display:none;position:fixed;inset:0;background:rgba(20,18,14,.72);z-index:60;align-items:center;justify-content:center;padding:24px;}}
#evm .box{{background:#fff;border-radius:10px;max-width:520px;padding:22px 26px;position:relative;}}
#evm .evm-x{{position:absolute;top:10px;right:14px;border:0;background:none;font-size:20px;cursor:pointer;color:var(--mut);}}
#evm .evm-date{{color:var(--mut);font-size:12.5px;}}
#evm .evm-title{{font-weight:700;margin:4px 0 10px;}}
#evm .evm-link{{display:none;background:var(--blue);color:#fff;text-decoration:none;font-size:13px;padding:8px 14px;border-radius:6px;}}
.chips{{margin:0 0 14px;}}
.chip{{display:inline-block;border:1px solid var(--line);border-radius:20px;padding:4px 12px;font-size:12.5px;cursor:pointer;margin:0 6px 6px 0;background:#fff;}}
.chip.on{{background:var(--blue);color:#fff;border-color:var(--blue);}}
.grid{{display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start;}}
.gyear{{flex-basis:100%;font-weight:700;color:var(--mut);font-size:12.5px;margin-top:8px;}}
.gcell{{position:relative;width:84px;height:84px;border-radius:6px;overflow:hidden;display:block;}}
.gcell img{{width:100%;height:100%;object-fit:cover;display:block;}}
.gcell .gv{{position:absolute;right:5px;bottom:3px;color:#fff;font-size:12px;text-shadow:0 0 4px #000;}}
.gdoc{{outline:2px solid #d8d2c0;outline-offset:-2px;}}
.gdoc .gd{{position:absolute;left:0;right:0;bottom:0;background:rgba(31,29,24,.78);color:#efece3;font-size:9.5px;text-align:center;padding:2px 0;}}
.players{{display:flex;gap:14px;flex-wrap:wrap;}}
.player{{margin:0;width:240px;}}
.poster{{position:relative;}}
.poster img{{width:240px;height:150px;object-fit:cover;border-radius:8px;display:block;}}
.poster .pv{{position:absolute;top:56px;left:104px;color:#fff;font-size:26px;text-shadow:0 0 8px #000;}}
.poster .pnote{{position:absolute;left:0;right:0;bottom:0;background:rgba(31,29,24,.8);color:#efece3;font-size:10px;text-align:center;padding:3px 6px;border-radius:0 0 8px 8px;}}
figcaption b{{display:block;font-size:13.5px;margin-top:6px;}}
figcaption span{{color:var(--mut);font-size:12px;}}
.ask{{background:#f4f3ee;border-left:3px solid var(--blue);padding:12px 16px;font-size:13.5px;margin:12px 0;}}
.dl{{display:inline-block;border:1px solid var(--line);border-radius:8px;padding:10px 16px;margin:6px 10px 0 0;text-decoration:none;color:var(--ink);font-size:13.5px;background:#fff;}}
footer{{margin-top:48px;border-top:1px solid var(--line);padding-top:16px;color:var(--mut);font-size:12.5px;}}
a{{color:var(--blue);}}
</style></head><body>
<div class="fiction"><b>FICTIONAL DEMONSTRATION.</b> Every name, party, vehicle, document, number, and image on this
page is invented. This is a template exemplar from the <a style="color:#ffd34d" href="https://github.com/buildtherecord/lemon-case-file">lemon-case-file</a> method.</div>
<div class="wrap">
<h1>The Meridian EV Case — Timeline &amp; Defect History</h1>
<div class="sub">2024 Acme Meridian EV &middot; VIN ACME00DEMO000000 &middot; Repurchase review case #00-DEMO (fictional)</div>
<div class="banner"><b>Prepared for the manufacturer's repurchase review — case #00-DEMO.</b> Submitted May 2026 (fictional).</div>

<div class="abstract"><span class="ab-label">In brief</span>
<p style="margin:8px 0 0">The owners have reported the same three problems — the displays going dark while driving,
a rear door latch that fails to open, and charging faults — since July 2024, four months after purchase.
Acme's dealers have serviced the vehicle six times: two visits closed &#8220;could not verify&#8221; or
&#8220;working as designed,&#8221; and every part that was replaced has had its symptom recur, at 10, 43, and 83 days.
A federal safety recall for the display defect was filed in May 2025, but no remedy existed for five months,
during which the vehicle sat at the dealership 84 days. The displays went dark again 83 days after the recall
remedy was performed.</p>
<div class="ab-ask">What the owners are asking for: that Acme Motors repurchase this vehicle. A written decision
is expected by June 30, 2026 (fictional).</div></div>

<h2>The record, 2024–2026</h2>
<p>The most serious failure came first. On July 6, 2024, while driving at roughly 40 mph, the instrument
cluster — the screen behind the steering wheel that carries the speedometer, battery level, and safety
warnings — went dark, and the center screen went dark with it. The owners reported it in writing the same
day. The dealership kept the car two days and closed the repair order &#8220;could not verify customer
concern&#8221; (RO410221). Thirty-eight days later the owners filmed the same failure (#012).</p>
<p>Each subsequent problem followed the same shape: a written report, a &#8220;could not verify&#8221; or
&#8220;working as designed&#8221; visit, and a dated recording of the symptom recurring. When federal recall
25V-987 confirmed the display defect across the model line in May 2025, no fix existed: Acme's own notice
told dealers &#8220;no repair available.&#8221; The car waited at the dealership from August 20 to
November 12, 2025 — <b>84 days, of which 51 passed before a remedy existed at all</b>. The recall software
was performed November 12, 2025. On February 3, 2026 — 83 days later — the cluster went dark again while
driving (#048).</p>

<h2>Component ledger — what was done, in their words, and what recurred</h2>
<table class="ledger"><thead><tr><th>Date</th><th>RO</th><th>Component — action &amp; their stated basis</th><th>Recurred</th></tr></thead>
<tbody>{lrows}</tbody></table>

<h2>Timeline</h2>
<p class="sub" style="margin-top:-4px">Hover any mark; click for detail. Red bar: recall from federal filing to the work
on this car (white tick: remedy became available). Grey: at the dealership. Blue: owner reports and dated captures.</p>
<svg id="tlsvg" viewBox="0 0 1000 252" style="width:100%;background:#fff;border:1px solid var(--line);border-radius:8px;">{''.join(S)}</svg>

<h2>Exemplar recordings</h2>
<div class="players">{players}</div>

<h2>The full record — 61 dated captures and 14 documents (sample shown)</h2>
<div class="chips"><span class="chip on" data-f="all">All</span><span class="chip" data-f="displays">Displays</span>
<span class="chip" data-f="door_latch">Door latch</span><span class="chip" data-f="charging">Charging</span>
<span class="chip" data-f="paper">Documents</span></div>
<div class="grid">{''.join(cells)}</div>

<h2>Diagnostic records requested</h2>
<div class="ask"><b>The request.</b> For each problem, the manufacturer has been asked to produce its diagnostic
session logs, stored fault memory, and telematics for the full calendar day of each of the <b>58 recorded incident
timestamps</b> (Displays — 21 &middot; Door latch — 14 &middot; Charging — 17 &middot; Other electrical — 6), the complete
logs from every service visit, and to treat any fault found in those records as having been reported by the owners.
<a href="placeholder-document.pdf" target="_blank">The request document (placeholder PDF)</a>.</div>

<h2>Downloads</h2>
<a class="dl" href="placeholder-document.pdf" target="_blank">&#9636; The case file (PDF) — placeholder</a>
<a class="dl" href="placeholder-document.pdf" target="_blank">&#9636; Diagnostic-records request — placeholder</a>

<footer>This page is a <b>fictional demonstration</b> of the case-file format produced by the
<a href="https://github.com/buildtherecord/lemon-case-file">lemon-case-file</a> method — see the prompts and
deploy kit there to build a real one from your own records. Real case files are served behind a password with
an access log (see <code>site/</code>); this demo is public because it contains nothing real.
Fact pattern modeled on published appellate opinions listed in
<a href="https://github.com/buildtherecord/lemon-case-file/blob/main/EXEMPLARS.md">EXEMPLARS.md</a>.</footer>
</div>
<div id="tip"></div>
<div id="evm"><div class="box"><button class="evm-x">&#10005;</button>
<div class="evm-date"></div><div class="evm-title"></div><a class="evm-link" target="_blank" rel="noopener"></a></div></div>
<script>
{TTJS}
(function(){{
  var tip=document.getElementById('tip');
  document.querySelectorAll('.tlp').forEach(function(el){{
    el.addEventListener('mousemove',function(ev){{
      var d=TT[+el.dataset.i]; if(!d)return;
      tip.innerHTML='<b>'+d.d+'</b><br>'+d.t; tip.style.display='block';
      tip.style.left=Math.min(ev.clientX+14,window.innerWidth-360)+'px';
      tip.style.top=(ev.clientY+16)+'px';
    }});
    el.addEventListener('mouseleave',function(){{tip.style.display='none';}});
    el.addEventListener('click',function(){{
      var d=TT[+el.dataset.i]; if(!d)return;
      var evm=document.getElementById('evm');
      evm.querySelector('.evm-date').textContent=d.d.replace(/&#8594;/g,'\\u2192');
      evm.querySelector('.evm-title').textContent=d.t;
      var a=evm.querySelector('.evm-link');
      if(d.u){{a.href=d.u;a.textContent=d.ul||'Open the document';a.style.display='inline-block';}}
      else{{a.style.display='none';}}
      evm.style.display='flex';
    }});
  }});
  var evm=document.getElementById('evm');
  function close(){{evm.style.display='none';}}
  evm.addEventListener('click',function(ev){{if(ev.target===evm)close();}});
  evm.querySelector('.evm-x').addEventListener('click',close);
  document.addEventListener('keydown',function(ev){{if(ev.key==='Escape')close();}});
  document.querySelectorAll('.chip').forEach(function(ch){{
    ch.addEventListener('click',function(){{
      document.querySelectorAll('.chip').forEach(function(c){{c.classList.remove('on');}});
      ch.classList.add('on');
      var f=ch.dataset.f;
      document.querySelectorAll('.gcell').forEach(function(c){{
        c.style.display=(f==='all'||c.dataset.cat===f)?'':'none';
      }});
    }});
  }});
}})();
</script></body></html>"""
open("docs/index.html", "w").write(HTML)
print("demo bytes:", len(HTML), "| TT entries:", len(TT), "| grid cells:", sum(1 for r in GRID if r[1]))
