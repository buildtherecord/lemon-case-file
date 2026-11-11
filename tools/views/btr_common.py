"""Helpers shared by build_views.py, build_home.py and checks.py: dates, text, escaping, safe output folders.

Nothing here reads a record's meaning. Rules about the record live in checks.py."""
import datetime as dt, hashlib, html, json, os, re, shutil, tempfile, urllib.parse, uuid

MARKER = '.btr-output'
MARKER_TEXT = 'Made by Build the Record tools/views. This folder is replaced on the next build. Nothing else is deleted.\n'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
esc = html.escape


class BuildError(Exception):
    """A problem the person can fix. The message is plain language and names the file or fact."""


# ---------- dates ----------

def precision_of(s):
    return {4: 'year', 7: 'month', 10: 'day'}.get(len(s or ''))


def parse_date(s):
    """'2026-10-04' -> (date, 'day'); '2026-10' -> (date(2026,10,1), 'month'). The 1st is only a sort key, never shown."""
    p = precision_of(s)
    if p is None or not re.fullmatch(r'\d{4}(-\d{2}(-\d{2})?)?', s):
        raise ValueError(s)
    parts = [int(x) for x in s.split('-')]
    return dt.date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1), p


def eff_precision(s, explicit=None):
    """The precision a date is shown at: what the person said, but never finer than the text allows."""
    p = precision_of(s)
    return explicit or p


def period(s, explicit=None):
    """(first day, last day) the date can mean."""
    d, p = parse_date(s)
    p = eff_precision(s, explicit) if explicit else p
    if p == 'day':
        return d, d
    if p == 'month':
        nxt = dt.date(d.year + (d.month // 12), d.month % 12 + 1, 1)
        return dt.date(d.year, d.month, 1), nxt - dt.timedelta(days=1)
    return dt.date(d.year, 1, 1), dt.date(d.year, 12, 31)


def fmt_date(s, explicit=None):
    """'Oct 4, 2026' for a day, 'October 2024' for a month, '2024' for a year. Empty stays empty."""
    if not s:
        return ''
    try:
        d, p = parse_date(s)
    except ValueError:
        return s
    p = explicit or p
    if p == 'year':
        return str(d.year)
    if p == 'month':
        return f'{MONTHS[d.month - 1]} {d.year}'
    return f'{MONTHS[d.month - 1][:3]} {d.day}, {d.year}'


def fact_when(f):
    p = f.get('date_precision')
    return fmt_date(f['date'], p) + (f", {f['time']}" if f.get('time') and eff_precision(f['date'], p) == 'day' else '')


def fact_start(f):
    return period(f['date'], f.get('date_precision'))[0]


def fact_is_day(f):
    return eff_precision(f['date'], f.get('date_precision')) == 'day'


def fact_sort_key(f):
    return (fact_start(f).isoformat(), f.get('time') or '', f['id'])


def sorted_facts(facts):
    return sorted(facts, key=fact_sort_key)


def days_between(fa, fb):
    return (fact_start(fb) - fact_start(fa)).days


def range_label(a, b):
    """Date label for a section, made from its own start and end. Whole months read as months, whole years as years."""
    (a0, _), (_, b1) = period(a), period(b)
    if a0.day == 1 and (b1 + dt.timedelta(days=1)).day == 1:
        if a0.month == 1 and b1.month == 12:
            return str(a0.year) if a0.year == b1.year else f'{a0.year} to {b1.year}'
        la, lb = f'{MONTHS[a0.month - 1]} {a0.year}', f'{MONTHS[b1.month - 1]} {b1.year}'
        return la if la == lb else (f'{MONTHS[a0.month - 1]} to {lb}' if a0.year == b1.year else f'{la} to {lb}')
    return fmt_date(a0.isoformat()) if a0 == b1 else f'{fmt_date(a0.isoformat())} to {fmt_date(b1.isoformat())}'


# ---------- text and urls ----------

def qurl(path):
    """A relative path made safe for an href or src (spaces, #, ? and non-ASCII letters)."""
    return urllib.parse.quote(path.replace('\\', '/'), safe='/')


def is_http(u):
    return bool(re.match(r'(?i)^https?://', u or ''))


def host_of(u):
    return (urllib.parse.urlsplit(u).hostname or '').lower()


def script_json(obj):
    """JSON that is safe inside <script type="application/json">: no raw <, > or & can close the tag."""
    return json.dumps(obj, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def shorten(text, n):
    """Cut at a word boundary, never inside a quotation, and mark the cut."""
    text = ' '.join((text or '').split())
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(' ', 1)[0] if ' ' in text[:n] else text[:n]
    if cut.count('"') % 2 or cut.count('“') > cut.count('”'):
        q = max(cut.rfind('“'), cut.rfind('"'))
        if q > 0:
            cut = cut[:q].rstrip()
        else:
            close = max(text.find('”'), text.find('"', 1))
            if close > 0:
                return text[:close + 1] + (' …' if close + 1 < len(text) else '')
    return cut.rstrip(' ,;:-') + ' …'


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def new_token():
    return uuid.uuid4().hex


OPEN_ON_HASH_JS = (r'(function(){function o(e){for(var d=e&&e.closest&&e.closest("details");d;d=d.parentElement&&d.parentElement.closest("details"))d.open=true;}'
                   r'function h(){if(location.hash){var e=document.getElementById(decodeURIComponent(location.hash.slice(1)));o(e);if(e)e.scrollIntoView({block:"center"});}}'
                   r'addEventListener("hashchange",h);document.addEventListener("click",function(ev){var a=ev.target.closest&&ev.target.closest("a[href^=\\#]");'
                   r'if(a){var e=document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));o(e);}},true);h();})();')


# ---------- output folders: build in a temp sibling, swap in, delete only what this tool made ----------

def _same_or_inside(path, other):
    path, other = os.path.realpath(path), os.path.realpath(other)
    return path == other or path.startswith(other + os.sep)


def check_output_target(out, label='output folder'):
    """Plain error unless the folder is new, empty, or one this tool made before (it carries the marker file)."""
    if os.path.lexists(out):
        if not os.path.isdir(out) or os.path.islink(out):
            raise BuildError(f'The {label} {out!r} exists and is not a folder. Pick a new folder name.')
        if os.listdir(out) and not os.path.exists(os.path.join(out, MARKER)):
            raise BuildError(f'The {label} {out!r} already holds files that this tool did not make, so it will not replace them. '
                             f'Pick a new folder name, or move or delete that folder yourself.')


def start_build(out):
    """A new empty temp folder next to `out` (same disk, so the swap is one rename)."""
    parent = os.path.dirname(os.path.abspath(out)) or '.'
    os.makedirs(parent, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='.btr-build-', dir=parent)
    os.chmod(tmp, 0o755)
    with open(os.path.join(tmp, MARKER), 'w') as fh:
        fh.write(MARKER_TEXT)
    return tmp


def remove_made_dir(path):
    """Delete a folder only if this tool made it (marker present) or it is empty."""
    if not os.path.isdir(path) or os.path.islink(path):
        return
    if os.listdir(path) and not os.path.exists(os.path.join(path, MARKER)):
        raise BuildError(f'Refusing to delete {path!r}: it does not carry the marker this tool leaves in folders it makes.')
    shutil.rmtree(path)


def swap_into_place(tmp, out):
    old = None
    if os.path.lexists(out):
        old = f'{out}.btr-old-{new_token()[:8]}'
        os.rename(out, old)
    try:
        os.rename(tmp, out)
    except OSError:
        if old:
            os.rename(old, out)
        raise
    if old:
        remove_made_dir(old)


def tool_version():
    return 'build-the-record tools/views'
