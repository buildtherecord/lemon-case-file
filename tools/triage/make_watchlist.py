#!/usr/bin/env python3
"""Build the watch list: a single offline web page where the owner watches each flagged
item and records one answer. Nothing leaves the computer; there is no network call.

  python3 make_watchlist.py review-queue.csv --title "My watch list" --out watchlist.html

review-queue.csv columns (extra columns are ignored):
  id            the item's catalogue id
  title         one line: what the item is
  when          date and time
  current_grade the grade now ("" if none yet)
  proposed_grade the assistant's proposal ("" if none)
  watch_for     the ONE question to answer and where to look (seconds if known)
  frames_note   what the assistant could see in sampled frames (and could not)
  media         path to a review copy, relative to the html file (see proxy_clips.py)
  original      optional: where the full-quality original lives
  flags         optional: sensitive content, settlement scope, conflicting timestamps

Open watchlist.html in a browser next to the media folder. Answers save in the browser as
you go. "Download answers.csv" exports them for apply_answers.py.
A good queue is short, ordered by how likely each item is to change grade, and holds only
what stills could not settle: movement, sound, and anything the assistant is unsure of.
"""
import argparse, csv, html, json

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f1f1ee;--surface:#fff;--ink:#16181a;--muted:#5c6166;--line:#d4d6d8;--quote:#f4f5f5;--accent:#1d5f73;--accent-ink:#fff;--warn:#8a4b00;--warn-bg:#fbeed9}
@media (prefers-color-scheme:dark){:root{--bg:#121416;--surface:#1b1e21;--ink:#e8eaeb;--muted:#98a0a6;--line:#2c3236;--quote:#22272a;--accent:#59b3c9;--accent-ink:#06222a;--warn:#f0b35a;--warn-bg:#3a2b12}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;padding:0 16px 64px}
.wrap{max-width:760px;margin:0 auto}
h1{font-size:26px;margin:24px 0 6px}
p.lede{margin:0 0 12px;color:var(--muted);max-width:62ch}
.rubric{display:grid;gap:4px;font-size:13.5px;margin:10px 0}
.rubric b{display:inline-block;min-width:2.2em}
.bar{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:5}
.meter{flex:1;min-width:140px;height:6px;background:var(--line);border-radius:3px;overflow:hidden}
.meter i{display:block;height:100%;width:0;background:var(--accent)}
.count{font-family:ui-monospace,monospace;font-size:12.5px;color:var(--muted)}
button,a.btn{font:inherit;cursor:pointer}
.btn{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:6px;padding:6px 12px;font-size:13.5px;text-decoration:none;display:inline-block}
.card{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:14px 16px;margin:12px 0;display:grid;gap:10px;min-width:0}
.head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.cid{font-family:ui-monospace,monospace;font-weight:600;font-size:13px;background:var(--quote);padding:2px 7px;border-radius:4px}
.ttl{font-weight:600;overflow-wrap:anywhere}
.when{margin-left:auto;font-family:ui-monospace,monospace;font-size:12px;color:var(--muted)}
video{width:100%;max-height:62vh;background:#000;border-radius:4px}
.look{background:var(--quote);border-radius:4px;padding:8px 10px;overflow-wrap:anywhere}
.small{font-size:13px;color:var(--muted);overflow-wrap:anywhere}
.lab{display:block;font-family:ui-monospace,monospace;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:2px}
.flag{font-size:12.5px;color:var(--warn);background:var(--warn-bg);padding:4px 8px;border-radius:4px}
.seg{display:flex;gap:6px;flex-wrap:wrap}
.seg button{border:1px solid var(--line);background:var(--surface);color:var(--ink);padding:6px 11px;border-radius:6px;font-size:13.5px}
.seg button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.two{display:grid;grid-template-columns:130px 1fr;gap:10px}
@media (max-width:480px){.two{grid-template-columns:1fr}}
label{font-family:ui-monospace,monospace;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);display:block;margin-bottom:3px}
input[type=text],textarea{width:100%;font:inherit;font-size:14px;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:8px 10px}
textarea{min-height:54px;resize:vertical}
.saved{font-family:ui-monospace,monospace;font-size:11.5px;color:var(--muted);min-height:1em}
.out textarea{min-height:140px;font-family:ui-monospace,monospace;font-size:12px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style></head><body><div class="wrap">
<h1>__TITLE__</h1>
<p class="lede">Watch each item, choose what you saw, and note the second it happens. Your answers save in this browser as you go. When you are done, download the answers and hand them to the assistant.</p>
<div class="rubric">
<div><b>A</b> Shown on camera. The fault itself is visible; a caption may explain it.</div>
<div><b>B1</b> Supporting, described. You describe the fault; the recording does not clearly show it.</div>
<div><b>B2</b> Supporting, context. Context, a comparison, a retake, or a timestamp to check on a recording that documents an incident.</div>
<div><b>C</b> Weaker. Little usable content, no clear link to a defect, or a clip that is only a timestamp.</div>
</div>
<div class="bar"><div class="meter"><i id="m"></i></div><span class="count" id="c"></span>
<a class="btn" id="dl" download="answers.csv">Download answers.csv</a><button class="btn" id="cp" type="button">Copy answers</button></div>
<div id="cards"></div>
<div class="out" id="out" hidden><textarea id="ta" readonly aria-label="Answers as CSV"></textarea></div>
</div>
<script>
const ITEMS=__ITEMS__;
const KEY='watchlist:'+__KEY__;
const CHOICES=[['A','A · shown on camera'],['B1','B1 · described'],['B2','B2 · context or timestamp'],['C','C · weaker'],['FOLD','Same footage as another item'],['UNSURE','Cannot tell']];
let state={};try{state=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const $=id=>document.getElementById(id);
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
function persist(){try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}refresh()}
function code(s){if(!s||!s.g)return '';if(s.g==='FOLD')return 'FOLD:'+(s.fold||'').trim();return s.g}
function csv(){const q=v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"';
  return ['id,grade,sec,note'].concat(ITEMS.filter(i=>state[i.id]&&state[i.id].g).map(i=>{const s=state[i.id];return [q(i.id),q(code(s)),q(s.sec),q(s.note)].join(',')})).join('\\n')+'\\n'}
function refresh(){const n=ITEMS.filter(i=>state[i.id]&&state[i.id].g).length;$('c').textContent=n+' of '+ITEMS.length;$('m').style.width=(100*n/Math.max(1,ITEMS.length))+'%';
  const t=csv();$('dl').href='data:text/csv;charset=utf-8,'+encodeURIComponent(t);$('ta').value=t}
function field(it,key,label,tag,ph){const w=el('div');const l=el('label',null,label);const f=document.createElement(tag);f.id=key+'-'+it.id;l.htmlFor=f.id;
  if(tag==='input')f.type='text';f.placeholder=ph||'';f.value=(state[it.id]&&state[it.id][key])||'';
  f.oninput=()=>{state[it.id]=Object.assign(state[it.id]||{},{[key]:f.value});persist()};w.append(l,f);return w}
ITEMS.forEach(it=>{const card=el('div','card');const h=el('div','head');
  h.append(el('span','cid',it.id),el('span','ttl',it.title));if(it.when)h.append(el('span','when',it.when));card.appendChild(h);
  const g=[it.current_grade&&('now '+it.current_grade),it.proposed_grade&&('proposed '+it.proposed_grade)].filter(Boolean).join('   ');
  if(g)card.appendChild(el('div','small',g));
  if(it.media){const v=document.createElement('video');v.controls=true;v.preload='metadata';v.playsInline=true;v.src=it.media;card.appendChild(v)}
  const lk=el('div','look');lk.append(el('span','lab','Watch for'),document.createTextNode(it.watch_for||''));card.appendChild(lk);
  if(it.frames_note){const f=el('div','small');f.append(el('span','lab','What the sampled frames showed'),document.createTextNode(it.frames_note));card.appendChild(f)}
  if(it.flags)card.appendChild(el('div','flag',it.flags));
  if(it.original){card.appendChild(el('div','small','Original: '+it.original))}
  const seg=el('div','seg');const foldBox=field(it,'fold','Fold into which item id?','input','e.g. 020');foldBox.hidden=true;
  const sync=()=>{const s=state[it.id]||{};[...seg.children].forEach(b=>b.setAttribute('aria-pressed',String(s.g===b.dataset.g)));foldBox.hidden=s.g!=='FOLD'};
  CHOICES.forEach(([k,t])=>{const b=el('button',null,t);b.type='button';b.dataset.g=k;b.onclick=()=>{state[it.id]=Object.assign(state[it.id]||{},{g:k});sync();persist()};seg.appendChild(b)});
  card.appendChild(seg);card.appendChild(foldBox);
  const two=el('div','two');two.append(field(it,'sec','Second(s)','input','e.g. 12'),field(it,'note','What you saw or heard','textarea'));card.appendChild(two);
  sync();$('cards').appendChild(card)});
$('cp').onclick=async()=>{try{await navigator.clipboard.writeText(csv());$('cp').textContent='Copied'}catch(e){$('out').hidden=false;$('ta').select()}setTimeout(()=>{$('cp').textContent='Copy answers'},1600)};
refresh();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('queue')
    ap.add_argument('--title', default='Watch list')
    ap.add_argument('--out', default='watchlist.html')
    a = ap.parse_args()
    with open(a.queue, newline='', encoding='utf-8') as f:
        items = [{k: (v or '').strip() for k, v in r.items()} for r in csv.DictReader(f)]
    if not items:
        raise SystemExit('The queue is empty: nothing to watch.')
    for i in items:
        if not i.get('id') or not i.get('watch_for'):
            raise SystemExit(f'Every item needs an id and a watch_for question (row: {i.get("id") or "?"}).')
    data = json.dumps(items, ensure_ascii=False).replace('</', '<\\/')
    page = (PAGE.replace('__TITLE__', html.escape(a.title))
                .replace('__ITEMS__', data)
                .replace('__KEY__', json.dumps(a.title)))
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'wrote {a.out}: {len(items)} items')


if __name__ == '__main__':
    main()
