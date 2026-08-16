# Exhibit numbering scheme

Five classes, letters A–E. Numbers are assigned deterministically by code —
chronological within class, computed from the bundle — and the SAME code runs in
the site build and the PDF build, so the two can never disagree. Never hand-assign.

| Class | Contents |
|-------|----------|
| A | The manufacturer's own records: repair orders, TSBs, recall filings, dealer communications, denials, purchase paperwork, diagnostic logs |
| B | Correspondence: support-case transcripts/chats, notices, demand letters, voicemails |
| C | Owner media evidence — keep your catalogue numbers (Ex. C-<catalogue #>) so exhibit and catalogue IDs stay unified |
| D | Phone records: carrier extract D-1, then screenshots, then the workbook |
| E | Third-party records (arbitration bodies, listing-app rejections, etc.) |

Reference implementation (adapt the classifier regexes to your document titles):

```python
import re

def build_map(bundle):
    tl = sorted(bundle["timeline"], key=lambda t: (t["date"], t.get("title") or ""))
    amap, counts = {}, {"A": 0, "B": 0, "E": 0}
    for t in tl:
        blob = (t.get("title") or "") + " " + (t.get("typeLabel") or "")
        if re.search(r"arbitration|BBB", blob, re.I):
            cls = "E"
        elif re.search(r"chat|case opened|Notice|Demand|statutory|transcript", blob, re.I):
            cls = "B"
        else:
            cls = "A"
        counts[cls] += 1
        key = t.get("fileId") or ("TL::" + t["date"] + "::" + (t.get("title") or ""))
        amap[key] = f"{cls}-{counts[cls]}"
    return amap, counts
```

Documents that live outside the bundle timeline (e.g. an adverse position paper you
host, a voicemail) get fixed labels appended after the computed counts — also in
code, so a rebuild can't shift them.

Every exhibit number must appear identically in: the PDF's chronological record,
the PDF's exhibit index appendix, the site's grid captions, the site's modal links,
and any email that cites an exhibit.
