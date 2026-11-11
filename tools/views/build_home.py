#!/usr/bin/env python3
"""Generate the OUTWARD page (what you could hand to the other side, a reviewer or a journalist) from the same record that feeds the inward pages.

  python3 build_home.py record.json OUTDIR [--files-dir DIR] [--strict] [--private-dir DIR] [--archive DIR]

Makes OUTDIR (the folder you publish: index.html and files/) and OUTDIR-private (the share report and a manifest with the sha256 of every outgoing
file; never publish it). Before anything is written the shared checker (checks.py) runs, so a record that the inward builder refuses is refused here too.

Release is opt-in. Nothing goes on the page unless you set it:
  - a fact appears only if fact.outward is true; a document is shared only if exhibit.share is true. No value means not released.
  - a fact whose documents are not shared still appears, and says "(document not included here)".
  - lawyer, offers, deadlines, held_back and strategy fields never render here.
  - a shared document is copied with its metadata removed (photos lose EXIF and GPS; PDFs lose Author, Subject, Title, Creator; recordings lose
    location tags) and read back; one leftover tag stops the build. Thumbnails and PDF page images are made only for shared documents.
  - the build stops if a shared document, thumbnail or link points at a private host (private.example.com, plus private-hosts.txt), if the page or an outgoing text file carries a
    counsel marker ("for counsel", "privileged", "work product", "Rule 408"), or if a phrase the case holds back appears anywhere.
  - emails, phone numbers, street addresses and long numbers found in outgoing text are listed in the private report to clear one at a time.
DRAFT until the share gate is answered: unless meta.share_gate has recipient, confidentiality_checked, names_checked, defamation_reminder_ack and
attorney_read all set, the page is stamped "DRAFT — not reviewed for sending" and carries no snapshot id.
The snapshot id (non-draft pages) is a hash over every published file, the page included, so a re-masked document changes it. Page files hash as
published, except that index.html is hashed with its own snapshot id replaced by SNAPSHOT-ID. --archive DIR also saves each non-draft build in
DIR/<date>-<snapshot>/ with its recipient; that folder is never replaced or deleted by this tool.
Last step: the output folders are built next to the real ones and swapped in. A folder is replaced only if this tool made it (a .btr-output marker file
is inside) or it is empty; any other folder is refused.
"""
import argparse, datetime as dt, hashlib, json, os, re, shutil, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks, btr_scrub as scrub
from checks import STATUS, BANNER, DRAFT_STAMP, display_status, expand, make_resolver, is_recording, gate_missing, held_phrases, marker_hits, phrase_hits, pii_findings
from btr_common import (BuildError, MARKER, OPEN_ON_HASH_JS, esc, qurl, fmt_date, fact_when, fact_start, fact_is_day, period, sorted_facts, days_between, range_label, is_http,
                    script_json, shorten, sha256_file, sha256_text, new_token, start_build, swap_into_place, check_output_target, remove_made_dir)

HERE = os.path.dirname(os.path.abspath(__file__))
fmt = fmt_date
CSS = """:root{--bg:#fdfcf5;--card:#fffefa;--ink:#2b281d;--muted:#736d56;--line:#e8e3c9;--rule:#e9d2c8;--accent:#8c8460;--mk:#7a7350;--onmk:#fffefa;--link:#5f5a3f;--hot:#2e6e63;--amber:#9a5a12;--blue:#1a4d8f;--cursor:#b3261e;--bad:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#1b1a13;--card:#222118;--ink:#ece8d4;--muted:#a8a284;--line:#3a3827;--rule:#4a3a33;--accent:#a89f72;--mk:#a89f72;--onmk:#1b1a13;--link:#cfc79a;--hot:#6fb5a6;--amber:#e0a050;--blue:#8db7ee;--cursor:#ff6f61;--bad:#ff9d94}}
*{box-sizing:border-box}[hidden]{display:none!important}html{scroll-padding-top:12px}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,'Segoe UI',system-ui,sans-serif;padding:0 18px 60px}
main{max-width:860px;margin:0 auto;border-left:2px solid var(--rule);padding-left:18px}@media (max-width:600px){main{padding-left:12px}}
h1{font:700 28px/1.2 Georgia,serif;margin:30px 0 4px}
h2{font:700 22px/1.25 Georgia,serif;letter-spacing:0;text-transform:none;color:var(--ink);margin:56px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--muted);border-bottom:1px solid color-mix(in srgb,var(--ink) 45%,transparent)}
h2 .n{font:600 15px -apple-system,'Segoe UI',system-ui,sans-serif;color:var(--muted);margin-left:6px}
.sub{color:var(--muted);font-size:14.5px}.upd{display:inline-block;margin:8px 0 6px;padding:5px 10px;border:1px solid var(--line);border-radius:4px;font-size:13.5px;background:var(--card)}
.snap{color:var(--muted);font-size:12.5px;margin:2px 0 8px}.brief{background:var(--card);border-left:4px solid var(--accent);border-radius:4px;padding:16px 20px;margin:12px 0}
.brief p{margin:0 0 10px}.brief p:last-child{margin:0}.brief .lead strong{font-weight:700}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));gap:10px;margin:14px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:9px 11px}.tile b{display:block;font-size:24px;line-height:1.2;font-weight:600;white-space:nowrap}.tile b small{font-size:13px;font-weight:500;color:var(--muted)}.tile span{display:block;font-size:12.5px;line-height:1.4;color:var(--muted)}
.jump{display:flex;flex-wrap:nowrap;gap:6px;overflow-x:auto;margin:4px -2px 8px;padding:2px;scrollbar-width:thin}
.jump a{flex:none;display:inline-flex;align-items:center;gap:6px;min-height:44px;padding:0 14px;border:1px solid var(--line);border-radius:22px;background:var(--card);font-size:14px;color:var(--ink);text-decoration:none;white-space:nowrap}
.jump a span{color:var(--muted);font-size:13px}.jump a:hover{border-color:var(--hot);color:var(--ink)}@media (pointer:fine){.jump a{min-height:34px}}
details{border-top:1px solid var(--line)}details>summary{cursor:pointer;list-style:none;padding:12px 0}details>summary::-webkit-details-marker{display:none}
details>summary::before{content:'\\25B8';display:inline-block;width:1.1em;color:var(--muted)}details[open]>summary::before{content:'\\25BE';color:var(--hot)}
summary b{font:700 17px/1.3 Georgia,serif}details[open]>summary b{color:var(--hot)}.sumline{display:block;margin:3px 0 0 1.1em;color:var(--muted);font-size:14.5px}details>div{margin-left:1.1em;padding-bottom:12px}
.beats details{border:1px solid var(--line);border-radius:6px;background:var(--card);margin:0 0 8px}.beats details>summary{padding:12px 14px}.beats details>div{margin:0 14px;padding-bottom:12px}
.years details>summary,.groups details>summary{display:flex;align-items:baseline;padding:9px 0}.years .sumline,.groups .sumline{display:inline;margin:0 0 0 auto;padding-left:12px;white-space:nowrap}
.f{display:grid;grid-template-columns:130px 1fr;gap:12px;padding:7px 0;border-top:1px solid var(--line);font-size:15px}.f:first-child{border-top:0}.d{color:var(--muted);font-size:13px}
.s{font-size:11.5px;font-weight:600;border:1px solid var(--line);padding:0 6px;border-radius:3px;margin-right:6px;white-space:normal;max-width:100%}.s-account{color:var(--amber);border-color:var(--amber)}.s-disputed{color:var(--blue);border-color:var(--blue)}
a{color:var(--link);text-decoration:underline;text-decoration-color:currentColor;text-decoration-thickness:1px;text-underline-offset:2px}a:hover{color:var(--hot)}
a:focus-visible,button:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--hot);outline-offset:2px;border-radius:2px}
.docs{list-style:none;padding:0;margin:0}.docs li{padding:6px 0;border-top:1px solid var(--line);font-size:15px}.docs .k{color:var(--muted);font-size:13px}
.media{display:flex;gap:8px;overflow-x:auto;scroll-snap-type:x proximity;padding:2px 2px 8px;margin:8px -2px 0}
.media a{flex:0 0 132px;scroll-snap-align:start;display:block;background:var(--card);border:1px solid var(--line);border-radius:4px;overflow:hidden;text-decoration:none;color:inherit}
.media img{display:block;width:100%;height:84px;object-fit:cover;object-position:top;background:var(--line);filter:grayscale(1) sepia(.18) contrast(.95) brightness(1.02);opacity:.82;transition:filter .2s,opacity .2s}
.media a:hover img,.media a:focus-visible img,.media a:active img{filter:none;opacity:1}.media a:hover{border-color:var(--hot)}.media a:focus-visible{outline-offset:1px}
.media .c{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;padding:5px 7px 0;font-size:12px;line-height:1.3;color:var(--ink)}.media small{display:block;padding:2px 7px 6px;font-size:11.5px;line-height:1.3;color:var(--muted)}
.pl{position:relative}.pl::after{content:'\\25B6';position:absolute;right:5px;top:5px;background:rgba(43,40,29,.7);color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:9px;pointer-events:none}
@media (max-width:600px){.years .sumline,.groups .sumline{white-space:normal;padding-left:8px}.years details>summary,.groups details>summary{flex-wrap:wrap}}
.vh,.skip:not(:focus){position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.skip:focus{display:inline-block;margin:0 0 8px;padding:8px 12px;background:var(--card);border:1px solid var(--hot)}
.swwrap{position:relative}.sw{position:relative;overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:4px;padding:6px 0}
svg.sv{display:none;height:auto}svg.sv-narrow{display:block;width:100%;max-width:420px;margin:0 auto;--fs:12.5px}svg.sv-mid{--fs:12.5px}svg.sv-wide{--fs:14.5px}
@media (min-width:600px){svg.sv-narrow{display:none}svg.sv-mid{display:block;width:100%}}@media (min-width:800px){svg.sv-mid{display:none}svg.sv-wide{display:block;width:100%}}
.swwrap .band{fill:none;stroke:var(--line)}.swwrap .lbl{fill:var(--ink);font:700 var(--fs) Georgia,serif;paint-order:stroke;stroke:var(--card);stroke-width:3px;stroke-linejoin:round}.swwrap .tick{stroke:var(--line);stroke-dasharray:2 3}.swwrap .tl,.swwrap .yr{font:var(--fs) -apple-system,system-ui,sans-serif}
.swwrap .tl{fill:var(--muted)}.swwrap .yr{fill:var(--ink);font-weight:700}.swwrap .yrline{stroke:var(--muted);stroke-width:1;opacity:.5}.swwrap .brk{stroke:var(--accent);stroke-width:1;stroke-dasharray:1 3;opacity:.7}
.swwrap .m{stroke:var(--card);stroke-width:1.5}.swwrap .m-documented{fill:var(--mk)}.swwrap .m-account{fill:var(--card);stroke:var(--mk);stroke-width:2.2}.swwrap .m-disputed{fill:var(--mk);stroke:var(--card);stroke-width:1.5}
.swwrap .m-open{fill:var(--card);stroke:var(--muted);stroke-width:2;stroke-dasharray:2 2}.swwrap .m-mixed{fill:var(--card);stroke:var(--ink);stroke-width:2.2}
.swwrap .mn{fill:var(--onmk);font:700 11px -apple-system,system-ui,sans-serif;text-anchor:middle;pointer-events:none}.swwrap .mn.r{fill:var(--ink)}
.swwrap a.mk{cursor:pointer;text-decoration:none}.swwrap a.mk:hover .m-documented,.swwrap a.mk:focus-visible .m-documented{fill:var(--hot)}.swwrap a.mk:hover .m-account,.swwrap a.mk:hover .m-open{stroke:var(--hot)}.swwrap a.mk:hover .m-disputed{fill:var(--blue)}
.swwrap a.mk:focus{outline:none}.swwrap a.mk:focus-visible{outline:2px solid var(--hot);outline-offset:3px}.swwrap a.mk:focus-visible .m,.swwrap a.mk.sel .m{stroke:var(--cursor);stroke-width:3}.swwrap a.mk:focus-visible .bar,.swwrap a.mk:focus-visible .approx,.swwrap a.mk.sel .bar,.swwrap a.mk.sel .approx{stroke:var(--cursor);stroke-width:2}
.swwrap .bar{fill:var(--accent);fill-opacity:.35;stroke:var(--accent);stroke-width:1.2}.swwrap .approx{fill:var(--accent);fill-opacity:.3;stroke:var(--accent);stroke-width:1;stroke-dasharray:3 2}
.swwrap .gbar{fill:var(--accent);fill-opacity:.45;stroke:var(--accent);stroke-width:1.2}.swwrap .gl{fill:var(--ink);font:600 var(--fs) -apple-system,system-ui,sans-serif;paint-order:stroke;stroke:var(--card);stroke-width:3px;stroke-linejoin:round}
.swwrap .asof{stroke:var(--ink);stroke-width:1}.swwrap .asoft{fill:var(--ink);font:var(--fs) -apple-system,system-ui,sans-serif}
.swwrap .cur{stroke:var(--cursor);stroke-width:1.6;pointer-events:none}
#swtip{position:absolute;z-index:3;width:max-content;max-width:min(310px,calc(100% - 8px));background:var(--card);border:1px solid var(--line);border-left:3px solid var(--cursor);border-radius:4px;padding:7px 10px;font-size:12.5px;line-height:1.45;box-shadow:0 6px 20px rgba(60,50,10,.15);pointer-events:none}
#swtip b{font-weight:700}#swtip .q{display:block;color:var(--muted);margin-top:3px}#swtip .st{display:block;margin-top:4px;padding-top:4px;border-top:1px solid var(--line)}
.strip{margin:8px 0 0;padding:10px 12px;border:1px solid var(--line);border-left:3px solid var(--cursor);border-radius:4px;background:var(--card);font-size:14px;line-height:1.45}@media (max-width:799px){.strip{min-height:7.5em}}
.strip .hint{margin:0;color:var(--muted)}.strip .rh{display:flex;flex-wrap:wrap;gap:2px 10px;align-items:baseline}.strip .ent{margin:6px 0 0}.strip .ent+.ent{padding-top:6px;border-top:1px solid var(--line)}
.strip .ctx{display:block;margin-top:6px;color:var(--muted);font-size:13px}.strip .ctx b{color:var(--ink)}.strip .ctx .q,.strip .ctx .st{display:block;margin-top:3px}.strip .acts{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 0}.strip .acts:empty{display:none}
.strip button,.strip a.go{min-height:44px;display:inline-flex;align-items:center;padding:0 14px;border:1px solid var(--muted);border-radius:4px;background:var(--card);color:var(--ink);font:inherit;font-size:14px;text-decoration:none;cursor:pointer}
.strip a.go{background:var(--ink);color:var(--bg);border-color:var(--ink);font-weight:600}.strip a.go:hover{color:var(--bg)}@media (pointer:fine){.strip button,.strip a.go{min-height:34px}}
.earlier{position:absolute;left:6px;top:6px;z-index:2;min-height:44px;padding:0 12px;border:1px solid var(--muted);border-radius:22px;background:var(--card);color:var(--ink);font:inherit;font-size:13px;cursor:pointer}
.legend{font-size:12.5px;color:var(--muted);margin:6px 0 0}.legend p{margin:0 0 3px}.legend .lg{display:inline-block;margin:0 14px 2px 0}.legend svg{width:14px;height:14px;vertical-align:-2px;margin-right:4px;overflow:visible}
.dsum{color:var(--muted);font-size:14.5px;margin:2px 0 8px}.docs button.dl{all:unset;cursor:pointer;color:var(--link);text-decoration:underline;text-decoration-color:currentColor;text-decoration-thickness:1px;text-underline-offset:2px}
.docs button.dl:hover{color:var(--hot)}.docs button.dl:focus-visible{outline:2px solid var(--hot);outline-offset:2px;border-radius:2px}
#lb{position:fixed;inset:0;z-index:50;background:#201e14;display:flex;flex-direction:column;color:#efeadb}#lb[hidden]{display:none}
#lb .bar{display:flex;align-items:center;gap:10px;padding:8px 10px 8px 14px;min-height:56px}#lb .bar .t{flex:1;min-width:0}#lb .bar .t b{display:block;font:700 15px/1.3 Georgia,serif;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
#lb button,#lb a.o{background:#3a3826;border:1px solid #8a8466;color:#efeadb;border-radius:4px;padding:0 14px;min-height:44px;display:inline-flex;align-items:center;justify-content:center;font:inherit;font-size:14px;cursor:pointer;text-decoration:none}
#lb button:hover,#lb a.o:hover{background:#4a4733;border-color:#e9e2c0}#lb button:focus-visible,#lb a.o:focus-visible,#lb .pg:focus-visible{outline:2px solid #e9e2c0;outline-offset:2px}
#lb .stage{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;position:relative;touch-action:pan-y}#lb .stage img{max-width:100%;max-height:100%;object-fit:contain}#lbc{width:100%;height:100%;min-height:0;display:flex;align-items:center;justify-content:center}
#lb .stage video{max-width:100%;max-height:100%;background:#000}#lb .stage audio{width:min(92%,520px)}
#lb .pg{width:100%;height:100%;overflow-y:auto;display:flex;flex-direction:column;align-items:center;gap:10px;padding:6px 14px;box-sizing:border-box}#lb .pg img{width:auto;max-width:min(100%,920px);height:auto;max-height:none;background:#fff}#lb .pgn{color:#cfc9b2;font-size:13px;padding:4px 0 10px}
#lb .stage iframe{width:100%;height:100%;border:0;background:#fff}#lb .ext{text-align:center;padding:20px}#lb .ext img{max-height:55vh;opacity:.9;margin-bottom:14px}
#lb .bot{display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center;padding:8px 10px calc(8px + env(safe-area-inset-bottom));min-height:60px;background:#201e14;border-top:1px solid #3a3826}
#lb .bot .mid{display:flex;flex-direction:column;align-items:center;gap:6px;min-width:0;text-align:center;color:#cfc9b2;font-size:13px}#lb .bot .mid a.o{min-height:36px;font-size:13px;padding:0 12px}#lb .bot .nv{min-width:84px;font-weight:600}
@media (min-width:600px){#lb .bot .mid{flex-direction:row;justify-content:center;gap:14px}}
.note{font-size:13.5px;color:var(--muted);border-top:1px solid var(--line);margin-top:34px;padding-top:12px}.note p{margin:0 0 6px}@media (max-width:600px){.f{grid-template-columns:1fr;gap:2px}}
.draft{border:2px solid var(--bad);color:var(--bad);font-weight:700;padding:8px 12px;border-radius:4px;margin:12px 0;font-size:15px}
.s-claimant_doc{color:var(--amber);border-color:var(--amber)}.s-open{border-style:dashed}.f.x{padding-left:14px;font-size:14px}
@media (forced-colors:active){.swwrap .m-documented,.swwrap .m-disputed{fill:CanvasText;stroke:Canvas}.swwrap .m-account,.swwrap .m-open,.swwrap .m-mixed{fill:Canvas;stroke:CanvasText}.swwrap .bar,.swwrap .gbar,.swwrap .approx{fill:Canvas;stroke:CanvasText}.swwrap .cur{stroke:Highlight}.swwrap .asof{stroke:CanvasText}}
@media print{body{padding:0 6px}.jump,.skip,.strip,.earlier,#swtip,#lb,.legend .tip{display:none!important}.sw{overflow:visible}svg.sv-narrow,svg.sv-mid{display:none!important}svg.sv-wide{display:block!important;width:100%}
.media{flex-wrap:wrap;overflow:visible}details::details-content{content-visibility:visible;display:block}details>summary::before{content:'\\25BE'}h2{break-after:avoid}.f,.docs li{break-inside:avoid}a{color:inherit}}"""


PLAYABLE = {'.mp4': 'video', '.m4v': 'video', '.mov': 'video', '.webm': 'video', '.mp3': 'audio', '.m4a': 'audio', '.wav': 'audio', '.aac': 'audio'}
ABBREV = ('Mr.', 'Mrs.', 'Ms.', 'Dr.', 'St.', 'No.', 'Inc.', 'Co.', 'Corp.', 'Ltd.', 'vs.', 'etc.', 'e.g.', 'i.e.')
KIND_PLURAL = {'documented': 'show in a document', 'account': "claimant’s account", 'claimant_doc': "per the claimant’s own document", 'disputed': 'disputed', 'open': 'open question'}
SW_WIDTHS = (('narrow', 300, 10, 12.5, 6.2, 9.0), ('mid', 600, 16, 12.5, 6.8, 9.5), ('wide', 960, 24, 14.5, 7.4, 10.0))   # name, viewBox width, left margin, text size, mark radius, radius of a mark that stands for several entries


def span_days(start, end):
    """Days after the start date, so the end date is day N of N. cursor.js uses the same rule (spanTotal, spanDay) and a test holds the two together."""
    return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days


def plural(n, word, many=None):
    return f'{n} {word if n == 1 else (many or word + "s")}'


def lead_split(text):
    """(first sentence, the rest) of a paragraph. It does not cut after an initial or an abbreviation such as U.S. or Mr."""
    for m in re.finditer(r'[.!?][”"’)]?\s+(?=[A-Z“"‘(])', text):
        head = text[:m.end()].rstrip()
        last = head.split()[-1]
        if re.fullmatch(r'(?:[A-Z]\.)+[”"’)]?', last) or last in ABBREV:
            continue
        return head, text[m.end():]
    return text, ''


def wrap_text(s, max_units, size, tail=''):
    """Lines of at most max_units, by word, for SVG text (an over-long single word stays whole). `tail` stays on the last line with the last word."""
    cw, lines, cur = 0.6 * size, [], ''
    words = s.split() or ['']
    words[-1] += tail
    for w in words:
        t = (cur + ' ' + w).strip()
        if cur and len(t) * cw > max_units:
            lines.append(cur)
            cur = w
        else:
            cur = t
    return lines + [cur] if cur else lines or ['']


def tick_plan(span, units, size):
    """(kind, step) for the axis. By case length: under 60 days weekly, under 240 days monthly, longer quarterly. Widened until the labels fit."""
    steps = [('day', 7), ('day', 14), ('day', 28), ('month', 1), ('month', 2), ('month', 3), ('month', 6), ('month', 12), ('month', 24), ('month', 60)]
    i = 0 if span < 60 else 3 if span < 240 else 5
    while i < len(steps) - 1:
        kind, n = steps[i]
        gap = (n if kind == 'day' else n * 30.4) * units / span
        chars = 5 if kind == 'day' else 3 if n < 12 else 4
        if gap >= chars * 0.62 * size + 6:
            break
        i += 1
    return steps[i]


def tick_dates(d0, d1, kind, n):
    out = []
    if kind == 'day':
        cur = d0 + dt.timedelta(days=(7 - d0.weekday()) % 7)
        while cur <= d1:
            out.append(cur)
            cur += dt.timedelta(days=n)
        return out
    idx = d0.year * 12 + d0.month - 1
    idx = -(-idx // n) * n
    cur = dt.date(idx // 12, idx % 12 + 1, 1)
    while cur < d0:
        idx += n
        cur = dt.date(idx // 12, idx % 12 + 1, 1)
    while cur <= d1:
        out.append(cur)
        idx += n
        cur = dt.date(idx // 12, idx % 12 + 1, 1)
    return out


def offsets():
    yield 0
    k = 1
    while True:
        yield k
        yield -k
        k += 1


PRINT_JS = ('(function(){var s=[];addEventListener("beforeprint",function(){s=[].map.call(document.querySelectorAll("details"),function(d){var o=d.open;d.open=true;return [d,o]})});'
            'addEventListener("afterprint",function(){s.forEach(function(x){x[0].open=x[1]});s=[]});})();')



class Outward:
    """One outward build: decides what is released, copies and scrubs the files, renders the page, scans what goes out."""

    def __init__(self, rec, R, files_dir):
        self.rec, self.R, self.files_dir = rec, R, files_dir
        self.meta = rec['meta']
        self.ex = {e['id']: e for e in rec.get('exhibits', [])}
        self.all_facts = sorted_facts(rec['facts'])
        self.by_id = {f['id']: f for f in self.all_facts}
        self.released = {f['id'] for f in self.all_facts if f.get('outward') is True}
        self.parent = {f['id']: f.get('excerpt_of') or f.get('fold_into') for f in self.all_facts if f.get('excerpt_of') or f.get('fold_into')}
        self.tops = [f for f in self.all_facts if f['id'] in self.released and f['id'] not in self.parent]
        self.kids = defaultdict(list)
        for f in self.all_facts:
            if f['id'] in self.released and f.get('excerpt_of') and not f.get('fold_into') and f['excerpt_of'] in self.released:
                self.kids[f['excerpt_of']].append(f)
        self.visible = self.tops + [k for ks in self.kids.values() for k in ks]
        self.ds = {f['id']: display_status(f, self.ex, self.meta.get('claimant_label')) for f in self.all_facts}
        self.report, self.out_files = [], {}
        self.listed, self.docs_by_id = [], {}

    # ----- what is released -----

    def openable(self, e):
        f = e.get('file')
        return bool(f) and (is_http(f) or bool(self.files_dir and os.path.isfile(os.path.join(self.files_dir, f))))

    def decide(self):
        for f in self.all_facts:
            if f['id'] in self.released:
                if f['id'] in self.parent and f['id'] not in {k['id'] for ks in self.kids.values() for k in ks}:
                    self.report.append(f"HIDDEN {f['id']} ({f['date']}): " + ('folded into ' + f['fold_into'] if f.get('fold_into') else f"excerpt of {f['excerpt_of']}, which is not released"))
                else:
                    src = [s['ex'] for s in f.get('sources', [])]
                    if src and not any(self.ex[x].get('share') is True for x in src):
                        self.report.append(f"NOTE {f['id']}: its document(s) {', '.join(src)} are not shared, so the page says '(document not included here)'")
            else:
                self.report.append(f"NOT RELEASED {f['id']} ({f['date']}): " + ('outward is false (held back by decision)' if f.get('outward') is False else 'no outward decision recorded (the default is not released)'))
        cited = {s['ex'] for f in self.visible for s in f.get('sources', [])}
        shared_text = [e['text'] for e in self.ex.values() if e.get('share') is True and e.get('text')]
        held_text = {i: e['text'] for i, e in self.ex.items() if e.get('share') is not True and e.get('text')}
        for f in self.visible:
            for q in checks.extract_quotes(f['text']):
                if not any(checks.verify_quote(q, t)[0] == 'ok' for t in shared_text):
                    src = [i for i, t in held_text.items() if checks.verify_quote(q, t)[0] == 'ok']
                    if src:
                        self.report.append(f"NOTE {f['id']} quotes words that appear only in {', '.join(src)}, which is not shared. The page shows those words; check that is intended.")
        for i, e in sorted(self.ex.items(), key=lambda kv: (kv[1].get('date', ''), kv[0])):
            if e.get('fold_into'):
                self.report.append(f"HIDDEN {i}: folded into {e['fold_into']}")
            elif e.get('share') is not True:
                self.report.append(f"NOT SHARED {i} ({e['title']}): " + ('share is false (held back by decision)' if e.get('share') is False else 'no share decision recorded (the default is not shared)'))
            elif not self.openable(e):
                self.report.append(f"NOTE {i} ({e['title']}) is shared but has no file someone can open, so it is not listed or counted")
            elif i in cited or (e.get('feature') and e.get('thumb')):
                self.listed.append(e)
            else:
                self.report.append(f"NOTE {i} ({e['title']}) is shared but no released entry cites it and it is not featured, so it was not copied")
        self.docs_by_id = {e['id']: e for e in self.listed}

    # ----- files: scrub, copy, page images -----

    def register(self, rel, src, exhibit, note):
        if rel in self.out_files and self.out_files[rel]['src'] != src:
            self.R.error(f"Two different files would both be published as {rel!r} (exhibit {exhibit}). Rename one.")
            return False
        clash = next((k for k in self.out_files if k != rel and k.casefold() == rel.casefold()), None)
        if clash:
            self.R.error(f"The files {clash!r} and {rel!r} differ only by capitals, so one would overwrite the other on a Mac or Windows computer (exhibit {exhibit}). Rename one.")
            return False
        self.out_files[rel] = {'src': src, 'exhibit': exhibit, 'note': note}
        return True

    def local_src(self, rel, who):
        root = os.path.realpath(self.files_dir)
        src = os.path.realpath(os.path.join(root, rel))
        if not (src == root or src.startswith(root + os.sep)) or not os.path.isfile(src):
            raise BuildError(f"{who}: {rel!r} is not a file inside the files folder.")
        return src

    def copy_files(self, pub):
        for e in self.listed:
            for fld in ('file', 'thumb'):
                rel = e.get(fld)
                if not rel or is_http(rel) or 'files/' + rel.replace('\\', '/') in self.out_files:
                    continue
                dst_rel = 'files/' + rel.replace('\\', '/')
                try:
                    src = self.local_src(rel, f"exhibit {e['id']}")
                    note = scrub.scrub_copy(src, os.path.join(pub, dst_rel))
                    if os.path.splitext(rel)[1].lower() in ('.html', '.htm'):
                        self.add_robots(os.path.join(pub, dst_rel))
                        note += '; noindex added'
                    self.register(dst_rel, src, e['id'], note)
                except BuildError as ex:
                    self.R.error(str(ex) if str(ex).startswith('exhibit ') else f"exhibit {e['id']} ({fld}): {ex}")
                    continue
                if fld == 'file' and scrub.kind_of(rel)[0] == 'pdf':
                    try:
                        names, n = scrub.render_pdf_pages(os.path.join(pub, dst_rel), os.path.join(pub, 'files', 'pages'), e['id'])
                        e['_pages'], e['_npages'] = ['files/pages/' + x for x in names], n
                        for x in names:
                            self.register('files/pages/' + x, src, e['id'], 'page image rendered from the scrubbed PDF')
                    except BuildError as ex:
                        self.R.error(f"exhibit {e['id']}: {ex}")

    @staticmethod
    def add_robots(path):
        with open(path, encoding='utf-8', errors='replace') as fh:
            t = fh.read()
        if re.search(r'(?i)<meta[^>]+name=["\']robots', t):
            return
        tag = '<meta name="robots" content="noindex,nofollow">'
        t2 = re.sub(r'(?i)(<head[^>]*>)', r'\1' + tag, t, count=1) if re.search(r'(?i)<head[^>]*>', t) else tag + t
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(t2)

    # ----- numbers and text -----

    def counts(self):
        n = lambda key: sum(1 for f in self.tops if self.ds[f['id']][0] == key)
        top_docs = [e for e in self.listed if not e.get('excerpt_of')]
        return {'facts': len(self.tops), 'documents': sum(1 for e in top_docs if not is_recording(e)), 'recordings': sum(1 for e in top_docs if is_recording(e)),
                'documented': n('documented'), 'claimant_docs': n('claimant_doc'), 'account': n('account'), 'disputed': n('disputed'), 'open': n('open')}

    # ----- the timeline: the same chart drawn at three widths, each at a size where its text and marks are readable -----

    def timeline(self, T0, skip_target):
        rec, meta, ds = self.rec, self.meta, self.ds
        lanes = rec.get('lanes') or [{'id': 'all', 'label': 'Entries'}]
        default_lane = lanes[-1]['id']
        spans = sorted(rec.get('spans', []), key=lambda x: (x['start'], x['end']))
        pts = self.tops
        asof = dt.date.fromisoformat(meta['asof']) if meta.get('asof') else None
        shape = lambda f: {'claimant_doc': 'account'}.get(ds[f['id']][0], ds[f['id']][0])

        def f_span(f):
            lo, hi = period(f['date'], f.get('date_precision'))
            if f.get('end'):
                hi = max(hi, period(f['end'])[1])
            return lo, hi

        d_lo = [f_span(f)[0] for f in pts] + [dt.date.fromisoformat(x['start']) for x in spans]
        d_hi = [f_span(f)[1] for f in pts] + [dt.date.fromisoformat(x['end']) for x in spans] + ([asof] if asof else [])
        d0 = min(d_lo) - dt.timedelta(days=12)
        d1 = max(d_hi) + dt.timedelta(days=12)
        span = max((d1 - d0).days, 1)

        lane_marks = []                      # one entry per lane: its marks. Same lane and same day make one mark with a count.
        for l in lanes:
            items = sorted((f for f in pts if (f.get('lane') or default_lane) == l['id']), key=lambda f: (f['date'], f['id']))
            marks, by_day = [], {}
            for f in items:
                lo, hi = f_span(f)
                if fact_is_day(f):
                    m = by_day.get(lo)
                    if m is None:
                        m = by_day[lo] = {'facts': [], 'lo': lo, 'hi': lo, 'approx': False}
                        marks.append(m)
                    m['facts'].append(f)
                    m['hi'] = max(m['hi'], hi)
                else:
                    marks.append({'facts': [f], 'lo': lo, 'hi': hi, 'approx': True})
            lane_marks.append((l, items, marks))
        all_marks = [m for _l, _i, ms in lane_marks for m in ms]

        def kind_of(m):
            ks = {shape(f) for f in m['facts']}
            return ks.pop() if len(ks) == 1 else 'mixed'

        def mark_title(m):
            fs = m['facts']
            when = fact_when(fs[0])
            if len(fs) == 1:
                return f"{when}. {ds[fs[0]['id']][1]}. {shorten(T0(fs[0]['text']), 140)}"
            counts = defaultdict(int)
            for f in fs:
                counts[ds[f['id']][0]] += 1
            return f"{when}. {len(fs)} entries ({', '.join(f'{n} {KIND_PLURAL[k]}' for k, n in counts.items())}). First: {shorten(T0(fs[0]['text']), 100)}"

        def draw(name, W, X0, size, r1, r2):
            X1 = W - X0
            xo = lambda d: X0 + (d - d0).days / span * (X1 - X0)
            lh = size * 1.3
            axis_h = 2 * size + 12
            y = axis_h + 6
            sp_svg = []
            for sp in spans:
                days = span_days(sp['start'], sp['end'])
                tail = f" · {plural(days, 'day')}"
                lab = T0(sp['label']) + tail
                lines = wrap_text(T0(sp['label']), X1 - X0, size, tail)
                xs, xe = xo(dt.date.fromisoformat(sp['start'])), xo(dt.date.fromisoformat(sp['end']))
                tx = min(max(xs, X0), max(X0, X1 - max(len(s) for s in lines) * 0.6 * size))
                bar_y = y + len(lines) * lh + 2
                full = f"{lab} ({fmt_date(sp['start'])} to {fmt_date(sp['end'])})"
                txt = ''.join(f'<tspan x="{tx:.1f}" y="{y + (i + 0.8) * lh:.1f}">{esc(s)}</tspan>' for i, s in enumerate(lines))
                sp_svg.append(f'<g><text class="gl">{txt}</text><rect class="gbar" x="{xs:.1f}" y="{bar_y:.1f}" width="{max(xe - xs, 3):.1f}" height="9" rx="3"><title>{esc(full)}</title></rect></g>')
                y = bar_y + 9 + 9
            y += 4 if spans else 0
            bands, geo = [], []
            for l, items, marks in lane_marks:
                head = wrap_text(T0(l['label']), X1 - X0 - 4, size * 1.05, f' · {len(items)}')
                head_h = len(head) * lh + 4
                ROW = round(2 * r2 + 2) if any(len(m['facts']) > 1 for m in marks) else round(2 * r1 + 4)
                placed, out = [], []
                for m in sorted(marks, key=lambda m: (m['lo'], m['facts'][0]['id'])):
                    r = r2 if len(m['facts']) > 1 else r1
                    x = xo(m['lo'])
                    if m['approx']:
                        bx0, bx1, half = x, max(xo(m['hi']), x + 8), 5.0
                    else:
                        bx0, bx1, half = x - r - 1.5, max(x + r + 1.5, xo(m['hi']) + 1), r + 1.5
                    for k in offsets():
                        top, bot = k * ROW - half, k * ROW + half
                        if not any(bx0 < p[1] and bx1 > p[0] and top < p[3] and bot > p[2] for p in placed):
                            break
                    placed.append((bx0, bx1, top, bot))
                    out.append((m, x, k, r))
                ks = [k for _m, _x, k, _r in out] or [0]
                mink, rows = min(ks), max(ks) - min(ks) + 1
                h = head_h + rows * ROW + 8
                bands.append((l, y, h, head, head_h, mink, out, ROW))
                geo.append({'id': l['id'], 'y0': round(y, 1), 'y1': round(y + h, 1)})
                y += h + 6
            H = y + (size + 8 if asof else 4)
            g = []
            tick_kind, tick_n = tick_plan(span, X1 - X0, size)
            yr_y = 2 * size + 5
            for t in tick_dates(d0, d1, tick_kind, tick_n):
                x = xo(t)
                g.append(f'<line class="tick" x1="{x:.1f}" x2="{x:.1f}" y1="{axis_h}" y2="{H - 2:.1f}"/>')
                if tick_kind == 'day' or tick_n < 12:
                    lab = f'{t.strftime("%b")} {t.day}' if tick_kind == 'day' else t.strftime('%b')
                    if x + 3 + len(lab) * 0.62 * size <= W - 2:
                        g.append(f'<text class="tl" x="{x + 3:.1f}" y="{size + 1:.1f}">{lab}</text>')
            jan = [dt.date(yr, 1, 1) for yr in range(d0.year + 1, d1.year + 1) if d0 <= dt.date(yr, 1, 1) <= d1]
            yw = 4 * 0.62 * size + 6
            if not jan or xo(jan[0]) - X0 >= yw:
                g.append(f'<text class="yr" x="{X0:.1f}" y="{yr_y:.1f}">{d0.year}</text>')
            for j in jan:
                x = xo(j)
                g.append(f'<line class="yrline" x1="{x:.1f}" x2="{x:.1f}" y1="{size + 6:.1f}" y2="{H - 2:.1f}"/><text class="yr" x="{x + 3:.1f}" y="{yr_y:.1f}">{j.year}</text>')
            lane_pos = {b[0]['id']: n for n, b in enumerate(bands)}
            for sp in spans:
                ls = [lane_pos[x] for x in (sp.get('lanes') if isinstance(sp.get('lanes'), list) else lane_pos) if x in lane_pos] or list(range(len(bands)))
                top, bot = bands[min(ls)][1], bands[max(ls)][1] + bands[max(ls)][2]
                for d in (sp['start'], sp['end']):
                    x = xo(dt.date.fromisoformat(d))
                    g.append(f'<line class="brk" x1="{x:.1f}" x2="{x:.1f}" y1="{top:.1f}" y2="{bot:.1f}"/>')
            for l, y0, h, head, head_h, mink, out, ROW in bands:
                g.append(f'<rect class="band" x="{X0 - 6}" y="{y0:.1f}" width="{X1 - X0 + 12}" height="{h:.1f}" rx="6"/>' +
                         '<text class="lbl">' + ''.join(f'<tspan x="{X0}" y="{y0 + (i + 0.85) * lh:.1f}">{esc(s)}</tspan>' for i, s in enumerate(head)) + '</text>')
                for m, x, k, r in out:
                    cy = y0 + head_h + 3 + (k - mink + 0.5) * ROW
                    kind = kind_of(m)
                    parts = []
                    if m['approx']:
                        parts.append(f'<rect class="approx" x="{x:.1f}" y="{cy - 4.5:.1f}" width="{max(xo(m["hi"]) - x, 8):.1f}" height="9" rx="3"/>')
                    else:
                        for f in m['facts']:
                            if f.get('end') and f_span(f)[1] > m['lo']:
                                parts.append(f'<rect class="bar" x="{x:.1f}" y="{cy - 4:.1f}" width="{max(xo(f_span(f)[1]) - x, 6):.1f}" height="8" rx="3"/>')
                        if kind == 'disputed':
                            s = r + 1.5
                            parts.append(f'<path class="m m-disputed" d="M{x:.1f},{cy - s:.1f}L{x + s:.1f},{cy:.1f}L{x:.1f},{cy + s:.1f}L{x - s:.1f},{cy:.1f}Z"/>')
                        else:
                            parts.append(f'<circle class="m m-{kind}" cx="{x:.1f}" cy="{cy:.1f}" r="{r}"/>')
                        if len(m['facts']) > 1:
                            parts.append(f'<text class="mn{"" if kind in ("documented", "disputed") else " r"}" x="{x:.1f}" y="{cy + 4:.1f}">{len(m["facts"])}</text>')
                    ids = ' '.join(f['id'] for f in m['facts'])
                    g.append(f'<a class="mk" href="#e-{esc(m["facts"][0]["id"])}" data-ids="{esc(ids)}" data-d="{m["lo"].isoformat()}"><title>{esc(mark_title(m))}</title>{"".join(parts)}</a>')
            if asof:
                x = xo(asof)
                lab = f'as of {fmt_date(asof.isoformat())}'
                left = x - 4 - len(lab) * 0.6 * size >= X0
                g.append(f'<line class="asof" x1="{x:.1f}" x2="{x:.1f}" y1="{axis_h}" y2="{H - size - 6:.1f}"/>'
                         f'<text class="asoft" x="{x + (-4 if left else 4):.1f}" y="{H - 5:.1f}" text-anchor="{"end" if left else "start"}">{esc(lab)}</text>')
            g.extend(sp_svg)
            g.append(f'<line class="cur" x1="0" x2="0" y1="{axis_h - 6}" y2="{H - 2:.1f}" style="display:none"/>')
            svg = (f'<svg class="sv sv-{name}" data-v="{name}" viewBox="0 0 {W} {H:.0f}" role="group" aria-label="Swimlane timeline of {len(pts)} dated entries">{"".join(g)}</svg>')
            return svg, {'W': W, 'H': round(H), 'X0': X0, 'X1': X1, 'lanes': geo}

        svgs, vgeo = [], {}
        for name, W, X0, size, r1, r2 in SW_WIDTHS:
            s, gdata = draw(name, W, X0, size, r1, r2)
            svgs.append(s)
            vgeo[name] = gdata
        facts = []
        for f in pts:
            lo, hi = f_span(f)
            facts.append({'id': f['id'], 'd': lo.isoformat(), 'e': hi.isoformat() if hi > lo else None, 'l': f.get('lane') or default_lane, 't': shorten(T0(f['text']), 64),
                          'x': shorten(T0(f['text']), 150), 'k': shape(f), 'w': ds[f['id']][1], 'when': fact_when(f), 'a': 0 if fact_is_day(f) else 1})
        data = {'d0': d0.isoformat(), 'span': span, 'asof': asof.isoformat() if asof else None, 'lanes': [{'id': l['id'], 'label': T0(l['label'])} for l in lanes], 'v': vgeo, 'facts': facts,
                'spans': [{'s': sp['start'], 'e': sp['end'], 'label': T0(sp['label']), 'note': T0(sp.get('note', ''))} for sp in spans],
                'hint': 'Tap a mark to read it here. With a keyboard, Tab to the timeline, then use the arrow keys to move between entries and Enter to go to the entry.'}
        present = {shape(f) for f in pts}
        mixed = any(kind_of(m) == 'mixed' for m in all_marks)
        counted = any(len(m['facts']) > 1 for m in all_marks)

        def lg(cls, text, d=None):
            shp = f'<path class="m {cls}" d="{d}"/>' if d else f'<circle class="m {cls}" cx="7" cy="7" r="5.5"/>'
            return f'<span class="lg"><svg viewBox="0 0 14 14" aria-hidden="true">{shp}</svg>{text}</span>'

        leg = ''.join(x for x in [
            lg('m-documented', 'shows in a document') if 'documented' in present else '',
            lg('m-account', 'claimant’s account or own document') if 'account' in present else '',
            lg('m-disputed', 'disputed', 'M7,0.5L13.5,7L7,13.5L0.5,7Z') if 'disputed' in present else '',
            lg('m-open', 'open question') if 'open' in present else '',
            lg('m-mixed', 'several entries on one day with different statuses') if mixed else ''])
        notes = ['a number inside a mark is how many entries share that day'] if counted else []
        if asof:
            notes.append(f'black line: as of {fmt_date(asof.isoformat())}')
        if spans:
            notes.append('span lengths count the days after the start date')
        notes.append('move across the timeline, or tap a mark: the red line reads the story at that point')
        legend = f'<div class="legend"><p>{leg}</p><p class="tip">{esc("; ".join(notes))}.</p></div>'
        return (f'<div class="swwrap" id="sw"><a class="skip" href="#{skip_target}">Skip the timeline</a>'
                f'<p class="vh" id="swhelp" hidden>{esc(data["hint"])}</p>'
                f'<div class="sw">{"".join(svgs)}<button class="earlier" type="button" hidden aria-label="Show earlier dates on the timeline">&#8592; Earlier</button></div>'
                f'<div id="swtip" aria-hidden="true" hidden></div><div class="strip" id="swstrip" hidden></div>'
                f'<script type="application/json" id="swdata">{script_json(data)}</script>{legend}</div>')

    # ----- rendering -----

    def href(self, rel):
        return rel if is_http(rel) else 'files/' + qurl(rel.replace('\\', '/'))

    def render(self, draft, snap_token):
        rec, meta, ex = self.rec, self.meta, self.ex
        counts = self.counts()
        intervals = {i['id']: i for i in rec.get('intervals', []) if i.get('id')}
        resolver = make_resolver(self.by_id, intervals, counts, self.ex)
        T0 = lambda s: expand(s, resolver)
        T = lambda s: esc(T0(s))
        listed_ids = set(self.docs_by_id)
        lanes = rec.get('lanes') or []

        def frow(f, extra='', pre='e-'):
            key, words = self.ds[f['id']]
            st = '' if key == 'documented' else f'<span class="s s-{key}">{esc(words)}</span>'
            refs = ' '.join(f'<a href="#x-{esc(s["ex"])}">[{esc(s["ex"])}]</a>' for s in f.get('sources', []) if s['ex'] in listed_ids)
            if f.get('sources') and not refs:
                refs = '<span class="d">(document not included here)</span>'
            lead = f'<span class="d">Excerpt of {esc(f["excerpt_of"])}. </span>' if f.get('excerpt_of') else ''
            return f'<div class="f{extra}" id="{pre}{esc(f["id"])}"><div class="d">{esc(fact_when(f))}</div><div>{lead}{st}{T(f["text"])} {refs}</div></div>'

        def frows(fs, pre='e-'):
            return ''.join(frow(f, '', pre) + ''.join(frow(k, ' x', pre) for k in self.kids.get(f['id'], [])) for f in fs)

        def file_ext(e):
            return os.path.splitext((e.get('file') or '').split('?')[0])[1].lower()

        def playable(e):
            return bool(e.get('file')) and not is_http(e['file']) and file_ext(e) in PLAYABLE

        feats = [e for e in self.listed if e.get('feature') and e.get('thumb')]

        def media_strip():
            cells = []
            for e in feats:
                href = self.href(e['file']) if e.get('file') else (e.get('link') or f'#x-{e["id"]}')
                cap = esc(T0(e.get('caption') or e['title']))
                line = ' · '.join(x for x in [fmt_date(e.get('date', ''), e.get('date_precision')), e.get('kind') or ''] if x)
                cells.append(f'<a href="{esc(href)}" data-lbid="{esc(e["id"])}"{" class=pl" if playable(e) else ""}><img src="{esc(self.href(e["thumb"]))}" alt="" loading="lazy">'
                             f'<span class="c">{cap}</span><small>{esc(line)}</small></a>')
            return f'<div class="media">{"".join(cells)}</div>' if cells else ''

        tiles = []
        for iv in rec.get('intervals', []):
            a, b = self.by_id[iv['a']], self.by_id[iv['b']]
            if a['id'] in self.released and b['id'] in self.released:
                tiles.append(f'<div class="tile"><b>{days_between(a, b)}<small> days</small></b><span>{T(iv["label"])} (computed from {esc(fact_when(a))} and {esc(fact_when(b))})</span></div>')
            else:
                self.report.append(f"NOTE interval {iv['label']!r} is not shown: fact {a['id'] if a['id'] not in self.released else b['id']} is not released")
        if meta.get('review_opened'):
            days = (dt.date.fromisoformat(meta['asof']) - dt.date.fromisoformat(meta['review_opened'])).days
            tiles.append(f'<div class="tile"><b>Day {days}</b><span>of the review opened {esc(fmt_date(meta["review_opened"]))}, as of {esc(fmt_date(meta["asof"]))}</span></div>')
        default_lane = (lanes or [{'id': 'all'}])[-1]['id']
        for l in (lanes or [{'id': 'all', 'label': ''}])[:4]:
            fs = [f for f in self.tops if (f.get('lane') or default_lane) == l['id']]
            if not fs:
                continue
            dates = len({fact_start(f) for f in fs}) if all(fact_is_day(f) for f in fs) else 0
            where = ', '.join(x for x in [esc(T0(l['label'])) if lanes else '', f'on {plural(dates, "date")}' if dates else ''] if x)
            tiles.append(f'<div class="tile"><b>{len(fs)}<small> {"entry" if len(fs) == 1 else "entries"}</small></b><span>{where}</span></div>')

        beats = []
        for bi, b in enumerate(rec.get('beats', [])):
            lo, hi = period(b['from'])[0], period(b['to'])[1]
            inr = [f for f in self.tops if lo <= fact_start(f) <= hi]
            prose = ''.join(f'<p>{T(p)}</p>' for p in b.get('prose', []))
            line = f' — {T(b["line"])}' if b.get('line') else ''
            beats.append(f'<details><summary><b>{T(b["title"])}</b><span class="sumline">{esc(range_label(b["from"], b["to"]))}{line}</span></summary><div>{prose}{frows(inr, f"b{bi}-")}</div></details>')
        years = sorted({fact_start(f).year for f in self.tops})
        tl = ''.join(f'<details><summary><b>{y}</b><span class="sumline">{plural(n, "entry", "entries")}</span></summary><div>{frows(fs)}</div></details>'
                     for y in years for fs in [[f for f in self.tops if fact_start(f).year == y]] for n in [len(fs)])

        def dtype(e):
            f = e.get('file') or ''
            if is_http(f):
                return 'ext'
            ext = file_ext(e)
            return PLAYABLE.get(ext) or ('image' if ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp') else 'pdf' if ext == '.pdf' else 'html' if ext in ('.html', '.htm') else 'ext')

        lbitems, lbidx = [], {}
        for e in self.listed:
            f = e.get('file') or ''
            lbitems.append({'pages': e.get('_pages', []), 'npages': e.get('_npages', 0), 'id': e['id'], 'title': e['title'],
                            'meta': ' · '.join(x for x in [fmt_date(e.get('date', ''), e.get('date_precision')), e.get('kind') or ''] if x),
                            'href': self.href(f) if f else '', 'type': dtype(e) if f else 'ext', 'thumb': self.href(e['thumb']) if e.get('thumb') else ''})
            lbidx[e['id']] = len(lbitems) - 1
        groups = defaultdict(list)
        for e in self.listed:
            if not e.get('excerpt_of'):
                groups[e.get('kind') or 'Document'].append(e)
        dsum = (f'{plural(counts["documents"], "document")}' + (f' and {plural(counts["recordings"], "recording")}' if counts['recordings'] else '') +
                f' in {len(groups)} kinds: ' + ', '.join(f'{k} {len(v)}' for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))) +
                '. Open a group, then click a title to view it; use the arrow keys or swipe to move between documents.') if groups else 'No documents are shared on this page.'
        excerpts = defaultdict(list)
        for e in self.listed:
            if e.get('excerpt_of'):
                excerpts[e['excerpt_of']].append(e)

        def drow(e, nested=False):
            lead = f'<span class="k">Excerpt of {esc(e["excerpt_of"])} · </span>' if nested else ''
            li = (f'<li id="x-{esc(e["id"])}">{lead}<b>{esc(e["id"])}</b> · <button class="dl" data-lb="{lbidx[e["id"]]}">{esc(T0(e["title"]))}</button> '
                  f'<span class="k">· {esc(fmt_date(e.get("date", ""), e.get("date_precision")))}</span></li>')
            return li + ''.join(drow(x, True) for x in excerpts.get(e['id'], []))

        nrec = counts['recordings']
        docs = f'<p class="dsum">{esc(dsum)}</p><div class="groups">' + ''.join(
            f'<details><summary><b>{esc(k)}</b><span class="sumline">{plural(len(v), "document")}</span></summary><div><ul class="docs">{"".join(drow(e) for e in v)}</ul></div></details>'
            for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))) + '</div>'
        strip = media_strip()
        has_rec, has_doc = any(is_recording(e) for e in feats), any(not is_recording(e) for e in feats)
        media_title = 'Key documents and recordings' if has_rec and has_doc else 'Key recordings' if has_rec else 'Key documents'
        if feats and all((e.get('kind') or '').lower().startswith(('still', 'frame')) for e in feats):
            media_title = 'Key items'
        n_docs = counts['documents'] + nrec
        sections = ([('s-media', 'Key items' if (has_rec and has_doc) else media_title, len(feats))] if strip else []) + [('s-timeline', 'Timeline', None)] + \
                   ([('s-parts', 'In parts', len(beats))] if beats else []) + [('s-entries', 'All entries', len(self.tops)), ('s-docs', 'Documents', n_docs)]
        jump = ('<nav class="jump" aria-label="Sections of this page">' +
                ''.join(f'<a href="#{i}">{esc(t)}{f" <span>{n}</span>" if n is not None else ""}</a>' for i, t, n in sections) + '</nav>')
        h2 = lambda i, t, n=None: f'<h2 id="{i}">{esc(t)}{f" <span class=n>{n}</span>" if n is not None else ""}</h2>'
        skip_target = 's-parts' if beats else 's-entries'
        stamp = f'<div class="draft" role="note">{esc(DRAFT_STAMP)}</div>' if draft else ''
        lead, rest = lead_split(T0(meta['summary']))
        counts_line = f'{plural(counts["facts"], "dated entry", "dated entries")} · {plural(counts["documents"], "document")}' + (f' and {plural(nrec, "recording")}' if nrec else '') + ' shared on this page'
        snap = counts_line + ('.' if draft else f' · Snapshot {snap_token}. This page is a copy as of that time; the record may have changed since.')
        body = (f'<h1>{esc(meta["title"])}</h1><div class="sub">{esc(meta.get("subtitle", ""))}</div>{stamp}'
                f'<div class="upd">Last updated <b>{esc(meta["updated"])}</b></div>{jump}'
                f'<div class="brief"><p class="lead"><strong>{esc(lead)}</strong>{(" " + esc(rest)) if rest else ""}</p><p><b>Asked for:</b> {esc(T0(meta.get("ask", "")))}</p></div>'
                f'<div class="tiles">{"".join(tiles)}</div>'
                f'{(h2("s-media", media_title, len(feats)) + strip) if strip else ""}{h2("s-timeline", "Timeline")}{self.timeline(T0, skip_target)}'
                f'{(h2("s-parts", "The record in parts", len(beats)) + "<div class=beats>" + "".join(beats) + "</div>") if beats else ""}'
                f'{h2("s-entries", "Every dated entry", len(self.tops))}<div class="years">{tl}</div>{h2("s-docs", "Documents and recordings" if nrec else "Documents", n_docs)}{docs}'
                f'<footer class="note"><p class="snap">{esc(snap)}</p><p>This page states what the documents say. It makes no argument and is not legal advice. {esc(T0(meta.get("contact_note", "")))}</p></footer>')
        viewer = ('<div id="lb" hidden role="dialog" aria-modal="true" aria-labelledby="lbt" aria-describedby="lbm"><div class="bar"><div class="t"><b id="lbt"></b></div>'
                  '<button id="lbx" type="button">Close</button></div><div class="stage" id="lbs"><div id="lbc"></div></div>'
                  '<div class="bot"><button class="nv" id="lbp" type="button" aria-label="Previous document">&#8249; Previous</button>'
                  '<div class="mid"><span id="lbm" aria-live="polite"></span><a class="o" id="lbo" target="_blank" rel="noopener">Open original</a></div>'
                  '<button class="nv" id="lbn" type="button" aria-label="Next document">Next &#8250;</button></div></div>'
                  f'<script type="application/json" id="lbdata">{script_json(lbitems)}</script>')
        title = ('DRAFT — ' if draft else '') + meta['title']
        with open(os.path.join(HERE, 'cursor.js'), encoding='utf-8') as fh:
            cursor_js = fh.read()
        with open(os.path.join(HERE, 'lightbox.js'), encoding='utf-8') as fh:
            lb_js = fh.read()
        page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{esc(title)}</title><meta name="robots" content="noindex,nofollow"><style>{CSS}</style></head><body><main>' + body + '</main>' + viewer +
                '<script>' + cursor_js + '</script><script>' + lb_js + '</script><script>' + OPEN_ON_HASH_JS + '</script><script>' + PRINT_JS + '</script></body></html>')
        seen = defaultdict(int)
        for i in re.findall(r'\sid="([^"]+)"', page):
            seen[i] += 1
        dup = sorted(i for i, n in seen.items() if n > 1)
        if dup:
            raise BuildError(f"The page would use the id {dup[0]!r} more than once, so a link to it could not land in one place. This is a bug in the page builder, not a mistake in the record.")
        return page

    # ----- what goes out: scan -----

    def scan(self, pub):
        """Marker, held-phrase, link and personal-detail checks over every outgoing text file. Returns the personal-detail lines for the private report."""
        meta = self.meta
        held = held_phrases(self.rec)
        pii_lines, notes, unscanned = [], [], []
        for dirpath, _d, names in os.walk(pub):
            for nm in sorted(names):
                path = os.path.join(dirpath, nm)
                rel = os.path.relpath(path, pub).replace(os.sep, '/')
                kind, _ext = scrub.kind_of(nm)
                ex = self.ex.get(self.out_files.get(rel, {}).get('exhibit'), {})
                text = None
                if rel == 'index.html' or kind == 'text':
                    with open(path, encoding='utf-8', errors='replace') as fh:
                        raw = fh.read()
                    text = re.sub(r'<[^>]+>', ' ', re.sub(r'(?is)<script(?![^>]*application/json)[^>]*>.*?</script>|<style.*?</style>', ' ', raw)) if nm.lower().endswith(('.html', '.htm')) else raw
                    if rel != 'index.html' and nm.lower().endswith(('.html', '.htm')):
                        if re.search(r'(?i)<script\b|<iframe\b|<object\b|<embed\b|\son[a-z]+\s*=|javascript:', raw):
                            self.R.error(f"{rel} contains a script or embedded content that would run on the reader's computer. Save the document as a PDF or a picture, or leave it unshared.")
                        for m in re.finditer(r'(?i)(?:<(?:img|link|source|video|audio)\b[^>]*?\s(?:src|href)\s*=|url\()\s*["\']?(https?://[^"\')\s>]+)', raw):
                            self.R.warn(f"{rel} loads something from {m.group(1)[:60]!r} when it is opened, which tells that site who opened it. Use a local copy.")
                    if rel == 'index.html':
                        for m in checks.private_url_rx().finditer(raw):
                            self.R.error(f"The page itself points to {m.group(0)[:80]!r}, a private site. Nothing on the outward page may link there.")
                    else:
                        for m in checks.private_url_rx().finditer(raw):
                            self.R.warn(f"{rel} mentions a private address ({m.group(0)[:60]!r}). Check that the document should be shared as it is.")
                elif kind == 'pdf':
                    text = scrub.pdf_text(path)
                    if text is None:
                        notes.append(f"{rel}: no text layer, so it could not be scanned for counsel markers or personal details. Look at it yourself.")
                elif rel != MARKER and not rel.startswith('files/pages/'):
                    unscanned.append(rel)
                if text is None:
                    continue
                for m in marker_hits(text, ex.get('allow_markers') or []):
                    self.R.error(f"{rel} contains '{m}', which marks material meant for counsel. It cannot go out. Remove it, or leave that document unshared.")
                for m in marker_hits(text):
                    if m.casefold() in {a.casefold() for a in ex.get('allow_markers') or []}:
                        notes.append(f"{rel}: contains '{m}'; allowed by allow_markers on exhibit {ex.get('id')}.")
                for p in phrase_hits(text, held):
                    self.R.error(f"{rel} contains a phrase this case holds back ({p!r}).")
                seen = set()
                for label, val in pii_findings(text):
                    if (label, val) not in seen:
                        seen.add((label, val))
                        pii_lines.append(f"{rel}: {label}: {val}")
        if unscanned:
            notes.append('pictures and recordings are not scanned (faces, plates, addresses, signatures): ' + ', '.join(sorted(unscanned)) + '. Look at each one yourself.')
        return pii_lines, notes


def snapshot_lines(pub, index_hash):
    lines = []
    for dirpath, _d, names in os.walk(pub):
        for nm in names:
            rel = os.path.relpath(os.path.join(dirpath, nm), pub).replace(os.sep, '/')
            lines.append(f'{rel}\t{index_hash if rel == "index.html" else sha256_file(os.path.join(dirpath, nm))}')
    return '\n'.join(sorted(lines)) + '\n'


def manifest_files(pub, out_files):
    rows = []
    for dirpath, _d, names in os.walk(pub):
        for nm in names:
            p = os.path.join(dirpath, nm)
            rel = os.path.relpath(p, pub).replace(os.sep, '/')
            rows.append({'path': rel, 'bytes': os.path.getsize(p), 'sha256': sha256_file(p), 'exhibit': out_files.get(rel, {}).get('exhibit'), 'note': out_files.get(rel, {}).get('note', '')})
    return sorted(rows, key=lambda r: r['path'])


def build(rec, out, files_dir=None, strict=False, private_dir=None, archive=None):
    rec, R = checks.check_record(rec, 'outward', strict, files_dir)
    if not R.ok:
        for w in R.warnings:
            print(f'note: {w}')
        print(checks.format_failure('HOME', R).strip())
        return 1
    out = os.path.abspath(out)
    private_dir = os.path.abspath(private_dir or out.rstrip(os.sep) + '-private')
    if files_dir and not os.path.isdir(files_dir):
        raise BuildError(f'The files folder {files_dir!r} does not exist.')
    for a, b in ((out, private_dir), (private_dir, out)):
        if a == b or a.startswith(b + os.sep):
            raise BuildError('The private report folder must be a different folder from the published one, and not inside it, or the report would be published with the page.')
    if files_dir:
        fd = os.path.realpath(files_dir)
        for p in (out, private_dir):
            if os.path.realpath(p) == fd or os.path.realpath(p).startswith(fd + os.sep) or fd.startswith(os.path.realpath(p) + os.sep):
                raise BuildError(f'The output folder {p!r} overlaps the files folder {files_dir!r}. Use a separate output folder.')
    check_output_target(out)
    check_output_target(private_dir, 'private report folder')
    pub, priv = start_build(out), start_build(private_dir)
    try:
        ow = Outward(rec, R, files_dir)
        if not ow.tops:
            raise BuildError('No released fact would appear on the page (an excerpt appears only under its released parent). Set outward: true on at least one fact that is not an excerpt or a folded duplicate.')
        ow.decide()
        ow.copy_files(pub)
        missing = checks.gate_missing(rec['meta'])
        draft = bool(missing)
        token = 'SNAP-' + new_token()
        page = ow.render(draft, token)
        index_path = os.path.join(pub, 'index.html')
        with open(index_path, 'w', encoding='utf-8') as fh:
            fh.write(page.replace(token, 'SNAPSHOT-ID'))
        lines = snapshot_lines(pub, sha256_file(index_path))
        content_hash = sha256_text(lines)
        snap = None if draft else content_hash[:8]
        if not draft:
            with open(index_path, 'w', encoding='utf-8') as fh:
                fh.write(page.replace(token, snap))
        pii, notes = ow.scan(pub)
        if not R.ok:
            for w in R.warnings:
                print(f'note: {w}')
            print(checks.format_failure('HOME', R).strip())
            remove_made_dir(pub)
            remove_made_dir(priv)
            return 1
        meta = rec['meta']
        files = manifest_files(pub, ow.out_files)
        gate = rec['meta'].get('share_gate') or {}
        manifest = {'tool': 'build-the-record tools/views', 'draft': draft, 'snapshot': snap, 'content_sha256': content_hash, 'updated': meta['updated'],
                    'snapshot_rule': 'sha256 over lines "path<TAB>sha256" for every published file, sorted by path, first 8 hex characters. index.html is hashed with its snapshot id replaced by SNAPSHOT-ID.',
                    'recipient': gate.get('recipient'), 'share_gate_missing': missing, 'entries': len(ow.tops), 'documents': sorted(ow.docs_by_id), 'files': files}
        with open(os.path.join(priv, 'manifest.json'), 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh, indent=1)
        with open(os.path.join(priv, 'snapshot.json'), 'w', encoding='utf-8') as fh:
            json.dump({'snapshot': snap, 'draft': draft, 'updated': meta['updated'], 'entries': len(ow.tops), 'documents': sorted(ow.docs_by_id), 'manifest': 'manifest.json'}, fh)
        rep = [f'SHARE REPORT (private: never publish this folder)', f'Build: ' + (DRAFT_STAMP + ' (no snapshot id)' if draft else f'snapshot {snap}') + f'; last updated {meta["updated"]}']
        if draft:
            rep.append('Share gate not complete. Still to answer: ' + '; '.join(checks.GATE_WORDS[k] for k in missing) + '.')
        else:
            rep.append(f'Share gate complete. Recipient: {gate["recipient"]}.')
        rep += ['', f'Released: {len(ow.tops)} of {len(rec["facts"])} facts on the page; {len(ow.listed)} documents listed.', ''] + ow.report
        rep += ['', 'FILES THAT GO OUT (sha256):'] + [f'  {r["sha256"]}  {r["path"]}' + (f'  [{r["note"]}]' if r['note'] else '') for r in files]
        rep += ['', f'QUOTES: {R.verified} checked word for word and matched; {len(R.unverified)} could not be checked.'] + [f'  {u}' for u in R.unverified]
        rep += ['', 'NOTES FROM THE CHECKS:'] + ([f'  {w}' for w in R.warnings] or ['  none'])
        rep += ['', 'LOOK AT THESE YOURSELF (not scanned):'] + ([f'  {n}' for n in notes] or ['  none'])
        rep += ['', 'PERSONAL DETAILS FOUND IN OUTGOING TEXT (clear each one, or confirm it should be there):'] + ([f'  {p}' for p in pii] or ['  none found'])
        with open(os.path.join(priv, 'share-report.txt'), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(rep) + '\n')
        swap_into_place(pub, out)
        swap_into_place(priv, private_dir)
    except BaseException:
        for t in (pub, priv):
            if os.path.isdir(t):
                remove_made_dir(t)
        raise
    for w in R.warnings:
        print(f'note: {w}')
    where = f'{"DRAFT (share gate incomplete: no snapshot id)" if draft else "snapshot " + snap}'
    print(f'ok: {len(ow.tops)} of {len(rec["facts"])} entries outward, {len(ow.listed)} documents listed, {where}; quotes: {R.verified} verified, {len(R.unverified)} could not be checked; '
          f'{len(pii)} personal details to clear; report and manifest: {private_dir} -> {out}')
    if archive:
        return archive_sent(out, private_dir, archive, snap, gate.get('recipient'), draft)
    return 0


def archive_sent(out, private_dir, archive, snap, recipient, draft):
    if draft:
        raise BuildError('A draft is not a sent copy. Answer the share gate (recipient, confidentiality, names, defamation reminder, attorney read) and build again before using --archive.')
    dest = os.path.join(os.path.abspath(archive), f'{dt.date.today().isoformat()}-{snap}')
    if os.path.exists(dest):
        with open(os.path.join(dest, 'private', 'manifest.json'), encoding='utf-8') as fh:
            old = json.load(fh)
        with open(os.path.join(private_dir, 'manifest.json'), encoding='utf-8') as fh:
            new = json.load(fh)
        if old.get('content_sha256') != new.get('content_sha256'):
            raise BuildError(f'{dest!r} already holds a different copy with the same name. Sent copies are never overwritten; nothing was changed.')
        print(f'archive: {dest} already holds this exact copy')
        return 0
    os.makedirs(os.path.abspath(archive), exist_ok=True)
    tmp = dest + '.partial'
    if os.path.exists(tmp):
        raise BuildError(f'{tmp!r} is left over from an interrupted save. Look at it and remove it yourself, then run again.')
    shutil.copytree(out, os.path.join(tmp, 'published'))
    shutil.copytree(private_dir, os.path.join(tmp, 'private'))
    with open(os.path.join(tmp, 'sent.json'), 'w', encoding='utf-8') as fh:
        json.dump({'snapshot': snap, 'recipient': recipient, 'saved_on': dt.date.today().isoformat(), 'note': 'This tool never replaces or deletes this folder.'}, fh, indent=1)
    os.rename(tmp, dest)
    print(f'archive: saved this copy in {dest}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('record')
    ap.add_argument('out')
    ap.add_argument('--files-dir', help='the folder the record\'s exhibit file names are relative to')
    ap.add_argument('--strict', action='store_true', help='unverified quotes, unknown fields and the other pre-send checks become errors')
    ap.add_argument('--private-dir', help='where the share report and manifest go (default: OUTDIR-private)')
    ap.add_argument('--archive', help='also save a non-draft build in DIR/<date>-<snapshot>/ (never replaced or deleted)')
    a = ap.parse_args(argv)
    rec, errs = checks.load_record(a.record)
    if errs:
        print('HOME BUILD FAILED:')
        print('\n'.join(f' - {e}' for e in errs))
        return 1
    try:
        return build(rec, a.out, a.files_dir, a.strict, a.private_dir, a.archive)
    except BuildError as e:
        print(f'HOME BUILD FAILED: {e}')
        return 1
    except OSError as e:
        print(f'HOME BUILD FAILED: a file or folder could not be read or written ({e}). Check that the folder exists and that you may write there.')
        return 1
    except Exception as e:
        if os.environ.get('BTR_DEBUG'):
            raise
        print(f'HOME BUILD FAILED: something unexpected went wrong ({type(e).__name__}: {e}). This is a bug in the tool, not a mistake in your record. Run again with BTR_DEBUG=1 to see where.')
        return 2


if __name__ == '__main__':
    sys.exit(main())
