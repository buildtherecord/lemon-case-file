#!/usr/bin/env python3
"""Apply the owner's watch-list answers to the grades file and show exactly what changed.

  python3 apply_answers.py grades.csv answers.csv [-o grades.new.csv | --in-place]

grades.csv  one row per piece of evidence. Columns used: id, grade (A|B|C), tier (B1|B2 when
            grade is B), fold_into, excerpt_of, reviewed_by, owner_note. Other columns are kept.
answers.csv exported from the watch list: id, grade, sec, note. grade is A, B1, B2, C,
            FOLD:<id> (same footage as another item), or UNSURE / blank (change nothing).

Rules enforced (the script exits non-zero if any fails, so a bad grades file cannot ship):
  - every grade is A, B or C; every B has a tier B1 or B2; no tier on anything else
  - a folded item points at a real item that is not itself folded
  - an excerpt points at a real parent
  - counts are printed with folded items and excerpts left out, because a piece of evidence
    is counted once and an excerpt is never separate evidence
Nothing is deleted: folded items stay in the file and in your folders.
"""
import argparse, csv, sys

NEED = ['id', 'grade', 'tier', 'fold_into', 'excerpt_of', 'reviewed_by', 'owner_note']
CHOICE = {'A': ('A', ''), 'B1': ('B', 'B1'), 'B2': ('B', 'B2'), 'C': ('C', '')}


def load(path):
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])


def validate(rows):
    ids = {r['id'] for r in rows}
    folded = {r['id'] for r in rows if r['fold_into']}
    errs = []
    for r in rows:
        i = r['id']
        if r['grade'] not in ('A', 'B', 'C'):
            errs.append(f'{i}: grade must be A, B or C (got "{r["grade"]}")')
        if r['grade'] == 'B' and r['tier'] not in ('B1', 'B2'):
            errs.append(f'{i}: a B needs a tier, B1 or B2')
        if r['grade'] != 'B' and r['tier']:
            errs.append(f'{i}: only a B carries a tier')
        t = r['fold_into']
        if t:
            if t == i: errs.append(f'{i}: cannot fold into itself')
            elif t not in ids: errs.append(f'{i}: folds into unknown item {t}')
            elif t in folded: errs.append(f'{i}: folds into {t}, which is itself folded')
        p = r['excerpt_of']
        if p and p not in ids:
            errs.append(f'{i}: excerpt of unknown item {p}')
    return errs


def counts(rows):
    live = [r for r in rows if not r['fold_into'] and not r['excerpt_of']]
    key = lambda r: r['tier'] if r['grade'] == 'B' else r['grade']
    c = {k: sum(1 for r in live if key(r) == k) for k in ('A', 'B1', 'B2', 'C')}
    return c, len(live), sum(1 for r in rows if r['fold_into']), sum(1 for r in rows if r['excerpt_of'])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('grades')
    ap.add_argument('answers')
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('--in-place', action='store_true')
    a = ap.parse_args()
    rows, fields = load(a.grades)
    for col in NEED:
        if col not in fields:
            fields.append(col)
            for r in rows: r[col] = ''
    by = {r['id']: r for r in rows}
    answers, _ = load(a.answers)
    bad = [x['id'] for x in answers if x['id'] not in by]
    if bad:
        sys.exit('Answers for unknown ids (nothing written): ' + ', '.join(bad))
    before = {r['id']: (r['grade'], r['tier'], r['fold_into']) for r in rows}
    for x in answers:
        g = (x.get('grade') or '').strip()
        if g in ('', 'UNSURE'):
            continue
        r = by[x['id']]
        if g.startswith('FOLD:'):
            r['fold_into'] = g.split(':', 1)[1].strip()
        elif g in CHOICE:
            r['grade'], r['tier'] = CHOICE[g]
            r['fold_into'] = ''
        else:
            sys.exit(f'{x["id"]}: unknown answer "{g}" (use A, B1, B2, C, FOLD:<id> or UNSURE)')
        note = (x.get('note') or '').strip()
        if (x.get('sec') or '').strip(): note = (note + f' (at {x["sec"].strip()}s)').strip()
        if note: r['owner_note'] = note
        r['reviewed_by'] = 'owner'
    errs = validate(rows)
    if errs:
        print('NOT WRITTEN. Fix these:')
        for e in errs: print('  -', e)
        sys.exit(1)
    changed = 0
    for r in rows:
        now = (r['grade'], r['tier'], r['fold_into'])
        if now != before[r['id']]:
            changed += 1
            fmt = lambda t: (t[1] or t[0]) + (f' folded into {t[2]}' if t[2] else '')
            print(f'  {r["id"]}: {fmt(before[r["id"]])} -> {fmt(now)}')
    c, live, nf, nx = counts(rows)
    print(f'{changed} changed. Counted: {live} items  A {c["A"]} / B1 {c["B1"]} / B2 {c["B2"]} / C {c["C"]}'
          f'   (left out: {nf} folded, {nx} excerpts)')
    out = a.grades if a.in_place else (a.out or a.grades.rsplit('.', 1)[0] + '.new.csv')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print('wrote', out)


if __name__ == '__main__':
    main()
