#!/usr/bin/env python3
"""Validate jurisdictions/*.md front-matter and structure. Stdlib only.

Usage: python3 tools/validate_jurisdictions.py
Front-matter is a flat block between --- lines: `key: value`, one per line.
Required keys: jurisdiction, domain, last_verified (YYYY-MM-DD), verified_against.
Body must contain a "## Sources" section with at least one http(s) link.
Warns (does not fail) when last_verified is older than 12 months.
"""
import datetime, glob, os, re, sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REQUIRED = ["jurisdiction", "domain", "last_verified", "verified_against"]
fails, warns = [], []

for path in sorted(glob.glob("jurisdictions/*.md")):
    name = os.path.basename(path)
    if name in ("README.md", "TEMPLATE.md"):
        continue
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        fails.append(f"{name}: missing front-matter block (--- ... ---)")
        continue
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    for k in REQUIRED:
        if not fm.get(k):
            fails.append(f"{name}: front-matter missing '{k}'")
    lv = fm.get("last_verified", "")
    try:
        d = datetime.date.fromisoformat(lv)
        if (datetime.date.today() - d).days > 365:
            warns.append(f"{name}: last_verified {lv} is over 12 months old — treat as historical")
    except ValueError:
        fails.append(f"{name}: last_verified '{lv}' is not YYYY-MM-DD")
    if not re.search(r"##\s*Sources", text):
        fails.append(f"{name}: missing '## Sources' section")
    elif not re.search(r"https?://", text.split("Sources", 1)[1]):
        fails.append(f"{name}: Sources section has no links")
    if "re-verif" not in text.lower():
        warns.append(f"{name}: consider keeping the re-verify warning near any deadline content")

for w in warns:
    print("WARN:", w)
if fails:
    for f in fails:
        print("FAIL:", f)
    sys.exit(1)
print("jurisdictions: OK" + (f" ({len(warns)} warnings)" if warns else ""))
