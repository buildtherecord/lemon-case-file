# Evidence triage tools

Small, offline tools for the triage step (`prompts/01b-evidence-triage.md`,
`METHOD.md` section 2a). Python 3 standard library plus `ffmpeg`/`ffprobe` for the
video tools. Nothing here uploads anything or calls a network; your evidence stays on
your computer.

| Tool | What it does |
|------|--------------|
| `proxy_clips.py` | Small review copies of videos (720p, stereo AAC, louder). Originals untouched. |
| `contact_sheets.py` | Dense frame grids so an assistant can see what is visible. Shows no motion and no sound. |
| `dupcheck.py` | Finds the same footage exported or uploaded twice, by comparing frames, not captions. |
| `make_watchlist.py` | Builds the owner's watch list: one offline page, one question per item, answers saved. |
| `apply_answers.py` | Applies the owner's answers to the grades file, enforces the rules, prints the counts. |
| `quotecheck.py` | Fails if a rewritten caption lost a direct quote from the original. |
| `example/make_example.py` | Makes a fictional example set to try all of the above. |

## The loop

```
inventory -> grades.csv (assistant proposes)
          -> contact_sheets.py            assistant looks at what is visible
          -> dupcheck.py                  assistant lists same-footage pairs
          -> review-queue.csv             only what stills could not settle
          -> make_watchlist.py            owner watches, answers
          -> answers.csv (downloaded)
          -> apply_answers.py             grades.csv updated, counts printed
          -> quotecheck.py                captions kept their quotes
          -> rebuild the site/PDF from grades.csv; show the owner what changed
          -> clear answered items; add whatever the answers raised
```

The watch list is a living queue. Items leave it when their answer is applied; new
questions join it as they arise (a clip that looked like nothing in stills turned out to
be the owner's best evidence, so the other clips like it get queued).

## Files

`grades.csv`, one row per piece of evidence:

`id, date, time, kind, caption, grade, tier, fold_into, excerpt_of, reviewed_by, owner_note, public_caption`

- `grade` is `A`, `B` or `C`; a `B` carries `tier` `B1` or `B2`. Definitions are in `METHOD.md` 2a.
- `fold_into` names the item this one duplicates. A folded item is hidden and not counted;
  it is never deleted.
- `excerpt_of` names the parent of an excerpt. An excerpt is shown, labelled, and never counted.
- `reviewed_by` is `assistant` until the owner has watched it, then `owner`.
- `public_caption` is the owner's own wording, lightly edited. `quotecheck.py` guards it.

`review-queue.csv`: `id, title, when, current_grade, proposed_grade, watch_for, frames_note,
media, original, flags`. `answers.csv` (exported by the watch list): `id, grade, sec, note`.

## Try it

```
python3 tools/triage/example/make_example.py /tmp/triage-demo
cd /tmp/triage-demo
python3 /path/to/tools/triage/proxy_clips.py c01.mp4 c02.mp4 c03.mp4 c04.mp4 --out proxies
python3 /path/to/tools/triage/dupcheck.py proxies          # flags c01 / c02 as the same footage
python3 /path/to/tools/triage/make_watchlist.py review-queue.csv --out watchlist.html
```

Open `watchlist.html`, answer, download `answers.csv`, then run
`apply_answers.py grades.csv answers.csv`.

## Privacy

Case material (plates, faces, names, dates of birth, account numbers) is flagged at triage and
kept out of anything public. This folder holds tools and a fictional example only. Never commit
a real grades file, queue, answer set or clip.
