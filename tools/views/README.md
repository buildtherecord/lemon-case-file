# Record views: one record, published two ways

One person's dispute becomes **one record file**. These tools turn it into two sets of pages:

| | Inward | Outward |
|---|---|---|
| What it is | The full linked record, for you and your attorney | The page you could hand to the other side, a reviewer or a journalist |
| Command | `build_views.py` | `build_home.py` |
| What is on it | Every fact, document, person and topic, linked both ways; deadlines you entered; gaps | Only what you released, with private details removed. States what the documents say and argues nothing |
| Safe to publish? | No. It is not scrubbed | Yes, once you have read it and answered the share gate |

There is no page in between. Anything family should see goes on the outward page.

Nothing here uploads anything. Everything runs on your computer, and your documents stay there.

## Step 0: check your computer

```
python3 tools/views/doctor.py
```

It says what is installed and what to install. The inward pages need only Python. The outward page also needs Pillow and poppler (`pdfinfo`, `pdftoppm`); `qpdf`, `pdftotext` and (for recordings) `ffmpeg` make it better.

## Step 1: the record

The record is one JSON file. Its shape is written in `schema/record.schema.json`. To see working examples, run

```
python3 tools/views/example/seed.py examples
```

That writes 21 invented records (18 short ones and 3 full ones: a vehicle, a contractor, and an estate with a money ledger and a power of attorney) plus placeholder documents. Copy one and change it.

If your documents are files, `python3 tools/views/extract_text.py record.json --files-dir files --write record-with-text.json` reads the words out of them (PDF text, web pages, and with `--ocr` pictures and scans) into each exhibit's `text`, so quotes can be checked. It saves a copy; your record is not changed.

Six rules to remember while you fill it in:

- **Quote with double quotation marks.** Words inside “...” are checked word for word against the document text in the exhibit's `text` field. Quotes with no document text to check are listed as unchecked (an error with `--strict`).
- **Never type a count.** Write `{days:F1:F2}` (days between two facts), `{count:facts}`, `{count:documents}`, `{count:recordings}`, `{interval:ID}` or `{miles:EXHIBIT:A:B}` and the page works the number out. Typing "177 days", "twelve visits" or "nine repair orders" is an error. `{miles:E12:48,210:48,222}` is the difference of two odometer readings; both numbers must be in the text of exhibit E12, and the page prints 12. A dollar figure in what you write must be in a document the fact cites. A number the cited document states in its own words is allowed.
- **Never type a total.** Put each transaction in `ledger`, with the amount exactly as the statement writes it (`12,500.00`) and the statement as its source; the amount must be in that document's text. Write `{sum}` for all rows, or filter in pairs: `{sum:to:P3}`, `{sum:by:P3}`, `{sum:under:A1}`, `{sum:status:disputed}`, and `{sum:before:A1}`, `{sum:within:A1}`, `{sum:after:A1}` against an authority's dates. Totals stay on the inward record; `{sum}` is refused on the outward page.
- **Say what the documents say.** Wording that judges a case, predicts an outcome ("will likely win", "good chance", "the odds"), states a deadline ("the deadline is", "must file by"), says someone is liable or broke the law, or tells the reader to hire a lawyer is an error in anything you write. It is allowed inside quotation marks, and in the documents themselves.
- **A documented fact must look like its document.** When the cited document has text, at least one number, name or longer word of the fact has to be in that text. If a fact is right but worded differently, give the place and the document's own words (`loc` and `quote` on the source) and the quote settles it.
- **Quote the whole sentence.** A quote that stops right before "if", "or", "unless", "until", "but", "except" or "provided" leaves out a condition. It is noted while you draft and an error with `--strict`. End the quote with ... if you mean it to be partial.
- **Dates in your own sentences must exist in the record.** A date written like March 12, 2025 in a summary, section or span has to be the date of a fact, span, document or deadline. "Is scheduled" or "will" about a date before `meta.asof` is noted (an error with `--strict`).

## Step 2: the inward pages

```
python3 tools/views/build_views.py record.json out/inward
```

Open `out/inward/index.html`. Add `--strict` before you rely on it.

## Step 3: the outward page

```
python3 tools/views/build_home.py record.json out/outward --files-dir files
```

`files` is the folder holding the documents your record names. This makes two folders:

- `out/outward` is the page and the documents. This is the folder you publish.
- `out/outward-private` holds the **share report** (what was released, what was held back and why, every outgoing file with its fingerprint, personal details found, things to look at yourself) and the manifest. **Never publish this folder.**

**Nothing goes out unless you say so.** A fact appears only if it says `"outward": true`. A document is shared only if it says `"share": true`. A fact whose documents are not shared still appears and says "(document not included here)".

**Every outgoing file is cleaned and read back.** Photos are rewritten without their location and camera tags. PDFs are rewritten without Author, Subject, Title and Creator. Recordings lose their location tags. If a tag is still there afterwards, the build stops. If you have no `qpdf`, a PDF is rebuilt with `pypdf`, or as pictures of its pages (the text can then no longer be selected).

**The build also stops** if a shared document, thumbnail or link points at a private host (`private.example.com`, plus every host you list, one per line, in `tools/views/private-hosts.txt`; see `private-hosts.example.txt`; the file stays on your computer and is not committed), if the page, an outgoing text file or a PDF with a text layer holds "for counsel", "privileged", "work product" or "Rule 408", or if it holds a phrase listed in `held_phrases`. It also stops if a shared web-page document holds a script or embedded content, which would run on the reader's computer. Two switches per document help here: `needs_clearance` ("Counsel") blocks sharing until you clear it, and `allow_markers` (for example `["privileged"]`) says that a marker in this document is the other side's own boilerplate; the allowance is listed in the private report. Emails, phone numbers, street addresses and long numbers are not blocked; they are listed in the private report so you can clear each one. Pictures and recordings are not read by the tool: look at faces, plates, addresses and signatures yourself.

**DRAFT until the share gate is answered.** Until `meta.share_gate` has `recipient`, `confidentiality_checked`, `names_checked`, `defamation_reminder_ack` and `attorney_read` all set, the page says **DRAFT — not reviewed for sending** and has no snapshot id.

**Snapshot id.** Once the gate is answered, the page shows a snapshot id: a fingerprint of every published file, the page included. Change one document and the id changes. `--archive out/sent` also saves that exact copy, with its recipient, in `out/sent/<date>-<snapshot>/`; the tool never replaces or deletes a saved copy.

## If you have a record from an older version

- Add `"outward": true` to each fact you release and `"share": true` to each document you share. Before, everything was released unless switched off; now nothing is.
- Give every exhibit an `author` (`claimant`, `other_side` or `third_party`). A fact that only the claimant's own documents support is shown as "Per the claimant's letter of <date>", not as documented.
- Put dates in a section's `from` and `to`, not in its `title`. The page prints the date label from them.
- Replace typed counts ("177 days", "seven visits") with placeholders, or put the document's own words in quotation marks.
- Give a deadline the document's own words in `wording` (and `ex`, the exhibit it is in), instead of a date you worked out.
- Month-only and year-only dates: write `2025-09` or `2025`. They are shown as "September 2025" and are never made into the 1st.
- Thumbnails named in `thumb` are copied from `--files-dir` for shared documents only. Do not copy them into the output yourself; anything added after the build is not in the manifest or the snapshot id.
- A folder an older version made has no `.btr-output` file and is refused. Pick a new folder name.

## Checking without building

```
python3 tools/views/checks.py record.json            # the checks both builders run
python3 tools/views/checks.py record.json --outward --files-dir files --strict
```

Every problem is a sentence that names the fact or document. A broken record never produces a Python error message.

## Folders are safe

A build is made in a temporary folder next to the real one and swapped in only when it succeeds, so a refused build changes nothing. An output folder is replaced only if this tool made it before (it holds a small `.btr-output` file) or it is empty. Any other folder is refused, so a wrong folder name cannot delete your documents.

## Tests

```
python3 -m unittest discover -s tools/views/tests -t tools/views
```

The same tests also run from inside `tools/views/tests` or `tools/views` with plain `python3 -m unittest`, and from the repository root with `python3 -m unittest discover -s tools/views/tests`. They build all 20 examples in both layers, check that a set of broken records is refused with the right sentence, and check that photos, PDFs and recordings come out clean.

## What the build checks

Status words: **built** (code in this folder does it and a test shows it), **planned** (nothing does it yet; a test shows it is not done, so this table cannot quietly go out of date).

| What is checked | How it behaves | Status |
|---|---|---|
| Quotes match the document word for word | Only capitals, spacing and quote marks are ignored; dropping a "not" or an "un-" fails; no document text means "unchecked" (an error with `--strict`) | built |
| A number with a unit is never typed | Days, times, visits, miles, faults, recordings, cases, documents, and now repair orders, attempts, trips, emails, entries, incidents, occasions, appointments, actions, messages, calls, items, pages, photos, videos, clips, texts, letters and notices, with up to two words between the number and the noun. Quoted words, placeholders and figures the cited document states are exempt | built |
| A clock time is not a count | "The 11:18 recording" is left alone, as are a year before a noun ("the 2025 letters") and "no one calls" | built |
| A dollar figure in prose is in a cited document | $48.00 and $4,800 are different figures; $4,800.00 and $4,800 are the same. Facts are checked against the exhibits they cite, summaries and sections against every exhibit. Your own `ask` and `amount` entries are not checked | built |
| Advice and advocacy wording | Judging a case, argument and name-calling, as before; now also prognosis ("will likely win", "good chance", "odds", "should prevail") | built |
| A deadline asserted in your voice | "The deadline is", "must file by", "has until", "the statute of limitations expires". Put a deadline in `deadlines` with the document's words instead | built |
| Liability and law applied to the facts, or advice to hire a lawyer | "Is liable", "broke the law", "illegal", "at fault"; "should hire", "should consult an attorney" | built |
| A documented fact shares a key word with its document | At least one number, name or word of five or more letters from the fact must be in the cited document's text (all cited documents must have text for this to apply). A source with `loc` and a verified `quote` settles it. A rough test: it finds a fact the document cannot show, it does not prove one that it can | built |
| A quote clipped before a qualifier | A quote that stops right before if, or, unless, until, but, except or provided. A note while drafting, an error with `--strict` | built |
| Odometer miles are computed | `{miles:EXHIBIT:A:B}` needs both readings in that exhibit's text, the second larger; the page prints the difference | built |
| A featured still frame shows no unconfirmed grade | A still of a recording is checked against the grade and `reviewed_by` of the facts that cite the recording; a still whose recording has no grade shows none and is not an error. A note, and an error with `--strict` | built |
| Dates written in summaries, sections and spans exist in the record | Month D, YYYY (and D Month YYYY, YYYY-MM-DD) must be the date of a fact, span, document, deadline or `asof`. "Is scheduled", "set for" or "will" about a date before `asof` is a note (an error with `--strict`) | built |
| A shared link or thumbnail on a private host stops the outward build | `private.example.com` plus `private-hosts.txt` (one host per line, kept out of git) | built |
| Deadlines are entered with a source, never computed | The tool shows the deadline you entered and the document's words; it never works one out | built |
| Counsel markers, held phrases and personal details | "For counsel", "privileged", "work product", "Rule 408" and `held_phrases` stop the outward build; emails, phone numbers and addresses are listed for you to clear | built |
| Dates written without a year ("October 7") or as a month ("March 2025") | Not compared with the record | planned |
| An amount written in words ("forty-eight dollars") or as a euro or pound figure | Not compared with the documents | planned |
| A dollar figure in `meta.ask` or `meta.amount` | Not compared with the documents; these are your own entries | planned |
| A fact that reuses a document's words but changes what it means | Only a person can see this; the key-word test cannot | planned |

## What is here

| File | What it does |
|---|---|
| `build_views.py`, `build_home.py` | The two builders |
| `checks.py` | The one checker both builders and the case converters run first |
| `private-hosts.example.txt`, `private-hosts.txt` | The format for the list of private hosts, and your own list (not committed) |
| `btr_common.py`, `btr_scrub.py` | Shared helpers; metadata removal and PDF page images (named so they cannot clash with a case folder's own `common.py` or `scrub.py`) |
| `cursor.js`, `lightbox.js` | The timeline reading and the document viewer, copied into the outward page |
| `doctor.py` | Checks your computer |
| `extract_text.py` | Reads the words out of your document files so quotes can be checked |
| `example/seed.py` | The 20 invented example records |
| `tests/` | The tests and the must-fail records |

This is information, not legal advice. The tool never works out or confirms a deadline: it shows the deadline you entered and the words of the document it came from.
