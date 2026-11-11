#!/usr/bin/env python3
"""Generate the INWARD pages (the full linked record) from ONE record file.

  python3 build_views.py record.json OUTDIR [--strict]

The record's shape is written in schema/record.schema.json; example/seed.py writes working examples
(python3 example/seed.py OUTDIR). Run python3 checks.py record.json to see every problem without building.

Pages (static HTML, no JavaScript needed):
  index.html       one-page brief: updated stamp, deadlines (claimant-entered), counts (computed), cast, gaps
  chronology.html  one row per fact; every fact links to its sources, people, and topics
  exhibits.html    exhibit index; exhibits/<id>.html shows what cites each exhibit (two-way links)
  people/<id>.html every fact and exhibit one person appears in
  issues/<id>.html every fact on one topic, side by side
  gaps.html        facts with no document, exhibits never cited, quotes that could not be checked, deadlines nobody has confirmed

Before anything is written, checks.py runs (the same checker build_home.py and the case converters run). The build stops, exit 1, with plain
sentences naming the fact or exhibit, when: the record does not match the schema; a documented fact names no document; a quote is not word for
word in its source; advice or advocacy wording appears in what the claimant or assistant wrote (never in documents or inside quotation
marks); a number with a unit is typed instead of computed; a deadline was computed; an id is unsafe. Held-back items are never rendered.
--strict also fails on quotes that cannot be checked (no document text), unknown fields and the other pre-send checks.

The output folder is built next to the real one and swapped in, so a failed build leaves the old folder as it was. A folder is replaced only if
this tool made it (it carries a .btr-output marker file) or it is empty; any other folder is refused.
"""
import argparse, json, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks
from checks import STATUS, BANNER, display_status, expand, make_resolver, is_recording
from btr_common import (BuildError, esc, qurl, fmt_date, fact_when, sorted_facts, days_between, is_http, start_build, swap_into_place, check_output_target,
                    remove_made_dir)

fmt = fmt_date
AUTHOR_WORDS = {'claimant': 'Claimant', 'other_side': 'Other side', 'third_party': 'Third party'}

CSS = """:root{--bg:#fff;--ink:#111;--muted:#555;--line:#ccc;--soft:#f3f3f3;--a:#8a4b00;--c:#1d4f8a}
@media (prefers-color-scheme:dark){:root{--bg:#111;--ink:#eee;--muted:#aaa;--line:#444;--soft:#1b1b1b;--a:#f0b35a;--c:#7fb2ee}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Georgia,serif;padding:0 18px 60px}main{max-width:900px;margin:0 auto}
h1{font:600 26px/1.2 system-ui,sans-serif;margin:28px 0 6px}h2{font:600 19px/1.3 system-ui,sans-serif;margin:34px 0 10px;border-top:1px solid var(--line);padding-top:16px}
nav{font:14px system-ui,sans-serif;display:flex;gap:4px 10px;flex-wrap:wrap;padding:4px 0;border-bottom:1px solid var(--line)}nav a{display:inline-block;padding:13px 6px}nav a[aria-current=page]{font-weight:700;text-decoration-thickness:2px}
a{color:inherit}a:focus-visible,summary:focus-visible{outline:2px solid var(--c);outline-offset:2px;border-radius:2px}
.upd{font:14px system-ui,sans-serif;border:1px solid var(--line);border-radius:4px;display:inline-block;padding:5px 10px;margin:6px 0}
.banner{background:var(--soft);padding:10px 14px;border-radius:4px;font:14px/1.5 system-ui,sans-serif}.muted{color:var(--muted)}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font:14.5px/1.5 system-ui,sans-serif}th,td{text-align:left;vertical-align:top;padding:8px 9px;border-top:1px solid var(--line)}
th{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}td.id{font-family:ui-monospace,monospace;font-size:13px;white-space:nowrap}
.s{font-size:12px;font-weight:600;border:1px solid var(--line);padding:1px 7px;border-radius:3px;display:inline-block}.s-account,.s-claimant_doc{color:var(--a);border-color:var(--a)}.s-disputed{color:var(--c);border-color:var(--c)}.s-open{border-style:dashed}
.q{border-left:3px solid var(--line);padding-left:10px;color:var(--muted);margin:4px 0}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.tile{border:1px solid var(--line);border-radius:4px;padding:10px 12px;font-family:system-ui,sans-serif}.tile b{font-size:24px;display:block}.tile span{font-size:13px;color:var(--muted)}.tile span,.tile small{display:block}.tile small{margin-top:4px}
tr.child td{font-size:13.5px;color:var(--muted);border-top:1px dotted var(--line)}tr.child td.id{padding-left:22px}
@media (max-width:640px){table.cards thead,table.cards tr:first-child:has(th){display:none}table.cards tr{display:block;border-top:1px solid var(--line);padding:10px 0}table.cards td{display:block;border:0;padding:2px 0}table.cards td[data-l]::before{content:attr(data-l);display:block;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
footer{margin-top:44px;font:12.5px system-ui,sans-serif;color:var(--muted);border-top:1px solid var(--line);padding-top:12px}"""


NAV = (('index', 'Brief'), ('chronology', 'Chronology'), ('money', 'Money'), ('exhibits', 'Exhibits'), ('gaps', 'Gaps'))


def page(meta, title, body, depth=0, current=None):
    p = '../' * depth
    nav = '<nav aria-label="Pages of this record">' + ''.join(f'<a href="{p}{k}.html"{" aria-current=page" if k == current else ""}>{t}</a>' for k, t in NAV) + '</nav>'
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><meta name="robots" content="noindex,nofollow"><style>{CSS}</style></head><body><main>{nav}'
            f'<h1>{esc(title)}</h1><p class="upd">Last updated <b>{esc(meta["updated"])}</b></p><p class="banner">{esc(BANNER)}</p>{body}'
            f'<footer>Generated from one record. Counts are computed. {esc(meta.get("footer", ""))}</footer></main></body></html>')


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def build(rec, out, strict=False):
    rec, R = checks.check_record(rec, 'record', strict)
    for w in R.warnings:
        print(f'note: {w}')
    if not R.ok:
        print(checks.format_failure('', R).strip())
        return 1
    check_output_target(out)
    meta = rec['meta']
    people = {p['id']: p for p in rec.get('people', [])}
    exhibits = {e['id']: e for e in rec.get('exhibits', [])}
    issues = {i['id']: i for i in rec.get('issues', [])}
    all_facts = sorted_facts(rec['facts'])
    by_id = {f['id']: f for f in all_facts}
    parent = {f['id']: f.get('excerpt_of') or f.get('fold_into') for f in all_facts if f.get('excerpt_of') or f.get('fold_into')}
    kids = defaultdict(list)
    for f in all_facts:
        if f['id'] in parent:
            kids[parent[f['id']]].append(f)
    facts = [f for f in all_facts if f['id'] not in parent]      # what is counted
    ds = {f['id']: display_status(f, exhibits, meta.get('claimant_label')) for f in all_facts}
    top_ex = [e for e in exhibits.values() if not e.get('excerpt_of') and not e.get('fold_into')]
    n = lambda key: sum(1 for f in facts if ds[f['id']][0] == key)
    counts = {'facts': len(facts), 'documents': sum(1 for e in top_ex if not is_recording(e)), 'recordings': sum(1 for e in top_ex if is_recording(e)),
              'documented': n('documented'), 'claimant_docs': n('claimant_doc'), 'account': n('account'), 'disputed': n('disputed'), 'open': n('open')}
    intervals = {i['id']: i for i in rec.get('intervals', []) if i.get('id')}
    ledger = sorted(rec.get('ledger', []), key=lambda e: (e['date'], e['id']))
    auths = {a['id']: a for a in rec.get('authorities', [])}
    resolver = make_resolver(by_id, intervals, counts, exhibits, ledger, auths)
    T = lambda s: esc(expand(s, resolver))

    cited = defaultdict(list)
    for f in all_facts:
        for s in f.get('sources', []):
            if f['id'] not in cited[s['ex']]:
                cited[s['ex']].append(f['id'])

    def src_links(f, depth=0):
        p = '../' * depth
        return '<br>'.join(f'<a href="{p}exhibits/{qurl(s["ex"])}.html#cited-{esc(f["id"])}">{esc(exhibits[s["ex"]]["title"])}'
                           f'{(", " + esc(s["loc"])) if s.get("loc") else ""}</a>' for s in f.get('sources', [])) or '<span class="muted">none yet</span>'

    def ppl_links(f, depth=0):
        p = '../' * depth
        return ', '.join(f'<a href="{p}people/{qurl(x)}.html">{esc(people[x]["name"])}</a>' for x in f.get('people', []))

    def row(f, depth=0, child=None):
        key, words = ds[f['id']]
        st = f'<span class="s s-{key}">{esc(words)}</span>'
        note = ''
        if child:
            note = f'<span class="muted">{"Excerpt of" if child == "excerpt" else "Same item as"} <a href="#{esc(parent[f["id"]])}">{esc(parent[f["id"]])}</a>{"" if child == "excerpt" else " (folded, not counted)"}. </span>'
        who = f'<br><small>{ppl_links(f, depth)}</small>' if f.get('people') else ''
        return (f'<tr id="{esc(f["id"])}"{" class=child" if child else ""}><td class="id">{esc(f["id"])}</td><td data-l="When">{esc(fact_when(f))}</td>'
                f'<td>{note}{T(f["text"])}{who}</td><td data-l="Status">{st}</td><td data-l="Source">{src_links(f, depth)}</td></tr>')

    def rows(fs, depth=0):
        out_ = []
        for f in fs:
            out_.append(row(f, depth))
            for k in kids.get(f['id'], []):
                out_.append(row(k, depth, 'excerpt' if k.get('excerpt_of') else 'folded'))
        return ''.join(out_)

    head = '<tr><th>ID</th><th>When</th><th>What</th><th>Status</th><th>Source</th></tr>'
    tmp = start_build(out)
    try:
        write(tmp, 'chronology.html', page(meta, 'Chronology', f'<div class="tw"><table class="cards">{head}{rows(facts)}</table></div>', 0, 'chronology'))
        for eid, e in exhibits.items():
            fl = ''
            if e.get('file'):
                href = e['file'] if is_http(e['file']) else '../files/' + qurl(e['file'])
                fl = f'<p><a href="{esc(href)}">Open the original file</a></p>'
            elif e.get('link'):
                fl = f'<p><a href="{esc(e["link"])}">Open the linked page</a></p>'
            erows = ''.join(
                f'<tr id="cited-{esc(x)}"><td class="id"><a href="../chronology.html#{esc(x)}">{esc(x)}</a></td><td data-l="Statement">{T(by_id[x]["text"])}</td>'
                f'<td data-l="Quoted">{"".join("<div class=q>" + esc(s["quote"]) + "</div>" for s in by_id[x]["sources"] if s["ex"] == eid and s.get("quote"))}</td></tr>' for x in cited.get(eid, []))
            facts_html = f'<div class="tw"><table class="cards"><tr><th>Fact</th><th>Statement</th><th>Quoted</th></tr>{erows}</table></div>' if erows else '<p class="muted">Not cited yet.</p>'
            bits = [e.get('kind') or '', AUTHOR_WORDS.get(e.get('author'), ''), fmt_date(e.get('date', ''), e.get('date_precision')) + (f' to {fmt_date(e["end"])}' if e.get('end') else ''),
                    'On the outward page' if e.get('share') is True else 'Not on the outward page']
            body = f'<p class="muted">{esc(" · ".join(b for b in bits if b))}</p>{fl}<h2>Facts that cite this exhibit</h2>{facts_html}'
            write(tmp, f'exhibits/{eid}.html', page(meta, f'{eid}: {e["title"]}', body, 1, 'exhibits'))
        erows = ''
        for eid, e in sorted(exhibits.items(), key=lambda kv: (kv[1].get('date', ''), kv[0])):
            note = f'Excerpt of {e["excerpt_of"]}' if e.get('excerpt_of') else (f'Same item as {e["fold_into"]} (folded)' if e.get('fold_into') else '')
            erows += (f'<tr><td class="id">{esc(eid)}</td><td data-l="Document"><a href="exhibits/{qurl(eid)}.html">{esc(e["title"])}</a>{"<br><small class=muted>" + esc(note) + "</small>" if note else ""}</td>'
                      f'<td data-l="Type">{esc(e.get("kind") or "")}</td><td data-l="Author">{esc(AUTHOR_WORDS.get(e.get("author"), ""))}</td><td data-l="Date">{esc(fmt_date(e.get("date", ""), e.get("date_precision")))}</td>'
                      f'<td data-l="Cited by">{len(cited.get(eid, []))}</td><td data-l="Outward page">{"Shared" if e.get("share") is True else "Not shared"}</td></tr>')
        write(tmp, 'exhibits.html', page(meta, 'Exhibits', f'<div class="tw"><table class="cards"><tr><th>ID</th><th>Document</th><th>Type</th><th>Author</th><th>Date</th><th>Cited by</th><th>Outward page</th></tr>{erows}</table></div>', 0, 'exhibits'))
        for pid, p in people.items():
            mine = [f for f in facts if pid in f.get('people', [])]
            body = f'<p class="muted">{esc(p.get("role", ""))}</p><div class="tw"><table class="cards">{head}{rows(mine, 1)}</table></div>' if mine else '<p class="muted">Not in any fact yet.</p>'
            write(tmp, f'people/{pid}.html', page(meta, p['name'], body, 1))
        for iid, i in issues.items():
            mine = [f for f in facts if iid in f.get('issues', [])]
            body = f'<div class="tw"><table class="cards">{head}{rows(mine, 1)}</table></div>' if mine else '<p class="muted">No facts on this topic yet.</p>'
            write(tmp, f'issues/{iid}.html', page(meta, i['label'], body, 1))

        no_doc = [f for f in facts if not f.get('sources')]
        uncited = [e for e in exhibits if not cited.get(e)]
        no_confirm = [d for d in rec.get('deadlines', []) if not d.get('confirmed_by')]
        thin = [i for i in issues if not any(ds[f['id']][0] in ('documented', 'claimant_doc') for f in facts if i in f.get('issues', []))]
        li = lambda items: ('<ul>' + ''.join(items) + '</ul>') if items else '<p class="muted">None.</p>'
        gbody = ('<h2>Facts with no document yet</h2>' + li([f'<li><a href="chronology.html#{esc(f["id"])}">{esc(f["id"])}</a> {T(f["text"])}</li>' for f in no_doc])
                 + '<h2>Exhibits no fact cites</h2>' + li([f'<li><a href="exhibits/{qurl(e)}.html">{esc(exhibits[e]["title"])}</a></li>' for e in uncited])
                 + '<h2>Topics with no documented fact</h2>' + li([f'<li><a href="issues/{qurl(i)}.html">{esc(issues[i]["label"])}</a></li>' for i in thin])
                 + f'<h2>Quotes the tool could not check</h2><p class="muted">{R.verified} quotes were checked word for word and matched. {len(R.unverified)} could not be checked, because the document text is not in the record.</p>'
                 + li([f'<li>{esc(u)}</li>' for u in R.unverified])
                 + '<h2>Deadlines nobody has confirmed</h2>' + ('<ul>' + ''.join(f'<li>{esc(d["label"])}: {esc(deadline_when(d))} (where it is written: {esc(d["source"])})</li>' for d in no_confirm) + '</ul>'
                                                                 if no_confirm else '<p class="muted">None entered, or all confirmed. If none was entered, that does not mean none applies.</p>'))
        write(tmp, 'gaps.html', page(meta, 'Gaps', gbody, 0, 'gaps'))
        write(tmp, 'money.html', page(meta, 'Money', money_page(rec, people, exhibits, by_id, ledger, auths, T), 0, 'money'))

        ivs = []
        for iv in rec.get('intervals', []):
            a, b = by_id[iv['a']], by_id[iv['b']]
            ivs.append(f'<div class="tile"><b>{days_between(a, b)} days</b><span>{T(iv["label"])}</span><small class="muted"><a href="chronology.html#{esc(a["id"])}">{esc(a["id"])}</a> to '
                       f'<a href="chronology.html#{esc(b["id"])}">{esc(b["id"])}</a> (computed)</small></div>')
        shared = sum(1 for e in top_ex if e.get('share') is True)
        if ledger:
            ivs.append(f'<div class="tile"><b>{esc(checks.fmt_money(sum((checks.entry_value(e) for e in ledger), checks.Decimal(0))))}</b><span>in {len(ledger)} ledger rows</span>'
                       f'<small class="muted"><a href="money.html">added up from the rows</a> (computed)</small></div>')
        tiles = ''.join(ivs) + ''.join(f'<div class="tile"><b>{v}</b><span>{esc(k)}</span></div>' for k, v in [
            ('facts', counts['facts']), ('show in a document', counts['documented']), ("per the claimant's own documents", counts['claimant_docs']), ("claimant's account", counts['account']),
            ('disputed', counts['disputed']), ('open questions', counts['open']), ('exhibits', len(top_ex)), ('exhibits marked for the outward page', shared)])
        dl = rec.get('deadlines', [])
        dlh = ('<div class="tw"><table class="cards"><tr><th>Deadline the claimant reports</th><th>Date or the document\'s own words</th><th>Where it is written</th><th>Confirmed by</th></tr>' + ''.join(
            f'<tr><td data-l="Deadline the claimant reports">{esc(d["label"])}</td><td data-l="Date or the document\'s own words">{esc(deadline_when(d))}</td><td data-l="Where it is written">{esc(d["source"])}</td><td data-l="Confirmed by">{esc(d.get("confirmed_by") or "nobody yet")}</td></tr>' for d in dl) + '</table></div>') if dl else \
            '<p>The claimant has not entered a deadline. <b>That does not mean none applies.</b></p>'
        cast = ''.join(f'<li><a href="people/{qurl(pid)}.html">{esc(p["name"])}</a> — {esc(p.get("role", ""))}</li>' for pid, p in people.items())
        ab = meta.get('absences')
        brief = [('Asked for', meta.get('ask')), ('Amount involved (claimant-reported)', meta.get('amount')), ('Jurisdiction', meta.get('jurisdiction')),
                 ('Prior or current lawyer', meta.get('lawyer', 'none reported')), ('Sent to or signed with the other side', meta.get('sent_to_other_side', 'nothing reported')),
                 ('Offers or releases presented', meta.get('offers', 'none reported')), ('Not found in any document', '; '.join(ab) if isinstance(ab, list) else ab)]
        st = meta.get('standing') or {}
        if st or ledger or auths:
            rh = people.get(st.get('rights_holder'), {}).get('name') if st.get('rights_holder') else None
            brief += [('Whose claim (as the claimant understands it)', (rh or 'not entered') + (f" (confirmed by {st['confirmed_by']})" if st.get('confirmed_by') else ' (nobody has confirmed this yet)')),
                      ('Who is building the record', st.get('builder_role')), ('How the rights holder agreed', st.get('permission'))]
        bt = '<table>' + ''.join(f'<tr><td><b>{esc(k)}</b></td><td>{esc(v or "not entered")}</td></tr>' for k, v in brief) + '</table>'
        body = (f'<p>{T(meta["summary"])}</p><h2>At a glance</h2><div class="tiles">{tiles}</div><h2>For intake</h2>{bt}'
                f'<h2>Deadlines</h2>{dlh}<h2>Cast</h2><ul>{cast}</ul>'
                f'<h2>Open gaps</h2><p>{len(no_doc)} facts without a document; {len(uncited)} exhibits not cited; {len(R.unverified)} quotes that could not be checked; {len(no_confirm)} deadlines unconfirmed. <a href="gaps.html">See gaps</a>.</p>')
        write(tmp, 'index.html', page(meta, meta['title'], body, 0, 'index'))
        write(tmp, 'counts.json', json.dumps({**counts, 'exhibits': len(top_ex), 'shared': shared, 'no_doc': len(no_doc), 'quotes_verified': R.verified, 'quotes_unverified': len(R.unverified)}))
        swap_into_place(tmp, out)
    except BaseException:
        if os.path.isdir(tmp):
            remove_made_dir(tmp)
        raise
    print(f'ok: {counts["facts"]} facts ({counts["documented"]} documented, {counts["claimant_docs"]} per the claimant\'s own documents, {counts["account"]} account, '
          f'{counts["disputed"]} disputed, {counts["open"]} open), {len(top_ex)} exhibits, {len(no_doc)} without a document; '
          f'quotes: {R.verified} verified, {len(R.unverified)} could not be checked -> {out}')
    return 0


POS_WORDS = {'before': 'dated before {a} starts', 'within': 'dated inside the dates of {a}', 'on the end date': 'dated on the end date recorded for {a}',
             'after': 'dated after the end recorded for {a}'}


def money_page(rec, people, exhibits, by_id, ledger, auths, T):
    """The ledger and the authority windows. Positions are by date alone; the page never says a transaction was or was not allowed."""
    who = lambda x: esc(people[x]['name']) if x in people else esc(x or '')
    src = lambda e: '<br>'.join(f'<a href="exhibits/{qurl(s["ex"])}.html">{esc(exhibits[s["ex"]]["title"])}{(", " + esc(s["loc"])) if s.get("loc") else ""}</a>'
                                for s in e['sources'] if s['ex'] in exhibits)
    out = ['<p class="banner">Every row comes from a document, and every total is added up from the rows. Where a row falls against an authority\'s dates is worked out '
           'from the dates alone. Whether a transaction was allowed is a question for a lawyer; this page does not answer it.</p>']
    if auths:
        out.append('<h2>Who could act for whom</h2><div class="tw"><table class="cards"><tr><th>ID</th><th>Who</th><th>For</th><th>Document</th><th>Starts</th><th>Ends (as recorded)</th></tr>')
        for aid, a in auths.items():
            f0, f1 = by_id.get(a['from']), by_id.get(a.get('to'))
            doc = f'<a href="exhibits/{qurl(a["ex"])}.html">{T(a["kind"])}</a>' if a.get('ex') in exhibits else T(a['kind'])
            out.append(f'<tr><td class="id">{esc(aid)}</td><td data-l="Who">{who(a["holder"])}</td><td data-l="For">{who(a.get("for"))}</td><td data-l="Document">{doc}</td>'
                       f'<td data-l="Starts"><a href="chronology.html#{esc(f0["id"])}">{esc(fact_when(f0))}</a></td>'
                       f'<td data-l="Ends (as recorded)">' + (f'<a href="chronology.html#{esc(f1["id"])}">{esc(fact_when(f1))}</a>: {T(f1["text"])}' if f1 else '<span class="muted">no end recorded</span>') + '</td></tr>')
        out.append('</table></div>')
    if not ledger:
        out.append('<p class="muted">No ledger rows yet.</p>')
        return ''.join(out)
    total = sum((checks.entry_value(e) for e in ledger), checks.Decimal(0))
    out.append(f'<h2>Ledger</h2><p>{len(ledger)} rows, {esc(checks.fmt_money(total))} in all (computed).</p>')
    out.append('<div class="tw"><table class="cards"><tr><th>ID</th><th>Date</th><th>Amount</th><th>From</th><th>To</th><th>By</th><th>Against the authority dates</th><th>Source</th></tr>')
    for e in ledger:
        pos = ''
        for aid, a in auths.items():
            if e.get('by') and a['holder'] != e['by']:
                continue
            if e.get('under') and e['under'] != aid:
                continue
            if not e.get('by') and not e.get('under'):
                continue
            pos += f'<div>{esc(POS_WORDS[checks.entry_position(e, a, by_id)].format(a=aid))}</div>'
        st = checks.entry_status(e)
        out.append(f'<tr id="{esc(e["id"])}"><td class="id">{esc(e["id"])}</td><td data-l="Date">{esc(fmt_date(e["date"]))}</td><td data-l="Amount">${esc(e["amount"])}'
                   + ('' if st == 'documented' else f' <span class="s s-{esc(st)}">{esc(STATUS.get(st, st))}</span>') + '</td>'
                   f'<td data-l="From">{who(e.get("from"))}</td><td data-l="To">{who(e.get("to"))}</td><td data-l="By">{who(e.get("by"))}{("<br><small class=muted>" + esc(e["method"]) + "</small>") if e.get("method") else ""}</td>'
                   f'<td data-l="Against the authority dates">{pos or "<span class=muted>none recorded</span>"}</td><td data-l="Source">{src(e)}</td></tr>')
    out.append('</table></div>')
    groups = []
    for key, label in (('to', 'Went to'), ('by', 'Made by')):
        vals = sorted({e.get(key) for e in ledger if e.get(key)})
        for v in vals:
            rows = [e for e in ledger if e.get(key) == v]
            groups.append(f'<tr><td>{label} {who(v)}</td><td>{len(rows)}</td><td>{esc(checks.fmt_money(sum((checks.entry_value(e) for e in rows), checks.Decimal(0))))}</td></tr>')
    for aid, a in auths.items():
        for posn in ('before', 'within', 'on the end date', 'after'):
            rows = [e for e in ledger if (e.get('under') == aid or (e.get('by') == a['holder'] and not e.get('under'))) and checks.entry_position(e, a, by_id) == posn]
            if rows:
                groups.append(f'<tr><td>Made by {who(a["holder"])}, {esc(POS_WORDS[posn].format(a=aid))}</td><td>{len(rows)}</td><td>{esc(checks.fmt_money(sum((checks.entry_value(e) for e in rows), checks.Decimal(0))))}</td></tr>')
    if groups:
        out.append('<h2>Totals (computed from the rows)</h2><div class="tw"><table><tr><th>Rows</th><th>Count</th><th>Total</th></tr>' + ''.join(groups) + '</table></div>')
    return ''.join(out)


def deadline_when(d):
    if d.get('date') and d.get('wording'):
        return f'{fmt_date(d["date"])}; the document says: “{d["wording"]}”'
    if d.get('wording'):
        return f'the document says: “{d["wording"]}”'
    return fmt_date(d['date'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('record')
    ap.add_argument('out')
    ap.add_argument('--strict', action='store_true', help='unverified quotes, unknown fields and the other pre-send checks become errors')
    a = ap.parse_args(argv)
    rec, errs = checks.load_record(a.record)
    if errs:
        print('BUILD FAILED:')
        print('\n'.join(f' - {e}' for e in errs))
        return 1
    try:
        return build(rec, a.out, a.strict)
    except BuildError as e:
        print(f'BUILD FAILED: {e}')
        return 1
    except OSError as e:
        print(f'BUILD FAILED: a file or folder could not be read or written ({e}). Check that the folder exists and that you may write there.')
        return 1
    except Exception as e:
        if os.environ.get('BTR_DEBUG'):
            raise
        print(f'BUILD FAILED: something unexpected went wrong ({type(e).__name__}: {e}). This is a bug in the tool, not a mistake in your record. Run again with BTR_DEBUG=1 to see where.')
        return 2


if __name__ == '__main__':
    sys.exit(main())
