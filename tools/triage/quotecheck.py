#!/usr/bin/env python3
"""Check that a rewritten caption kept every direct quote from the original.

  python3 quotecheck.py grades.csv [--original caption] [--edited public_caption]

For each row with an edited caption, every quoted phrase in the original ("...", curly
quotes, or single-quoted words) must still appear in the edit. Quotes are evidence:
a caption that drops "hurts the fingers" has silently thrown away the owner's words.
Exits non-zero if any quote was lost.
"""
import argparse, csv, re, sys


def norm(s):
    s = s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    return re.sub(r'\s+', ' ', s).strip().lower().rstrip('.,;')


def quotes(text):
    out = [m.group(1) for m in re.finditer('“([^”]+)”', text)]
    out += [m.group(1) for m in re.finditer(r"(?<![A-Za-z])'([^']{3,}?)'(?![A-Za-z])", text)]
    out += [m.group(1) for m in re.finditer(r'"([^"]{3,})"', text)]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('grades')
    ap.add_argument('--original', default='caption')
    ap.add_argument('--edited', default='public_caption')
    a = ap.parse_args()
    lost = 0
    with open(a.grades, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            edited = (r.get(a.edited) or '').strip()
            if not edited:
                continue
            for q in quotes(r.get(a.original) or ''):
                if norm(q) not in norm(edited):
                    lost += 1
                    print(f'{r.get("id", "?")}: lost the quote "{q}"')
    print('Quotes all kept.' if not lost else f'{lost} quote(s) lost. Put them back before publishing.')
    sys.exit(1 if lost else 0)


if __name__ == '__main__':
    main()
