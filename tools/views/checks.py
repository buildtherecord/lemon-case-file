#!/usr/bin/env python3
"""The one checker. build_views.py, build_home.py and the case converters all run it before anything is written.

  python3 checks.py record.json [--outward] [--strict] [--files-dir DIR]

It validates the record against schema/record.schema.json, then applies the doctrine:
  - advice and advocacy wording is checked only in what the claimant or assistant wrote, never in a document's own words
    and never inside quotation marks (so you can quote a letter that says "too late")
  - a quote must appear in a source text, word for word (only capitals, spacing and quote-mark style are ignored);
    a quote that drops a "not" or an "un-" fails; a quote with no source text to check against is reported as unverified
    (an error with --strict)
  - a number with a unit (days, times, visits, miles, faults, recordings, cases, documents, repair orders, attempts, emails, messages,
    calls, photos and the like, with a modifier word or two between) is never typed in prose: use {days:F1:F2}, {count:facts},
    {count:documents}, {count:recordings}, {interval:ID}, {miles:EXHIBIT:A:B} and the builder fills it in. A dollar figure in prose
    must appear in a document the fact cites. A figure the cited document itself states is allowed
  - ids use only letters, digits, - and _
  - deadlines are entered by the claimant with a source; the tool never computes or confirms one
  - a "documented" fact names at least one document and shares some key word, number or name with that document's text; an "open" fact is never worded as fact
  - a quote that stops right before "if", "or", "unless", "until", "but", "except" or "provided" is noted (an error with --strict)
  - a date written in a summary, section, span label or span note must be the date of a fact, span, document or deadline in the record;
    "is scheduled" or "will" about a date before the record's as-of date is noted (an error with --strict)
  - a shared link, file or thumbnail on a private host (private.example.com, plus tools/views/private-hosts.txt) stops the outward build
Every problem is a plain sentence that names the fact, exhibit or field. Nothing here raises a Python error for a bad record.
"""
import difflib, functools, json, os, re, sys, unicodedata, datetime as dt
from collections import defaultdict
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btr_common import (MONTHS, BuildError, esc, fmt_date, parse_date, period, precision_of, eff_precision, fact_start, fact_is_day, sorted_facts,
                    is_http, host_of, days_between)


def _fstart(f):
    try:
        return fact_start(f)
    except ValueError:
        return None


HERE = os.path.dirname(os.path.abspath(__file__))
_MONTH_NUM = {m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)}
SCHEMA_PATH = os.environ.get('BTR_RECORD_SCHEMA') or os.path.join(HERE, '..', '..', 'schema', 'record.schema.json')

STATUS = {'documented': 'Shows in a document', 'account': "Claimant's account", 'disputed': 'Disputed', 'open': 'Open question, not stated as fact'}
BANNER = ("Deadlines may apply that you and this page don't know about. Stopping or waiting does not stop a deadline and may give up rights. "
          "Ask someone who can advise you about your situation. This page is information, not legal advice.")
GATE_KEYS = ('recipient', 'confidentiality_checked', 'names_checked', 'defamation_reminder_ack', 'attorney_read')
GATE_WORDS = {'recipient': 'who will receive it', 'confidentiality_checked': 'whether settlement or confidentiality terms exist',
              'names_checked': 'whether it names people or businesses beyond what the documents say', 'defamation_reminder_ack': 'the defamation reminder',
              'attorney_read': 'whether an attorney has read it'}
DRAFT_STAMP = 'DRAFT — not reviewed for sending'

# ---------- wording the tool never uses in its own voice ----------

ADVICE = [
    (r"\byou (?:should|must|need to|ought to) (?:file|sue|settle|accept|reject|sign|appeal)\b", 'tells the reader what to do'),
    (r"\b(?:do not|don't|should not|shouldn't) file\b", 'says whether to file'),
    (r"\bfile (?:a|your) (?:lawsuit|complaint|appeal|claim|suit)\b[^.]{0,20}\b(?:now|today|immediately|soon|first)\b", 'says whether to file'),
    (r"\b(?:strong|weak|good|solid|winning|losing) (?:case|claim)\b", 'judges the strength of a case'),
    (r"\b(?:likely|unlikely|sure|certain|bound) to (?:win|succeed|prevail|lose)\b", 'predicts the outcome'),
    (r"\btoo late\b", 'says a deadline was missed'),
    (r"\b(?:deadline|time limit|limitations? period|statute of limitations)\b[^.]{0,40}\b(?:has|have|had) (?:already )?(?:passed|expired|run|lapsed)\b", 'says a deadline passed'),
    (r"\b(?:time|claim)[- ]barred\b", 'says a claim is barred'),
    (r"\byou (?:will|would|can|could) (?:win|lose|sue|recover|collect)\b", 'predicts the outcome'),
    (r"\bguarantee", 'promises a result'),
    (r"\byou have an? (?:valid|good|strong|solid|winning) (?:claim|case)\b", 'judges the claim'),
    (r"\bviolat(?:es|ed|ion of|ing) (?:the )?(?:law|laws|act|statute|statutes|code|regulations?)\b", 'applies law to the facts'),
    (r"\b(?:illegal(?:ly)?|unlawful(?:ly)?|against the law)\b", 'applies law to the facts'),
    (r"\b(?:breach(?:ed)?|breaking) (?:of )?(?:the )?(?:contract|warranty|agreement|lease)\b", 'applies law to the facts'),
    (r"\b(?:is|was|are|were) an? lemon\b|\bqualif(?:y|ies|ied) as an? lemon\b", 'applies law to the facts'),
    (r"\b(?:entitled to|owed|owes?) (?:a )?(?:full |complete )?(?:refund|repurchase|damages|compensation)\b", 'applies law to the facts'),
    (r"\bdays? (?:remaining|left) (?:to|until|before|on)\b", 'counts down to a deadline'),
    (r"\byou (?:can|may|must|should) (?:still )?(?:file|appeal) (?:by|before|within|until)\b", 'says when to file'),
    (r"\b(?:owners?|claimants?|buyers?|customers?|they|she|he|we)\s+(?:should|must|ought to|need to|needs to)\s+(?:file|sue|settle|accept|reject|appeal)\b", 'tells the reader what to do'),
    # a prognosis: who will win, the odds, the chances
    (r"\b(?:will|would|should|shall|might|may|could|can|going to)\s+(?:(?:very|most|quite|almost|also|easily|probably|likely|surely|certainly|definitely|possibly|ultimately|eventually|still)\s+)*(?:win|lose|prevail|succeed)\b", 'predicts the outcome'),
    (r"\b(?:likely|probably|surely|certainly|definitely|unlikely)\s+(?:to\s+)?(?:win|lose|prevail|succeed|be (?:successful|awarded|approved|denied|dismissed))\b", 'predicts the outcome'),
    (r"\b(?:will|would)\s+(?:most\s+)?(?:probably|likely|surely|certainly|definitely)\b", 'predicts the outcome'),
    (r"\b(?:good|great|strong|excellent|decent|fair|slim|slight|poor|little|better|best|real|high|low|small|realistic|reasonable|solid)\s+(?:chances?|odds|likelihood|probability|prospects?|shot)\b", 'predicts the outcome'),
    (r"\b(?:chances?|odds|likelihood|probability|prospects?)\s+(?:of|that|for)\s+(?:winning|succe\w+|prevail\w*|recover\w*|collect\w*|losing|a (?:win|loss|settlement|recovery))\b", 'predicts the outcome'),
    (r"\bodds\s+(?:are|favou?r)\b|\b(?:the|your|their|his|her|long|even|against the) odds\b", 'predicts the outcome'),
    # a deadline asserted in the tool's voice (a deadline belongs in 'deadlines', with the document's own words)
    (r"\b(?:deadline|time limit|limitations? period|statute of limitations|cut-?off|filing window)\s+(?:for\s+\w+(?:\s+\w+){0,3}\s+)?(?:is|was|will be|runs|expires|ends|falls on|lapses|closes)\b", 'asserts a deadline',
     r"\b(?:what|when|whether|how|if|unless)\b[^.]*$"),
    (r"\b(?:must|needs? to|has to|have to|should|shall|ought to)\s+(?:\w+\s+)?(?:file[ds]?|submit(?:ted)?|respond(?:ed)?|appeal(?:ed)?|sue[d]?|answer(?:ed)?|act|be filed|be submitted|be received|be postmarked)\s+(?:\w+\s+){0,3}?(?:by|before|within|no later than|prior to|until)\b", 'asserts a deadline'),
    (r"\b(?:has|have|had|gets?|got)\s+until\b", 'asserts a deadline'),
    # liability and law applied to the facts
    (r"\b(?:is|are|was|were|be|been|being|remains?|remained|becomes?|held)\s+(?:(?:also|legally|fully|solely|jointly|clearly|directly|personally)\s+)*(?:liable|at fault|to blame|negligent|guilty|culpable)\b", 'applies law to the facts'),
    (r"\b(?:broke|breaks|breaking|broken|breach(?:es|ed)?|violat\w+)\s+(?:(?:the|a|state|federal|consumer|these|those|its|their|his|her)\s+)*(?:laws?|statutes?|regulations?)\b", 'applies law to the facts'),
    (r"\blegally\s+(?:required|obligated|bound|responsible|liable|entitled|binding|wrong)\b", 'applies law to the facts'),
    (r"\b(?:should|must|ought to|need to|needs to|had better|better|recommend|recommended|advise|advised)\s+(?:(?:also|first|immediately|promptly|now|that|you|to)\s+)*(?:hire|retain|consult|contact|call|see|talk to|speak (?:to|with)|get|find|engage|seek|ask)\s+(?:\w+\s+){0,3}(?:lawyers?|attorneys?|counsel|solicitors?|law firm|legal (?:advice|help|counsel|representation))\b", 'tells the reader to get legal help'),
]
ADVOCACY = [
    (r"\b(?:clearly|obviously|blatant(?:ly)?|flagrant(?:ly)?|egregious(?:ly)?|outrageous(?:ly)?|shocking(?:ly)?|shameful(?:ly)?|disgraceful(?:ly)?|despicable|damning|devastating)\b", 'argues instead of stating'),
    (r"\b(?:scam(?:s|med|mer)?|swindle[ds]?|rip-?off|ripped off|cheated|crook(?:s|ed)?|predatory|bad faith|unconscionable)\b", 'argues instead of stating'),
    (r"(?<!consumer )\bfraud(?:ulent(?:ly)?)?\b(?! act)", 'argues instead of stating'),
    (r"\b(?:lied|lying|liar|deceived|deceit|misled)\b", 'argues instead of stating'),
    (r"\b(?:deliberate(?:ly)?|willful(?:ly)?|wilful(?:ly)?)\b", 'says what someone intended'),
    (r"\b(?:strongest|weakest|smoking gun)\b|\bproves? (?:that|the)\b", 'argues instead of stating'),
]
STATUTE = re.compile(r"\b\d+\s+ILCS\s+\d+/[\w().-]+|\b\d+\s+U\.?S\.?C\.?\s+§?\s*\d+|§\s*\d+")
# markers that mean "meant for counsel" when they appear in anything that goes outward
MARKERS = [(r'\bfor counsel\b', 'for counsel'), (r'\bprivileged\b', 'privileged'), (r'\bwork[- ]product\b', 'work product'),
           (r'\b(?:Rule|FRE|F\.R\.E\.|Fed\. ?R\. ?Evid\.) ?408\b', 'Rule 408')]
PII = [('email address', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')),
       ('phone number', re.compile(r'(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)')),
       ('street address', re.compile(r'\b\d{1,6}\s+(?:[NSEW]\.?\s+)?(?:[A-Z][A-Za-z0-9.\'-]*\s+){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Place|Pl|Circle|Cir|Terrace|Ter|Highway|Hwy)\b\.?')),
       ('state and ZIP code', re.compile(r'\b[A-Z]{2}\s\d{5}(?:-\d{4})?\b')),
       ('Social Security style number', re.compile(r'\b\d{3}-\d{2}-\d{4}\b')),
       ('long number (account or card?)', re.compile(r'(?<![\d$,.])\d{9,}(?![\d])'))]

_NUMW = r'(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|hundred|dozen|(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?)'
_UNIT = r'(?:days?|times?|visits?|miles?|faults?|recordings?|cases?|documents?)'
# more things a person counts. A four-digit year in front of one of these is read as a year, not a count.
_UNIT2 = r'(?:orders?|attempts?|trips?|e-?mails?|entr(?:y|ies)|incidents?|occasions?|appointments?|actions?|messages?|calls?|items?|pages?|photos?|videos?|clips?|texts?|letters?|notices?)'
# words that end a run of modifiers: a number then one of these then a noun is not "a count with modifiers"
_NOMOD = (r'(?:a|an|the|of|to|in|on|at|for|with|from|by|and|or|but|as|after|before|since|until|than|that|this|these|those|was|were|is|are|be|been|had|has|have|did|do|does|not|no|per|each|every|'
          r'into|over|under|about|between|during|within|without|while|when|where|who|which|what|how|we|they|he|she|it|you|our|their|his|her|its|my|your|also|then|so|if|am|pm|a\.m\.|p\.m\.)')
_COUNT_NUM = r'(?:\d[\d,]*(?:\.\d+)?|' + _NUMW + r')'
_COUNT_LEAD = r'(?<![\w$.,])(?<!\d:)(?<!\d{4}-\d\d-)(?<![A-Za-z]-)'
_MODS = r'(?:(?!' + _NOMOD + r'\b)[A-Za-z][A-Za-z\'-]*\s+){0,2}'
TYPED_COUNT = re.compile(_COUNT_LEAD + _COUNT_NUM + r'(?:-|\s+)(?:(?:more|additional|separate|different|consecutive|calendar|business|total|straight|other|prior|previous|recorded|repair|service|diagnostic|dealer|warranty|working)\s+){0,2}' + _UNIT + r'\b', re.I)
TYPED_COUNT2 = re.compile(_COUNT_LEAD + _COUNT_NUM + r'(?:-|\s+' + _MODS + r')(?P<unit>' + _UNIT + '|' + _UNIT2 + r')\b', re.I)  # 'two-way calls' is an adjective: after a hyphen the noun comes next
_YEARISH = re.compile(r'^(?:19|20)\d\d$')
PLACEHOLDER = re.compile(r'\{(\w+)((?::[^{}:\s]+)*)\}')
COUNT_NAMES = ('facts', 'documents', 'recordings', 'documented', 'claimant_docs', 'account', 'disputed', 'open')
NEGATORS = {'not', 'no', 'never', 'cannot', 'nor', 'neither', 'without', 'none', 'nobody', 'nothing', 'unable', 'hardly'}
DEADLINE_WINDOWS = (30, 45, 60, 90, 120, 180, 365)
RECORDING_EXT = ('.mp4', '.mov', '.m4v', '.webm', '.mp3', '.m4a', '.wav', '.aac')
UNIT_FIX = 'Write {days:F1:F2}, {count:facts}, {count:documents}, {count:recordings}, {interval:ID} or {miles:EXHIBIT:A:B} so the page computes it, cite a document that states the number in its own words, or put those words in quotation marks.'


# ---------- result ----------

class Result:
    def __init__(self, strict=False):
        self.strict = strict
        self.errors, self.warnings = [], []
        self.verified = 0
        self.unverified = []

    def error(self, msg):
        if msg not in self.errors:
            self.errors.append(msg)

    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)

    def soft(self, msg):
        """A problem that is a warning while drafting and an error with --strict (what you run before sending)."""
        (self.error if self.strict else self.warn)(msg)

    @property
    def ok(self):
        return not self.errors


# ---------- loading and the schema ----------

def load_record(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh), []
    except FileNotFoundError:
        return None, [f'The record file {path!r} was not found. Check the path.']
    except json.JSONDecodeError as e:
        return None, [f'{path!r} is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg}). A missing comma or quote is the usual cause.']
    except (OSError, UnicodeDecodeError) as e:
        return None, [f'The record file {path!r} could not be read: {e}.']


def normalize(rec):
    """A copy where null means absent, so a field set to null never reaches a builder."""
    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items() if v is not None}
        if isinstance(x, list):
            return [walk(v) for v in x]
        return x
    return walk(rec)


def load_schema():
    try:
        with open(SCHEMA_PATH, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise BuildError(f'The record schema was not found or is not valid ({os.path.abspath(SCHEMA_PATH)}: {e}). '
                         f'tools/views needs schema/record.schema.json beside it in the repository.')


_JSON_TYPES = {'string': str, 'array': list, 'object': dict, 'boolean': bool, 'null': type(None)}
_TYPE_WORDS = {'string': 'text', 'number': 'a number', 'integer': 'a whole number', 'boolean': 'true or false', 'array': 'a list', 'object': 'a group of fields', 'null': 'empty'}


def _is_type(v, t):
    if t in ('number', 'integer'):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and (t == 'number' or float(v).is_integer())
    return isinstance(v, _JSON_TYPES[t])


def _type_name(v):
    if isinstance(v, bool):
        return 'true or false'
    return _TYPE_WORDS.get({str: 'string', list: 'array', dict: 'object', int: 'number', float: 'number', type(None): 'null'}.get(type(v), 'string'), 'something else')


def validate_schema(inst, schema, root, path, issues):
    """A small JSON Schema 2020-12 checker for the keywords schema/record.schema.json uses. Issues are (path, keyword, detail)."""
    if '$ref' in schema:
        node = root
        for part in schema['$ref'].lstrip('#/').split('/'):
            node = node[part]
        return validate_schema(inst, node, root, path, issues)
    if 'oneOf' in schema:
        probe = [[] for _ in schema['oneOf']]
        for sub, buf in zip(schema['oneOf'], probe):
            validate_schema(inst, sub, root, path, buf)
        if sum(1 for b in probe if not b) != 1:
            issues.append((path, 'oneOf', None))
        return
    if 'const' in schema and inst != schema['const']:
        issues.append((path, 'const', schema['const']))
        return
    if 'enum' in schema and inst not in schema['enum']:
        issues.append((path, 'enum', schema['enum']))
        return
    if 'type' in schema:
        types = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        if not any(_is_type(inst, t) for t in types):
            issues.append((path, 'type', types))
            return
    if isinstance(inst, str):
        if len(inst.strip()) < schema.get('minLength', 0):
            issues.append((path, 'minLength', schema['minLength']))
        if 'pattern' in schema and not re.search(schema['pattern'], inst):
            issues.append((path, 'pattern', schema['pattern']))
    if isinstance(inst, list):
        if len(inst) < schema.get('minItems', 0):
            issues.append((path, 'minItems', schema['minItems']))
        if 'items' in schema:
            for i, v in enumerate(inst):
                validate_schema(v, schema['items'], root, path + (i,), issues)
    if isinstance(inst, dict):
        for k in schema.get('required', []):
            if k not in inst:
                issues.append((path + (k,), 'required', None))
        props = schema.get('properties', {})
        for k, v in inst.items():
            if k in props:
                validate_schema(v, props[k], root, path + (k,), issues)
            elif schema.get('additionalProperties') is False:
                issues.append((path + (k,), 'additional', list(props)))


def _where(rec, path):
    """('facts', 3, 'sources', 0, 'ex') -> 'fact F4, source 1' (the person's own id, never a list index)."""
    if not path or (len(path) == 1 and path[0] != 'meta'):
        return 'the record'
    top = path[0]
    names = {'facts': 'fact', 'exhibits': 'exhibit', 'people': 'person', 'issues': 'topic', 'lanes': 'lane', 'spans': 'span', 'beats': 'section',
             'intervals': 'interval', 'deadlines': 'deadline', 'held_back': 'held-back item'}
    if top == 'meta':
        return 'the record\'s meta' + (f" '{path[1]}'" if len(path) > 1 else '')
    if top in names and len(path) > 1 and isinstance(path[1], int):
        try:
            item = rec[top][path[1]]
        except (KeyError, IndexError, TypeError):
            item = None
        label = None
        if isinstance(item, dict):
            label = item.get('id') or item.get('title') or item.get('label')
        label = label if isinstance(label, str) and label else f'#{path[1] + 1}'
        out = f'{names[top]} {label}'
        if len(path) > 3 and path[2] == 'sources' and isinstance(path[3], int):
            out += f', source {path[3] + 1}'
        return out
    return f"'{top}'"


def _field_of(path):
    return str(path[-1]) if path and not isinstance(path[-1], int) else (str(path[-2]) if len(path) > 1 else '')


HINTS = {'date': 'write it as 2026-10-04 (2026-10 for a month, 2026 for a year)', 'status': 'use documented, account, disputed or open',
         'text': 'say what happened', 'id': 'give it a short id such as F12 (letters, digits, - and _)', 'title': 'give it a short title',
         'summary': 'one or two plain sentences about what happened', 'updated': "this is the 'Last updated' stamp shown at the top of every page, for example Oct 4, 2026, 9:00 AM CDT",
         'ex': 'name the id of the exhibit it points to', 'source': 'say where it is written, or who told the claimant', 'label': 'give it a short label',
         'a': 'name the id of the first fact', 'b': 'name the id of the second fact', 'from': 'write the first day, for example 2025-01-01', 'to': 'write the last day',
         'start': 'write the first day, for example 2025-01-01', 'end': 'write the last day', 'name': 'give the person a name', 'facts': 'a record needs at least one fact'}


def schema_messages(rec, issues):
    errs, extras = [], []
    for path, kw, detail in issues:
        where, field = _where(rec, path), _field_of(path)
        val = rec
        try:
            for p in path:
                val = val[p]
        except (KeyError, IndexError, TypeError):
            val = None
        if kw == 'required':
            errs.append(f"{_where(rec, path[:-1])}: '{path[-1]}' is missing; {HINTS.get(path[-1], 'add it')}.")
        elif kw == 'type':
            want = ' or '.join(_TYPE_WORDS[t] for t in detail if t != 'null') or 'text'
            errs.append(f"{where}: '{field}' should be {want}, not {_type_name(val)}.")
        elif kw == 'enum':
            errs.append(f"{where}: '{field}' is {val!r}; it must be one of: {', '.join(str(x) for x in detail)}.")
        elif kw == 'const' or kw == 'oneOf':
            errs.append(f"{where}: '{field}' is not allowed here; use \"all\" or a list of lane ids." if field == 'lanes' else f"{where}: '{field}' has a value this tool does not accept.")
        elif kw == 'minLength':
            errs.append(f"{where}: '{field}' is empty; {HINTS.get(field, 'fill it in')}.")
        elif kw == 'minItems':
            errs.append(f"{where}: '{field}' needs at least one entry.")
        elif kw == 'pattern':
            if str(detail).startswith('^[A-Za-z0-9_-]'):
                errs.append(f"{where}: {field} {val!r} is not a safe id. Ids use only letters, digits, - and _ (no spaces, slashes or quotation marks), up to 40 characters.")
            else:
                errs.append(f"{where}: '{field}' is {val!r}; write a date as 2026-10-04 (2026-10 for a month, 2026 for a year).")
        elif kw == 'additional':
            near = difflib.get_close_matches(str(path[-1]), detail, n=1, cutoff=0.7)
            extras.append(f"{_where(rec, path[:-1])}: '{path[-1]}' is not a field this tool reads, so it is ignored" + (f" (did you mean '{near[0]}'?)" if near else '') + '.')
    return errs, extras


# ---------- quotation marks and quotes ----------

_CURLY = re.compile(r'“([^”]*)”')
_STRAIGHT = re.compile(r'"([^"]*)"')


def extract_quotes(text):
    """The words inside double quotation marks, curly or straight."""
    out = [m.group(1) for m in _CURLY.finditer(text)]
    rest = _CURLY.sub(' ', text)
    out += [m.group(1) for m in _STRAIGHT.finditer(rest)]
    return [q for q in out if q.strip()]


def strip_quotes(text):
    return _STRAIGHT.sub(' ¶ ', _CURLY.sub(' ¶ ', text))


def unbalanced_quotes(text):
    rest = _CURLY.sub(' ', text)
    return rest.count('"') % 2 == 1 or rest.count('“') != rest.count('”')


@functools.lru_cache(maxsize=2048)
def norm_words(s):
    """Lower-case, one space, straight quotes, dashes as ' - '. Digits, punctuation and currency stay: $48.00 is not $4,800."""
    s = unicodedata.normalize('NFKC', s or '')
    s = s.replace('​', '').replace('­', '').replace('﻿', '')
    s = re.sub(r'[“”„‟«»]', '"', s)
    s = re.sub(r'[‘’‚‛‹›`´]', "'", s)
    s = re.sub(r'\s*[–—―]\s*', ' - ', s)
    s = s.replace('−', '-')
    return re.sub(r'\s+', ' ', s).strip().casefold()


_ELLIPSIS = re.compile(r'\s*(?:\[\s*(?:…|\.\.\.)\s*\]|…|\.\.\.|\. \. \.)\s*')


def _piece(p):
    p = norm_words(p).lstrip(' "\'').rstrip(' "\'')
    return p.rstrip('.,;:!?').rstrip(' "\'')


def _boundary(piece):
    return re.compile(r'(?<![\w-])(?<!\d[.,])' + re.escape(piece) + r'(?![\w-])(?![.,]\d)')


def _negated_edge(text, start, end):
    """True when a negator sits right before the match or right after it (the quote cut off a 'not')."""
    m = re.search(r'(\S+)\s+$', text[:start])
    if m and m.group(1)[-1] not in '.,;:!?"' and (m.group(1).strip('"\'()') in NEGATORS or m.group(1).endswith("n't")):
        return m.group(1).strip('"\'()')
    m = re.match(r'\s+(\S+)', text[end:])
    if m and text[end:end + 1].isspace():
        tok = m.group(1).rstrip('.,;:!?')
        if tok in NEGATORS or tok.endswith("n't"):
            return tok
    return None


def verify_quote(quote, text):
    """('ok'|'missing'|'negation', detail). Whole words only; a 'not' or 'un-' just outside the quote fails it."""
    pieces = [x for x in (_piece(p) for p in _ELLIPSIS.split(quote or '')) if x]
    if not pieces:
        return 'ok', None
    hay = norm_words(text)
    first = _boundary(pieces[0])
    seen_negation = None
    for m in first.finditer(hay):
        end, ok = m.end(), True
        for p in pieces[1:]:
            n = _boundary(p).search(hay, end)
            if not n:
                ok = False
                break
            end = n.end()
        if not ok:
            continue
        neg = _negated_edge(hay, m.start(), end)
        if neg is None:
            return 'ok', None
        seen_negation = neg
    return ('negation', seen_negation) if seen_negation else ('missing', None)


# ---------- placeholders ----------

def placeholders_in(text):
    return [(m.group(0), m.group(1), [a for a in m.group(2).split(':') if a]) for m in PLACEHOLDER.finditer(text or '')]


def expand(text, resolver):
    """Fill {days:..}, {count:..}, {interval:..} from the record. `resolver(kind, args)` returns a string."""
    return PLACEHOLDER.sub(lambda m: resolver(m.group(1), [a for a in m.group(2).split(':') if a]), text or '')


def make_resolver(facts_by, intervals_by, counts, exhibits=None, ledger=None, authorities=None):
    """The function expand() calls. Everything it returns is computed from the record; nothing is typed.
    exhibits ({id: exhibit}) is needed only for {miles:EXHIBIT:A:B}, the difference of two odometer readings that are both in that exhibit's text."""
    def resolve(kind, args):
        if kind == 'miles':
            if exhibits is None or len(args) != 3 or args[0] not in exhibits:
                raise BuildError('{miles:EXHIBIT:A:B} needs an exhibit of the record and two odometer readings; the builder was not given the exhibits.')
            a, b = reading(args[1]), reading(args[2])
            have = whole_numbers_in(exhibits[args[0]].get('text'))
            if a is None or b is None or a not in have or b not in have or b <= a:
                raise BuildError(f'{{miles:{":".join(args)}}}: both odometer readings must be in the text of exhibit {args[0]}, the second larger than the first.')
            return f'{b - a:,}'
        if kind == 'days':
            return str(days_between(facts_by[args[0]], facts_by[args[1]]))
        if kind == 'interval':
            iv = intervals_by[args[0]]
            return str(days_between(facts_by[iv['a']], facts_by[iv['b']]))
        if kind == 'count':
            return str(counts[args[0]])
        if kind == 'sum':
            if ledger is None:
                raise BuildError('{sum:...} needs the ledger; the builder was not given it.')
            rows = select_entries(ledger, args, authorities or {}, facts_by)
            return fmt_money(sum((entry_value(e) for e in rows), Decimal(0)))
        raise BuildError(f'{{{kind}}} is not a placeholder this tool knows.')
    return resolve


def _no_placeholders(text):
    return PLACEHOLDER.sub('⟦n⟧', text or '')


def lint_authored(text, banned=()):
    """[(kind, snippet, why)] for wording the tool does not use. Quoted words and placeholders are left alone."""
    plain = strip_quotes(_no_placeholders(text))
    out, spans = [], []
    for entry in ADVICE:
        pat, why = entry[0], entry[1]
        for m in re.finditer(pat, plain, re.I):
            if len(entry) > 2 and re.search(entry[2], plain[max(0, m.start() - 60):m.start()], re.I):
                continue  # 'what the deadline is' reports that something is missing; it does not assert one
            if any(m.start() < b and a < m.end() for a, b in spans):
                break  # the same words already reported by another rule
            spans.append((m.start(), m.end()))
            out.append(('advice', m.group(0), why))
            break
    for pat, why in ADVOCACY:
        m = re.search(pat, plain, re.I)
        if m:
            out.append(('advocacy', m.group(0), why))
    for w in banned:
        m = re.search(r'(?<![\w-])' + re.escape(w.strip()) + r'(?![\w-])', plain, re.I) if w.strip() else None
        if m:
            out.append(('banned', m.group(0), 'this case lists it as a word it never uses'))
    return out


def typed_counts(text):
    """Numbers with a unit typed into prose. 'one-time fee' is an adjective, not a count, and is left alone.
    A clock time ('11:18 recording'), a day of the month ('September 28 message'), a year before a thing ('the 2025 letters'),
    'one-on-one texts' and 'no one calls' are not counts."""
    plain = strip_quotes(_no_placeholders(text))
    found = []

    def keep(m, new_noun=False):
        lead = re.match(r'[^-\s]+', m.group(0)).group(0)
        if lead.casefold() == 'one' and re.search(r'(?i)\b(?:no|any|every|each|which|this|that|another)\s+$', plain[:m.start()]):
            return False  # 'no one calls' is not a count of calls
        if re.search(r'\b' + _MONTH_RX + r'\.?\s+$', plain[:m.start()]):
            return False  # 'the September 28 message' is a day of the month
        if new_noun and (_YEARISH.match(lead) or re.match(r'(?i)one-', m.group(0))):
            return False  # 'the 2025 letters' is a year; 'a one-page letter' is an adjective
        return not re.search(r'-times?$', m.group(0), re.I)

    for m in TYPED_COUNT.finditer(plain):
        if keep(m):
            found.append((m.start(), m.group(0)))
    for m in TYPED_COUNT2.finditer(plain):
        if keep(m, re.fullmatch(_UNIT2, m.group('unit'), re.I) is not None) and not any(a <= m.start() < a + len(t) for a, t in found):
            found.append((m.start(), m.group(0)))
    return [t for _a, t in sorted(found)]


def marker_hits(text, allow=()):
    allow = {a.casefold() for a in allow}
    return sorted({label for pat, label in MARKERS if re.search(pat, text or '', re.I) and label.casefold() not in allow})


def phrase_hits(text, phrases):
    hay = norm_words(text)
    return sorted({p for p in phrases if p and re.search(r'(?<![\w-])' + re.escape(norm_words(p)) + r'(?![\w-])', hay)})


def pii_findings(text):
    out = []
    for label, rx in PII:
        for m in rx.finditer(text or ''):
            out.append((label, m.group(0)))
    return out


def gate_missing(meta):
    g = meta.get('share_gate') or {}
    miss = []
    for k in GATE_KEYS:
        v = g.get(k)
        if k == 'recipient':
            if not (isinstance(v, str) and v.strip()):
                miss.append(k)
        elif v is not True:
            miss.append(k)
    return miss


def is_recording(e):
    k = (e.get('kind') or '').lower()
    ext = os.path.splitext((e.get('file') or '').split('?')[0])[1].lower()
    return k.startswith(('video', 'recording', 'audio')) or ext in RECORDING_EXT


STILL_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.tif', '.tiff')


def still_chain(e, exhibits):
    """Every exhibit above this one through excerpt_of, nearest first: a still of an excerpt of a recording gives [the excerpt, the recording]."""
    out, cur = [], e
    while cur.get('excerpt_of') in exhibits and cur['excerpt_of'] not in out:
        cur = exhibits[cur['excerpt_of']]
        out.append(cur['id'])
    return out


def still_of(e, exhibits):
    """The id of the recording this picture was taken from (the original, not an excerpt of it), or None."""
    recs = [i for i in still_chain(e, exhibits) if is_recording(exhibits[i]) and os.path.splitext((exhibits[i].get('file') or '').split('?')[0])[1].lower() not in STILL_EXT]
    return recs[-1] if recs else None


def is_still(e, exhibits):
    """A picture of a moment in a recording (a still frame or poster). It is shown as a picture, never as a recording."""
    k = (e.get('kind') or '').lower()
    ext = os.path.splitext((e.get('file') or '').split('?')[0])[1].lower()
    return bool(re.search(r'\bstill\b|\bposter\b|\bframe\b', k)) or (ext in STILL_EXT and still_of(e, exhibits) is not None)


def held_phrases(rec):
    out = list(rec.get('meta', {}).get('held_phrases') or [])
    for h in rec.get('held_back') or []:
        if isinstance(h, str):
            out.append(h)
        elif isinstance(h, dict) and isinstance(h.get('phrase'), str):
            out.append(h['phrase'])
    return [p for p in out if p.strip()]


def display_status(f, exhibits, claimant_label=None):
    """(key, words). A fact that only the claimant's own documents support says whose document, not 'documented'."""
    st = f['status']
    if st != 'documented':
        return st, STATUS[st]
    cited = [exhibits[s['ex']] for s in f.get('sources', []) if s['ex'] in exhibits]
    if cited and all(e.get('author') == 'claimant' for e in cited):
        who = claimant_label or "the claimant's"
        kinds = {(e.get('kind') or 'document').lower() for e in cited}
        noun = next(iter(kinds)) if len(cited) == 1 else ('documents' if len(kinds) > 1 or len(cited) > 1 else next(iter(kinds)))
        dates = sorted({(e.get('date') or '', e.get('date_precision')) for e in cited if e.get('date')})
        when = ''
        if dates:
            a, b = fmt_date(*dates[0]), fmt_date(*dates[-1])
            when = f' of {a}' if a == b else f' of {a} to {b}'
        return 'claimant_doc', f'Per {who} {noun}{when}'
    return 'documented', STATUS['documented']


def authored(rec):
    """(where, text, fact_or_None, shows_outward) for everything the claimant or assistant wrote that a page can show.
    shows_outward is True when the outward page would print it (only released facts, shared documents, and the few meta fields it prints)."""
    m = rec['meta']
    shared = {e['id'] for e in rec.get('exhibits', []) if e.get('share') is True}
    for k in ('title', 'subtitle', 'summary', 'ask', 'amount', 'contact_note', 'lawyer', 'sent_to_other_side', 'offers', 'footer', 'claimant_label'):
        if isinstance(m.get(k), str):
            yield f"the record's {k}", m[k], None, k in ('title', 'subtitle', 'summary', 'ask', 'contact_note')
    ab = m.get('absences')
    for a in ([ab] if isinstance(ab, str) else (ab or [])):
        yield "the record's absences", a, None, False
    for p in rec.get('people', []):
        if p.get('role'):
            yield f"person {p['id']} (role)", p['role'], None, False
    for x in rec.get('issues', []):
        yield f"topic {x['id']}", x['label'], None, False
    for x in rec.get('lanes', []):
        yield f"lane {x['id']}", x['label'], None, True
    for e in rec.get('exhibits', []):
        for k in ('title', 'caption', 'kind'):
            if e.get(k):
                yield f"exhibit {e['id']} ({k})", e[k], None, e['id'] in shared
    for f in rec['facts']:
        yield f"fact {f['id']}", f['text'], f, f.get('outward') is True
    for b in rec.get('beats', []):
        for k in ('title', 'line'):
            if b.get(k):
                yield f"section {b['title']!r} ({k})", b[k], None, True
        for i, p in enumerate(b.get('prose', [])):
            yield f"section {b['title']!r} (paragraph {i + 1})", p, None, True
    for s in rec.get('spans', []):
        for k in ('label', 'note'):
            if s.get(k):
                yield f"span {s['label']!r} ({k})", s[k], None, True
    for i in rec.get('intervals', []):
        yield f"interval {i['label']!r}", i['label'], None, True
    for a in rec.get('authorities', []):
        for k in ('kind', 'note'):
            if a.get(k):
                yield f"authority {a['id']} ({k})", a[k], None, False
    for e in rec.get('ledger', []):
        for k in ('note', 'method'):
            if e.get(k):
                yield f"ledger entry {e['id']} ({k})", e[k], None, False
    st = m.get('standing') or {}
    for k in ('builder_role', 'permission'):
        if isinstance(st.get(k), str):
            yield f"the record's standing ({k})", st[k], None, False
    for d in rec.get('deadlines', []):
        yield f"deadline {d['label']!r}", d['label'], None, False
        if d.get('source'):
            yield f"deadline {d['label']!r} (where it is written)", d['source'], None, False


# ---------- private hosts ----------

DEFAULT_PRIVATE_HOSTS = ('private.example.com',)


def private_hosts():
    """Hosts a shared link, file or thumbnail may never point at: private.example.com plus every line of tools/views/private-hosts.txt
    (optional, kept out of git; BTR_PRIVATE_HOSTS_FILE names another file). A line is a host name and covers that host and every site under it."""
    hosts = list(DEFAULT_PRIVATE_HOSTS)
    named = os.environ.get('BTR_PRIVATE_HOSTS_FILE')
    path = named or os.path.join(HERE, 'private-hosts.txt')
    try:
        with open(path, encoding='utf-8') as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        if named:
            raise BuildError(f'The private hosts file {path!r} (from BTR_PRIVATE_HOSTS_FILE) was not found. Fix the path, or unset it.')
        lines = []
    except (OSError, UnicodeDecodeError) as e:
        raise BuildError(f'The private hosts file {path!r} could not be read ({e}). Fix it or remove it; without it only the example host is blocked.')
    for ln in lines:
        h = re.sub(r'^[A-Za-z][A-Za-z0-9+.-]*://', '', ln.split('#', 1)[0].strip().lower()).split('/')[0].lstrip('*.').strip('.')
        if h:
            hosts.append(h)
    return sorted(set(hosts))


def is_private_host(host):
    host = (host or '').lower().rstrip('.')
    return any(host == h or host.endswith('.' + h) for h in private_hosts())


def private_url_rx():
    """A pattern for any http(s) address that names a private host anywhere in it. m.group(0) is the address."""
    return re.compile(r'https?://[^"\'\s<>\\]*(?:' + '|'.join(re.escape(h) for h in private_hosts()) + r')[^"\'\s<>\\]*', re.I)


# ---------- figures: dollars and odometer readings ----------

_NUM_TOKEN = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
_DOLLAR = re.compile(r'(?<![\w.])\$\s?(' + _NUM_TOKEN + r')(?:\s?(thousand|million|billion)\b|(?<=\d)(k|m)\b)?', re.I)
_MULT = {'thousand': 1000, 'k': 1000, 'million': 10 ** 6, 'm': 10 ** 6, 'billion': 10 ** 9}
_ANY_NUM = re.compile(r'(?<![\w.,])(' + _NUM_TOKEN + r')(?![\w]|[.,]\d)(?:\s?(thousand|million|billion)\b)?', re.I)


def _dec(num, suffix=None):
    try:
        v = Decimal(num.replace(',', ''))
    except InvalidOperation:
        return None
    return v * _MULT[suffix.lower()] if suffix else v


def dollar_figures(text):
    """[(as written, value)] for every $ amount in the text outside quotation marks and placeholders."""
    out = []
    for m in _DOLLAR.finditer(strip_quotes(_no_placeholders(text))):
        v = _dec(m.group(1), m.group(2) or m.group(3))
        if v is not None:
            out.append((m.group(0).strip(), v))
    return out


def figures_in(text):
    """Every number in a document's text, as a value ($4,800 and 4800.00 are the same figure; $48.00 is not)."""
    return {v for m in _ANY_NUM.finditer(text or '') for v in [_dec(m.group(1), m.group(2))] if v is not None}


def reading(s):
    """'48,210' or '48210' -> 48210, or None when it is not a whole number."""
    return int(s.replace(',', '')) if re.fullmatch(r'\d{1,3}(?:,\d{3})+|\d+', s or '') else None


def whole_numbers_in(text):
    return {int(m.group(0).replace(',', '')) for m in re.finditer(r'(?<![\w.,])(?:\d{1,3}(?:,\d{3})+|\d+)(?![\w]|[.,]\d)', text or '')}


# ---------- does the cited document show the fact? ----------

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'’]*")
_KEYNUM = re.compile(r'(?<![\w.,])\$?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)')
_SMALLSTOP = frozenset("""about above after again against almost along already also although always among another around because been before being below between both could does doing done during
each either enough every first found from given going have having here however into itself just later least less made make many might more most much must never next none often only other others
over perhaps quite rather really same several shall should since some still such than that their them then there these they thing things this those though through today under until upon used using
very want wants were what when where whether which while whose will with within without would yesterday wrote written writes write stated states state shows showed shown showing says said asked asks""".split())
_NOTNAME = frozenset(m.casefold() for m in MONTHS) | {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'} | _SMALLSTOP
_MONTH_RX = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
_WRITTEN_DATE = re.compile(r'\b(' + _MONTH_RX + r')\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b|\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + _MONTH_RX + r')\.?,?\s+(\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b')


_MONTH_DAY = re.compile(r'\b' + _MONTH_RX + r'\.?\s+\d{1,2}(?:st|nd|rd|th)?\b')


def _stem(w):
    w = re.sub(r"['’]s?$", '', w.casefold())
    for suf in ('ations', 'ation', 'ments', 'ment', 'ings', 'ing', 'edly', 'ed', 'es', 'ly', 's'):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)]
    return w


def _numkey(s):
    """'4,800' and '4800.00' are the same number; '48.00' is not."""
    try:
        return format(Decimal(s.replace(',', '')).normalize(), 'f')
    except InvalidOperation:
        return s


def key_tokens(text):
    """[(kind, key, as written)] for what is distinctive in a fact: a number, a name or code, or a word of five letters or more that is not a stop word."""
    plain = _MONTH_DAY.sub(' ', _WRITTEN_DATE.sub(' ', _no_placeholders(text)))
    out, seen = [], set()

    def add(kind, key, shown):
        if (kind, key) not in seen:
            seen.add((kind, key))
            out.append((kind, key, shown))

    for m in _KEYNUM.finditer(plain):
        add('n', _numkey(m.group(1)), m.group(0))
    for m in _WORD.finditer(plain):
        w = m.group(0)
        low = w.casefold()
        prev = plain[:m.start()].rstrip()
        initial = not prev or prev[-1] in '.!?:;“"('
        if re.search(r'\d', w) or (len(w) >= 2 and w.isupper() and w.isalpha()):
            add('a', low, w)
        elif w[0].isupper() and len(w) >= 3 and not initial and low not in _NOTNAME:
            add('a', _stem(low), w)
        elif len(w) >= 5 and low not in _SMALLSTOP and low not in _NOTNAME:
            add('w', _stem(low), w)
    return out


def doc_tokens(text):
    plain = text or ''
    nums = {_numkey(m.group(1)) for m in _KEYNUM.finditer(plain)}
    words = {m.group(0).casefold() for m in _WORD.finditer(plain)}
    return nums, words, {_stem(w) for w in words}


def shows_it(f, cited):
    """True when a documented fact shares something with the text of the documents it cites. cited: [(source, exhibit)] and every exhibit has text."""
    for s, e in cited:
        if s.get('loc') and s.get('quote') and verify_quote(s['quote'], e['text'])[0] == 'ok':
            return True  # the person gave the place and the document's own words, and the words are in the document
    toks = key_tokens(f['text'])
    if not toks:
        return True
    nums, words, stems = set(), set(), set()
    for _s, e in cited:
        a, b, c = doc_tokens(e['text'])
        nums |= a
        words |= b
        stems |= c
    return any((k in nums) if kind == 'n' else (k in words or k in stems) for kind, k, _shown in toks)


# ---------- a quote that stops before a qualifier ----------

QUALIFIERS = ('if', 'or', 'unless', 'until', 'but', 'except', 'provided')


def clipped_before(quote, text):
    """The qualifier ('unless', 'if', ...) that comes right after a verbatim quote in the document, or None. A quote that ends in an ellipsis is meant to be partial."""
    if re.search(r'(?:…|\.\.\.|\[\s*…\s*\])\s*["”\'’]*\s*$', (quote or '').strip()):
        return None
    pieces = [x for x in (_piece(p) for p in _ELLIPSIS.split(quote or '')) if x]
    if not pieces:
        return None
    hay = norm_words(text)
    found = None
    for m in _boundary(pieces[0]).finditer(hay):
        end, ok = m.end(), True
        for p in pieces[1:]:
            n = _boundary(p).search(hay, end)
            if not n:
                ok = False
                break
            end = n.end()
        if not ok or _negated_edge(hay, m.start(), end) is not None:
            continue
        tail = re.sub(r'^["\')\]]+', '', hay[end:].lstrip())
        if not tail or tail[0] in '.!?':
            return None  # the sentence ends here
        nxt = re.match(r'[,;:]?\s*(?:-\s+)?([a-z]+)\b', tail)
        if not nxt or nxt.group(1) not in QUALIFIERS:
            return None
        found = found or nxt.group(1)
    return found


# ---------- dates written in prose ----------

_FUTURE = re.compile(r'\b(?:(?:is|are)\s+(?:currently\s+|now\s+)?(?:scheduled|set|slated|planned|due|expected|booked)|(?:[Ss]cheduled|[Ss]et|[Ss]lated|[Pp]lanned|[Bb]ooked)\s+(?:for|on)|will(?:\s+be)?|upcoming|to be held)\b')


def written_dates(plain):
    """[(as written, date or None, start, end)] for dates written like March 12, 2025, 12 March 2025 or 2025-03-12."""
    out = []
    for m in _WRITTEN_DATE.finditer(plain):
        try:
            if m.group(1):
                d = dt.date(int(m.group(3)), _MONTH_NUM[m.group(1)[:3].lower()], int(m.group(2)))
            elif m.group(5):
                d = dt.date(int(m.group(6)), _MONTH_NUM[m.group(5)[:3].lower()], int(m.group(4)))
            else:
                d = dt.date(int(m.group(7)), int(m.group(8)), int(m.group(9)))
        except ValueError:
            d = None
        out.append((m.group(0), d, m.start(), m.end()))
    return out


_NARRATIVE = re.compile(r"the record's (?:title|subtitle|summary)$|section .* \((?:line|paragraph \d+)\)$|span .* \((?:label|note)\)$")
_OWN_ENTRY = re.compile(r"the record's (?:ask|amount|contact_note|lawyer|footer|claimant_label|sent_to_other_side|offers|absences)\b")


def _check_dates_in_prose(R, rec, meta, facts, exhibits):
    known = set()

    def add(v, prec=None):
        try:
            d, p = parse_date(v)
        except (ValueError, TypeError):
            return
        if (prec or p) == 'day':
            known.add(d)

    for f in facts:
        add(f['date'], f.get('date_precision'))
        if f.get('end'):
            add(f['end'])
    for sp in rec.get('spans', []):
        add(sp['start'])
        add(sp['end'])
    for e in exhibits.values():
        if e.get('date'):
            add(e['date'], e.get('date_precision'))
        if e.get('end'):
            add(e['end'])
    for dl in rec.get('deadlines', []):
        if dl.get('date'):
            add(dl['date'])
    for k in ('asof', 'review_opened'):
        if meta.get(k):
            add(meta[k])
    try:
        asof = parse_date(meta['asof'])[0] if meta.get('asof') else None
    except ValueError:
        asof = None
    for where, text, fact, _vis in authored(rec):
        if fact is not None or not _NARRATIVE.match(where):
            continue
        plain = strip_quotes(_no_placeholders(text))
        for raw, d, a, b in written_dates(plain):
            if d is None:
                R.error(f"{where}: writes {raw!r}, which is not a real date.")
                continue
            if d not in known:
                R.error(f"{where}: writes {raw!r}, but no fact, span, document or deadline in the record has that date. "
                        f"Correct the date, or add the fact it comes from.")
            if asof and d < asof:
                start = max([0] + [m.end() for m in re.finditer(r'[.!?]\s+(?=[A-Z“"])', plain[:a])])
                end_m = re.search(r'[.!?]\s+(?=[A-Z“"])', plain[b:])
                sentence = plain[start:b + (end_m.start() if end_m else len(plain))]
                fut = _FUTURE.search(sentence)
                if fut:
                    R.soft(f"{where}: says {fut.group(0)!r} about {raw}, a date before the record's as-of date ({fmt_date(meta['asof'])}). "
                           f"Say what happened, or change the as-of date.")


# ---------- money and authority ----------
# The ledger holds one row per transaction, each from a document. Totals are computed from the rows.
# An authority is bounded by two facts the claimant records. The tool places each row before, within or after
# those dates by date alone; whether a transaction was allowed is never the tool's to say.

SUM_KEYS = ('to', 'from', 'by', 'under', 'status', 'before', 'within', 'after')


def entry_value(e):
    return _dec(e['amount'])


def fmt_money(v):
    return f'${v:,.2f}'


def entry_status(e):
    return e.get('status') or 'documented'


def authority_window(a, facts_by):
    """(first day, end day or None) from the facts that bound the authority."""
    s = _fstart(facts_by[a['from']]) if a.get('from') in facts_by else None
    e = _fstart(facts_by[a['to']]) if a.get('to') in facts_by else None
    return s, e


def entry_position(e, a, facts_by):
    """'before', 'within', 'on the end date' or 'after' the facts that bound authority a, by date alone."""
    s, end = authority_window(a, facts_by)
    d = period(e['date'])[0]
    if s and d < s:
        return 'before'
    if end and d == end:
        return 'on the end date'
    if end and d > end:
        return 'after'
    return 'within'


def select_entries(ledger, args, authorities, facts_by):
    """The rows a {sum:KEY:VALUE:...} placeholder adds up. Keys: to, from, by, under, status, and before/within/after AUTHORITY."""
    rows = list(ledger)
    for k, v in zip(args[0::2], args[1::2]):
        if k in ('before', 'within', 'after'):
            a = authorities[v]
            rows = [e for e in rows if entry_position(e, a, facts_by) == k]
        elif k == 'status':
            rows = [e for e in rows if entry_status(e) == v]
        else:
            rows = [e for e in rows if e.get(k) == v]
    return rows


def _check_money(rec, R, ids, mode):
    meta = rec['meta']
    people, exhibits, facts_by, auth_by = ids['people'], ids['exhibits'], ids['facts'], ids['authorities']
    for aid, a in auth_by.items():
        who = f'authority {aid}'
        for k in ('holder', 'for'):
            if a.get(k) and a[k] not in people:
                R.error(f"{who}: '{k}' names {a[k]!r}, which is not a person in the record.")
        for k in ('from', 'to'):
            if a.get(k):
                if a[k] not in facts_by:
                    R.error(f"{who}: '{k}' names {a[k]!r}, which is not a fact. An authority starts and ends at facts, so each date has a source.")
                elif not fact_is_day(facts_by[a[k]]):
                    R.error(f"{who}: fact {a[k]} is only dated to the {eff_precision(facts_by[a[k]]['date'], facts_by[a[k]].get('date_precision'))}, so transactions cannot be placed before or after it.")
        if a.get('ex') and a['ex'] not in exhibits:
            R.error(f"{who}: ex names {a['ex']!r}, which is not an exhibit.")
        s, e = authority_window(a, facts_by)
        if s and e and e < s:
            R.error(f"{who}: the fact that ends it ({a['to']}) comes before the fact that starts it ({a['from']}).")
    for e in rec.get('ledger', []):
        who = f"ledger entry {e['id']}"
        _date_ok(R, who, 'date', e['date'], 'day')
        if e.get('by') and e['by'] not in people:
            R.error(f"{who}: 'by' names {e['by']!r}, which is not a person in the record.")
        if e.get('under'):
            if e['under'] not in auth_by:
                R.error(f"{who}: 'under' names {e['under']!r}, which is not an authority in the record.")
            elif e.get('by') and auth_by[e['under']]['holder'] != e['by']:
                R.warn(f"{who}: it is recorded as made under {e['under']}, but by {e['by']}, who is not that authority's holder. Check which the document shows.")
        val = entry_value(e)
        pool = [(s['ex'], exhibits[s['ex']].get('text')) for s in e['sources'] if s['ex'] in exhibits]
        for s in e['sources']:
            if s['ex'] not in exhibits:
                R.error(f"{who}: cites {s['ex']!r}, which is not an exhibit.")
            elif s.get('quote') and exhibits[s['ex']].get('text'):
                st, _det = verify_quote(s['quote'], exhibits[s['ex']]['text'])
                if st != 'ok':
                    R.error(f"{who}: the quote is not in {s['ex']} word for word: {s['quote'][:80]!r}.")
                else:
                    R.verified += 1
        texts = [t for _i, t in pool if t]
        if not texts:
            R.unverified.append(f"{who}: the amount {e['amount']} cannot be checked, because the document it cites has no text.")
        elif not any(val in figures_in(t) for t in texts):
            R.error(f"{who}: the amount {e['amount']} is not in the document(s) it cites ({', '.join(i for i, _t in pool)}). "
                    "Enter the amount exactly as the statement shows it, or cite the document that shows it.")
    st = meta.get('standing') or {}
    if st.get('rights_holder') and st['rights_holder'] not in people:
        R.error(f"the record's standing: rights_holder names {st['rights_holder']!r}, which is not a person in the record.")
    if (rec.get('ledger') or rec.get('authorities')) and not st.get('rights_holder'):
        R.warn("The record tracks money or authority but does not say whose claim it is. Add meta.standing (rights_holder, and how they agreed to this record) "
               "and ask a lawyer to confirm who that is.")
    if mode == 'outward' and meta.get('outward') is False:
        R.error("This record is marked outward: false, so it has no outward page. A record that accuses a named person stays off the outward page until a lawyer has read it. "
                "Change meta.outward only after that.")


# ---------- the record checks ----------

def check_record(rec, mode='record', strict=False, files_dir=None):
    """-> (normalized record or None, Result). mode is 'record' (inward pages) or 'outward' (the page that goes out)."""
    R = Result(strict)
    if not isinstance(rec, dict):
        R.error('The record file should hold one group of fields ({...}) with "meta" and "facts" in it. It holds something else.')
        return None, R
    rec = normalize(rec)
    try:
        issues, schema = [], load_schema()
        validate_schema(rec, schema, schema, (), issues)
        errs, extras = schema_messages(rec, issues)
        for e in errs:
            R.error(e)
        for x in extras:
            R.soft(x)
        if errs:
            return rec, R
        _semantic(rec, R, mode, files_dir)
    except BuildError as e:
        R.error(str(e))
    except Exception as e:  # never a traceback for a bad record
        if os.environ.get('BTR_DEBUG'):
            raise
        R.error(f'The checker hit a problem it did not expect ({type(e).__name__}: {e}). This is a bug in the tool, not a mistake in your record. '
                f'Run again with BTR_DEBUG=1 to see where.')
    return rec, R


def _ids(rec, R):
    seen = {}
    for coll, name in (('people', 'person'), ('exhibits', 'exhibit'), ('facts', 'fact'), ('issues', 'topic'), ('lanes', 'lane'), ('intervals', 'interval'),
                       ('authorities', 'authority'), ('ledger', 'ledger entry')):
        low = {}
        for x in rec.get(coll, []):
            i = x.get('id')
            if i is None:
                continue
            if i.casefold() in low:
                same = 'twice' if low[i.casefold()] == i else f'as {low[i.casefold()]!r} and {i!r}, which differ only by capitals, so they would share a file name'
                R.error(f'{name} id {i!r} is used {same}. Every {name} needs its own id.')
            low[i.casefold()] = i
        seen[coll] = {x['id']: x for x in rec.get(coll, []) if 'id' in x}
    return seen


def _date_ok(R, who, label, value, precision=None):
    try:
        parse_date(value)
    except ValueError:
        R.error(f"{who}: {label} {value!r} is not a real date. Write it as 2026-10-04 (2026-10 for a month, 2026 for a year).")
        return False
    if precision and (precision_of(value) is None or ['year', 'month', 'day'].index(precision) > ['year', 'month', 'day'].index(precision_of(value))):
        R.error(f"{who}: {label} {value!r} is only known to the {precision_of(value)}, but date_precision says {precision}. Make them agree.")
        return False
    return True


def _safe_path(R, who, field, v):
    if is_http(v):
        return
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', v) or v.startswith(('/', '\\', '~')) or '..' in re.split(r'[\\/]', v) or '\x00' in v:
        R.error(f"{who}: {field} {v!r} must be a path inside the files folder (no ..) or an http(s) address.")


def _semantic(rec, R, mode, files_dir):
    meta = rec['meta']
    ids = _ids(rec, R)
    people, exhibits, facts_by = ids['people'], ids['exhibits'], ids['facts']
    issues_by, lanes_by, intervals_by = ids['issues'], ids['lanes'], ids['intervals']
    facts = rec['facts']
    child_of = {}

    # dates in meta
    for k in ('asof', 'review_opened'):
        if k in meta:
            _date_ok(R, 'the record', f"meta '{k}'", meta[k], 'day')
    if ('review_opened' in meta) != ('asof' in meta) and 'review_opened' in meta:
        R.error("The record gives 'review_opened' but no 'asof'. 'Day N of the review' needs both dates (asof is the day the page is written).")
    if 'asof' in meta and 'review_opened' in meta and meta['asof'] < meta['review_opened']:
        R.error("The record's 'asof' is before 'review_opened'.")

    # exhibits
    for eid, e in exhibits.items():
        who = f'exhibit {eid}'
        if e.get('date'):
            if _date_ok(R, who, 'date', e['date'], e.get('date_precision')) and e.get('end') and _date_ok(R, who, 'end', e['end']):
                if period(e['end'])[1] < period(e['date'])[0]:
                    R.error(f"{who}: the end date {e['end']} is before its date {e['date']}.")
        elif e.get('end'):
            R.error(f"{who}: has an end date but no date.")
        for fld in ('file', 'thumb', 'link'):
            if e.get(fld):
                _safe_path(R, who, fld, e[fld])
        for fld in ('excerpt_of', 'fold_into'):
            if e.get(fld):
                if e[fld] not in exhibits:
                    R.error(f"{who}: {fld} names {e[fld]!r}, which is not an exhibit.")
                elif e[fld] == eid:
                    R.error(f"{who}: {fld} points at itself.")
                elif exhibits[e[fld]].get('excerpt_of') or exhibits[e[fld]].get('fold_into'):
                    R.error(f"{who}: {fld} names {e[fld]}, which is itself an excerpt or a folded duplicate. Point at the one that is kept.")
        if e.get('needs_clearance') and e.get('share') is True:
            R.error(f"{who}: marked as needing clearance from {e['needs_clearance']} but also share: true. Clear it first (remove needs_clearance), or leave it unshared.")
        for fld in ('title', 'caption'):
            if re.search(r'(?i)</?script|<iframe|javascript:', e.get(fld) or ''):
                R.error(f"{who}: {fld} contains what looks like page code. Remove it.")

    # facts
    for f in facts:
        who = f"fact {f['id']}"
        ok = _date_ok(R, who, 'date', f['date'], f.get('date_precision'))
        if ok and f.get('end') and _date_ok(R, who, 'end', f['end']):
            if period(f['end'])[1] < period(f['date'])[0]:
                R.error(f"{who}: the end {f['end']} is before the date {f['date']}.")
        if f['status'] == 'documented' and not f.get('sources'):
            R.error(f"{who} is marked documented but names no document. Add the document it shows up in under sources, or change the status to account.")
        apart, apart_range = [], []
        for i, s in enumerate(f.get('sources', [])):
            if s['ex'] not in exhibits:
                R.error(f"{who}: source {i + 1} names {s['ex']!r}, which is not an exhibit in this record.")
            elif ok:
                e = exhibits[s['ex']]
                if e.get('date') and _date_ok(R, f"exhibit {s['ex']}", 'date', e['date']) and not s.get('later_document'):
                    lo, hi = period(e['date'], e.get('date_precision'))[0], period(e.get('end') or e['date'], None if e.get('end') else e.get('date_precision'))[1]
                    flo, fhi = period(f['date'], f.get('date_precision'))
                    if fhi < lo or flo > hi:
                        (apart_range if e.get('end') else apart).append(f"{s['ex']} (dated {e['date']}{' to ' + e['end'] if e.get('end') else ''})")
        for bad, hard in ((apart_range, True), (apart, False)):
            if bad:
                (R.error if hard else R.soft)(
                    f"{who} ({f['date']}) cites {', '.join(bad)}. A document dated on another day cannot show what happened on this date. "
                    f"Cite the right document, give the exhibit a date range, or set later_document: true on the source once you have checked it.")
        for pid in f.get('people', []):
            if pid not in people:
                R.error(f"{who}: names person {pid!r}, who is not in the cast (people).")
        for iid in f.get('issues', []):
            if iid not in issues_by:
                R.error(f"{who}: names topic {iid!r}, which is not in the record's topics (issues).")
        if f.get('lane') and f['lane'] not in lanes_by:
            R.error(f"{who}: lane {f['lane']!r} is not one of the record's lanes.")
        for fld in ('excerpt_of', 'fold_into'):
            if f.get(fld):
                if f[fld] not in facts_by:
                    R.error(f"{who}: {fld} names {f[fld]!r}, which is not a fact.")
                elif f[fld] == f['id']:
                    R.error(f"{who}: {fld} points at itself.")
                else:
                    child_of[f['id']] = f[fld]
        if f.get('grade') == 'B' and not f.get('tier'):
            R.soft(f"{who}: grade B needs a tier (B1 or B2).")
    for cid, pid in child_of.items():
        if pid in child_of:
            R.error(f"fact {cid}: points at {pid}, which is itself an excerpt or a folded duplicate. Point at the one that is kept.")

    # exhibit authors: one note per exhibit, naming the facts that lean on it
    no_author = defaultdict(list)
    for f in facts:
        if f['status'] == 'documented':
            for s in f.get('sources', []):
                e = exhibits.get(s['ex'])
                if e is not None and not e.get('author') and f['id'] not in no_author[s['ex']]:
                    no_author[s['ex']].append(f['id'])
    for eid, fs in no_author.items():
        R.soft(f"exhibit {eid} has no author, so the page cannot say whose document supports fact {', '.join(fs[:3])}" + (f' and {len(fs) - 3} more' if len(fs) > 3 else '') +
               '. Set author to claimant, other_side or third_party.')

    # cast, topics, lanes, beats, spans, intervals
    for b in rec.get('beats', []):
        who = f"section {b['title']!r}"
        a_ok, z_ok = _date_ok(R, who, 'from', b['from']), _date_ok(R, who, 'to', b['to'])
        if a_ok and z_ok:
            if period(b['to'])[1] < period(b['from'])[0]:
                R.error(f"{who}: 'to' is before 'from'.")
            elif not any(_fstart(f) and period(b['from'])[0] <= _fstart(f) <= period(b['to'])[1] for f in facts):
                R.warn(f"{who} covers {b['from']} to {b['to']}, where the record has no facts.")
        if re.search(r'\b(?:19|20)\d{2}\b|\b(?:January|February|March|April|June|July|August|September|October|November|December)\b', b['title']):
            R.error(f"{who}: the title types dates. Put the dates in 'from' and 'to'; the page prints the date label itself, so it can never disagree with them.")
    for s in rec.get('spans', []):
        who = f"span {s['label']!r}"
        if _date_ok(R, who, 'start', s['start']) and _date_ok(R, who, 'end', s['end']) and s['end'] < s['start']:
            R.error(f"{who}: the end is before the start.")
        if isinstance(s.get('lanes'), list):
            for l in s['lanes']:
                if l not in lanes_by:
                    R.error(f"{who}: names lane {l!r}, which is not one of the record's lanes.")
    for it in rec.get('intervals', []):
        who = f"interval {it['label']!r}"
        pair = []
        for k in ('a', 'b'):
            if it[k] not in facts_by:
                R.error(f"{who}: '{k}' names {it[k]!r}, which is not a fact.")
            else:
                pair.append(facts_by[it[k]])
        if len(pair) == 2:
            for f in pair:
                if not fact_is_day(f):
                    R.error(f"{who}: fact {f['id']} is only dated to the {eff_precision(f['date'], f.get('date_precision'))}, so the number of days between the two cannot be computed.")
            if all(fact_is_day(f) and _fstart(f) for f in pair) and _fstart(pair[1]) < _fstart(pair[0]):
                R.error(f"{who}: fact {pair[1]['id']} comes before fact {pair[0]['id']}. Swap 'a' and 'b'.")

    # deadlines: entered by the claimant, never computed, never confirmed here
    for d in rec.get('deadlines', []):
        who = f"deadline {d['label']!r}"
        if 'computed' in d:
            R.error(f"{who}: deadlines must be entered by the claimant with the place they are written; the tool never computes one. Remove 'computed' and quote the document's own words.")
        if not d.get('date') and not d.get('wording'):
            R.error(f"{who}: give the date the document states, or the document's own words in 'wording'. The tool does not work a date out for you.")
        if d.get('date'):
            _date_ok(R, who, 'date', d['date'], 'day')
        if d.get('ex'):
            if d['ex'] not in exhibits:
                R.error(f"{who}: ex names {d['ex']!r}, which is not an exhibit.")
            elif d.get('wording'):
                text = exhibits[d['ex']].get('text')
                if text:
                    st, det = verify_quote(d['wording'], text)
                    if st != 'ok':
                        R.error(f"{who}: the wording is not in {d['ex']} word for word" + (f" (the document has {det!r} just outside it)" if st == 'negation' else '') + f": {d['wording'][:80]!r}.")
                    else:
                        R.verified += 1
                else:
                    R.unverified.append(f"{who}: the wording cannot be checked, because {d['ex']} has no text.")
            if d.get('date') and exhibits.get(d['ex'], {}).get('date') and precision_of(exhibits[d['ex']]['date']) == 'day' and not d.get('wording'):
                gap = (dt.date.fromisoformat(d['date']) - dt.date.fromisoformat(exhibits[d['ex']]['date'])).days
                if gap in DEADLINE_WINDOWS:
                    R.warn(f"{who}: the date is exactly {gap} days after {d['ex']}. If the document gives only a period and the date was worked out, enter the document's own words in 'wording' instead; the tool does not compute deadlines.")

    # money and authority
    _check_money(rec, R, ids, mode)

    # wording and numbers in everything the claimant or assistant wrote
    banned = meta.get('banned') or []
    ctx_corpus = [(eid, e['text']) for eid, e in exhibits.items() if e.get('text')]
    for where, text, fact, _vis in authored(rec):
        if re.search(r'(?i)</?script|<iframe|javascript:|onerror\s*=', text):
            R.error(f"{where}: contains what looks like page code. Remove it; an email header with <...> is fine, but not <script>.")
        if unbalanced_quotes(text):
            R.warn(f"{where}: has a quotation mark with no partner, so the words after it are checked as the claimant's own words.")
        for kind, snip, why in lint_authored(text, banned):
            R.error(f"{where}: wording the tool does not use ({kind}: {snip!r}, {why}). This page states what documents show and gives no legal conclusion or argument. "
                    f"Rephrase it, or put the other side's own words in quotation marks.")
        for m in STATUTE.finditer(strip_quotes(text)):
            R.warn(f"{where}: cites a statute ({m.group(0)!r}). Naming the law with its source is information; check that the sentence does not apply it to the facts.")
        cited_text = ' '.join(norm_words(exhibits[s['ex']].get('text') or '') for s in (fact or {}).get('sources', []) if s['ex'] in exhibits)
        for phrase in typed_counts(text):
            if fact is not None and cited_text and norm_words(phrase) in cited_text:
                continue  # a figure the cited document itself states
            R.error(f"{where}: {phrase!r} is a number typed into the text. {UNIT_FIX}")
        if not _OWN_ENTRY.match(where):
            _check_dollars(R, where, text, fact, exhibits, ctx_corpus)
        for raw, kind, args in placeholders_in(text):
            _check_placeholder(R, where, raw, kind, args, facts_by, intervals_by, mode, exhibits, rec.get('ledger', []), ids['authorities'])
        for q in extract_quotes(text):
            _check_prose_quote(R, where, q, fact, exhibits, ctx_corpus)

    # sources' own quotes
    for f in facts:
        for s in f.get('sources', []):
            q, e = s.get('quote'), exhibits.get(s['ex'])
            if not q or e is None:
                continue
            if not e.get('text'):
                R.unverified.append(f"fact {f['id']}: the quote from {s['ex']} cannot be checked, because {s['ex']} has no text.")
                continue
            st, det = verify_quote(q, e['text'])
            if st == 'ok':
                R.verified += 1
                clip = clipped_before(q, e['text'])
                if clip:
                    R.soft(f"fact {f['id']}: the quote from {s['ex']} stops right before {clip!r}, so the sentence in the document goes on with a qualifier the quote leaves out: "
                           f"{q[:60]!r}. Quote the whole sentence, or end the quote with … to show it is partial.")
            elif st == 'negation':
                R.error(f"fact {f['id']}: the quote from {s['ex']} cuts off a {det!r} that sits right next to it in the document: {q[:80]!r}. Quote the whole phrase.")
            else:
                R.error(f"fact {f['id']}: the quote is not in {s['ex']} word for word: {q[:80]!r}.")
    if R.strict:
        for u in R.unverified:
            R.error(u + ' Add the exhibit text, or remove the quotation marks.')

    # a documented fact and the words of the documents it cites
    for f in facts:
        if f['status'] != 'documented' or not f.get('sources'):
            continue
        cited = [(s, exhibits.get(s['ex'])) for s in f['sources']]
        if any(e is None or not e.get('text') for _s, e in cited):
            continue  # a document with no text (or no such exhibit, reported above) cannot be compared
        if not shows_it(f, cited):
            sample = ', '.join(shown for _k, _key, shown in key_tokens(f['text'])[:4])
            R.error(f"fact {f['id']} is marked documented but its cited document does not appear to show it: none of its key words ({sample}) are in "
                    f"{', '.join(sorted({s['ex'] for s, _e in cited}))}. Cite the document that shows it, reword the fact to what the document says, "
                    f"change the status to account, or add source.loc and source.quote with the document's own words.")
    _check_dates_in_prose(R, rec, meta, facts, exhibits)

    if mode == 'outward':
        _outward(rec, R, exhibits, facts, files_dir)


def _check_dollars(R, where, text, fact, exhibits, corpus):
    figs = dollar_figures(text)
    if not figs:
        return
    if fact is not None:
        pool = [(s['ex'], exhibits[s['ex']]['text']) for s in fact.get('sources', []) if s['ex'] in exhibits and exhibits[s['ex']].get('text')]
        named = ', '.join(sorted({s['ex'] for s in fact.get('sources', [])}))
    else:
        pool, named = corpus, ''
    for raw, val in figs:
        if not pool:
            if fact is not None and fact['status'] != 'documented':
                continue  # an account says whose words they are
            R.soft(f"{where}: the figure {raw} cannot be checked, because " + ('the document(s) it cites have no text.' if fact is not None else 'no document in the record has text.') +
                   ' Add the exhibit text, or leave the figure out.')
        elif not any(val in figures_in(t) for _i, t in pool):
            R.error(f"{where}: the figure {raw} is not in " + (f'the document(s) it cites ({named})' if fact is not None else 'any document in the record') +
                    ". Quote the amount from the document, cite the document that states it, or leave the figure out. "
                    "If the document is a picture, type the words you can read into the exhibit's text.")


def _check_placeholder(R, where, raw, kind, args, facts_by, intervals_by, mode, exhibits=None, ledger=(), authorities=None):
    exhibits = exhibits or {}
    authorities = authorities or {}
    if kind == 'sum':
        if mode == 'outward':
            R.error(f"{where}: {raw} adds up ledger rows, and the ledger is not on the outward page. Leave totals to the inward record.")
            return
        if len(args) % 2:
            R.error(f"{where}: {raw}: filters come in pairs, like {{sum:to:P3}} or {{sum:after:A1}}.")
            return
        for k, v in zip(args[0::2], args[1::2]):
            if k not in SUM_KEYS:
                R.error(f"{where}: {raw}: {k!r} is not a filter this tool knows. Use " + ', '.join(SUM_KEYS) + '.')
                return
            if k in ('before', 'within', 'after') and v not in authorities:
                R.error(f"{where}: {raw}: {v!r} is not an authority in the record.")
                return
            if k == 'under' and v not in authorities:
                R.error(f"{where}: {raw}: {v!r} is not an authority in the record.")
                return
        if not ledger:
            R.error(f"{where}: {raw} adds up the ledger, but the record has no ledger rows.")
        elif not select_entries(ledger, args, authorities, facts_by):
            R.error(f"{where}: {raw} selects no ledger rows. Check the filter.")
        return
    if kind == 'miles':
        if len(args) != 3:
            R.error(f"{where}: {raw} needs an exhibit id and two odometer readings, like {{miles:E12:48,210:48,222}}.")
            return
        ex_id, a, b = args
        e = exhibits.get(ex_id)
        if e is None:
            R.error(f"{where}: {raw} names {ex_id!r}, which is not an exhibit.")
            return
        ra, rb = reading(a), reading(b)
        if ra is None or rb is None:
            R.error(f"{where}: {raw}: the two odometer readings must be whole numbers, like 48,210.")
        elif rb <= ra:
            R.error(f"{where}: {raw}: the second reading ({b}) is not larger than the first ({a}). Write the earlier reading first.")
        elif not e.get('text'):
            R.error(f"{where}: {raw} cannot be checked, because exhibit {ex_id} has no text to find the readings in. Add the document's text to the exhibit.")
        else:
            have = whole_numbers_in(e['text'])
            gone = [x for x, v in ((a, ra), (b, rb)) if v not in have]
            if gone:
                R.error(f"{where}: {raw}: " + ' and '.join(f'the reading {x} is not in exhibit {ex_id}' for x in gone) + '. Both odometer readings must be numbers in that document.')
            elif mode == 'outward' and e.get('share') is not True:
                R.soft(f"{where}: {raw} gets its readings from exhibit {ex_id}, which is not shared, so a reader cannot check the miles against the document.")
    elif kind == 'days':
        if len(args) != 2:
            R.error(f"{where}: {raw} needs two fact ids, like {{days:F1:F2}}.")
            return
        for a in args:
            if a not in facts_by:
                R.error(f"{where}: {raw} names {a!r}, which is not a fact.")
            elif not fact_is_day(facts_by[a]):
                R.error(f"{where}: {raw} uses fact {a}, which is only dated to the {eff_precision(facts_by[a]['date'], facts_by[a].get('date_precision'))}, so days cannot be computed.")
            elif mode == 'outward' and facts_by[a].get('outward') is not True:
                R.error(f"{where}: {raw} uses fact {a}, which is not released to the outward page, so its date would leak through the number.")
        if all(a in facts_by and fact_is_day(facts_by[a]) and _fstart(facts_by[a]) for a in args) and _fstart(facts_by[args[1]]) < _fstart(facts_by[args[0]]):
            R.error(f"{where}: {raw}: fact {args[1]} comes before fact {args[0]}. Swap them.")
    elif kind == 'count':
        if len(args) != 1 or args[0] not in COUNT_NAMES:
            R.error(f"{where}: {raw} is not a count this tool knows. Use one of: " + ', '.join('{count:%s}' % n for n in COUNT_NAMES) + '.')
    elif kind == 'interval':
        if len(args) != 1 or args[0] not in intervals_by:
            R.error(f"{where}: {raw} names an interval id that is not in the record's intervals.")
    else:
        R.error(f"{where}: {raw} is not a placeholder this tool knows (days, count, interval, miles or sum).")


def _check_prose_quote(R, where, q, fact, exhibits, corpus):
    pool = [(s['ex'], exhibits[s['ex']].get('text')) for s in fact.get('sources', []) if s['ex'] in exhibits] if fact is not None else corpus
    pool = [(i, t) for i, t in pool if t]
    if not pool:
        R.unverified.append(f"{where}: the quoted words {q[:60]!r} cannot be checked" + (', because the documents it cites have no text.' if fact is not None and fact.get('sources') else ', because no document is attached to check them against.'))
        return
    neg, ok_in = None, []
    for i, t in pool:
        st, det = verify_quote(q, t)
        if st == 'ok':
            ok_in.append((i, t))
        else:
            neg = neg or (det if st == 'negation' else None)
    if ok_in:
        R.verified += 1
        clips = [clipped_before(q, t) for _i, t in ok_in]
        if all(clips):
            R.soft(f"{where}: the quoted words {q[:60]!r} stop right before {clips[0]!r} in {ok_in[0][0]}, so the sentence in the document goes on with a qualifier the quote leaves out. "
                   f"Quote the whole sentence, or end the quote with … to show it is partial.")
        return
    near = [i for i, t in corpus if verify_quote(q, t)[0] == 'ok'] if fact is not None else []
    if neg:
        R.error(f"{where}: the quoted words {q[:80]!r} cut off a {neg!r} that sits right next to them in the document. Quote the whole phrase.")
    else:
        R.error(f"{where}: the quoted words {q[:80]!r} are not in " + ('the document(s) it cites' if fact is not None else 'any document in the record') + ' word for word.' +
                (f" They are in {', '.join(near)}; cite that exhibit as a source." if near else ''))


def _outward(rec, R, exhibits, facts, files_dir):
    meta = rec['meta']
    if not any(f.get('outward') is True and not f.get('fold_into') for f in facts):
        R.error("No fact has outward: true, so the outward page would be empty. Nothing is released unless you set outward: true on it.")
    banned = meta.get('banned') or []
    held = held_phrases(rec)
    private_hosts()  # a private-hosts file that cannot be read is reported even when no link is shared
    for eid, e in exhibits.items():
        if e.get('share') is not True:
            continue
        who = f'exhibit {eid}'
        for fld in ('link', 'thumb', 'file'):
            v = e.get(fld)
            if v and is_http(v):
                h = host_of(v)
                if is_private_host(h):
                    R.error(f"{who}: {fld} points to {h}, a private site. The outward page may not link to it. Remove the {fld}, or share a copy of the document itself.")
                elif fld == 'thumb':
                    R.warn(f"{who}: the thumbnail loads from {h}, so that site learns who opens the page. Use a local file.")
        if e.get('file') and not is_http(e['file']):
            if not files_dir:
                R.error(f"{who} is shared, but no files folder was given (use --files-dir), so its file cannot be copied.")
            elif not os.path.isfile(os.path.join(files_dir, e['file'])):
                R.error(f"{who} is shared, but its file {e['file']!r} is not in the files folder {files_dir!r}.")
        if e.get('thumb') and not is_http(e['thumb']) and files_dir and not os.path.isfile(os.path.join(files_dir, e['thumb'])):
            R.error(f"{who}: the thumbnail {e['thumb']!r} is not in the files folder {files_dir!r}.")
        if e.get('feature'):
            if not e.get('caption'):
                R.soft(f"{who} is featured but has no public caption. Write a caption in your own words; the page shows the caption, not the file name.")
            if not e.get('thumb'):
                R.warn(f"{who} is featured but has no thumbnail, so it will not appear in the media strip.")
            if is_still(e, exhibits):
                # a picture taken from a recording shows the recording's grade only if the owner has confirmed it; a still whose recording has no grade shows none
                src = still_of(e, exhibits)
                ids = {eid} | set(still_chain(e, exhibits))
                unconfirmed = [f for f in facts if f.get('grade') and f.get('reviewed_by') != 'owner' and any(s['ex'] in ids for s in f.get('sources', []))]
                if unconfirmed:
                    R.soft(f"{who} is a featured still frame" + (f' of recording {src}' if src else '') + f", but fact {unconfirmed[0]['id']} gives it grade {unconfirmed[0]['grade']} and the owner has not confirmed that grade "
                           f"(reviewed_by is not 'owner'). Confirm the grade after watching the recording, or take the still off the featured list.")
            elif is_recording(e):
                citing = [f for f in facts if any(s['ex'] == eid for s in f.get('sources', []))]
                if not any(f.get('grade') == 'A' and f.get('reviewed_by') == 'owner' for f in citing):
                    R.soft(f"{who} is a featured recording, but no fact citing it carries grade A set by the owner (reviewed_by: owner). A grade is a proposal until the owner has watched it.")
    # words that must never appear in anything going out
    for w, t, _f, vis in authored(rec):
        if not vis:
            continue
        for m in marker_hits(t):
            R.error(f"{w}: contains '{m}', which marks material meant for counsel. It cannot go on the outward page.")
        for p in phrase_hits(t, held):
            R.error(f"{w}: contains a phrase this case holds back ({p!r}).")


def format_failure(prefix, R):
    lines = [f'{prefix} BUILD FAILED: {len(R.errors)} problem{"" if len(R.errors) == 1 else "s"} to fix, and nothing was written.']
    lines += [f' - {e}' for e in R.errors]
    return '\n'.join(lines)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('record')
    ap.add_argument('--outward', action='store_true', help='also run the checks for the outward page')
    ap.add_argument('--strict', action='store_true', help='unverified quotes, unknown fields and the other pre-send checks become errors')
    ap.add_argument('--files-dir')
    a = ap.parse_args(argv)
    rec, errs = load_record(a.record)
    if errs:
        print('\n'.join(errs))
        return 1
    _norm, R = check_record(rec, 'outward' if a.outward else 'record', a.strict, a.files_dir)
    for w in R.warnings:
        print(f'note: {w}')
    if not R.ok:
        print(format_failure('CHECK', R))
        return 1
    print(f'ok: record checks passed. {R.verified} quotes verified, {len(R.unverified)} could not be checked; {len(R.warnings)} notes.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
