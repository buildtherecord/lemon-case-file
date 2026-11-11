# The method

Everything below was learned the hard way on a real claim. The prompts in `prompts/`
operationalize these rules; this file is the why.

## 1. One source of truth

Build a single machine-readable catalogue (the "bundle", see `schema/`) holding every
incident capture, repair order, recall, bulletin, communication, and call. Every
artifact you produce — website, PDF, records request, cover email — is generated from
the bundle, never hand-edited. When something is wrong, you fix the bundle and rebuild.
This is what keeps a 30-page record internally consistent under hostile reading.

Every number that appears in prose (days out of service, incident counts, repair counts)
is computed from the bundle at build time, never typed. Your build asserts it: it fails
if the prose and the data disagree, and the ground rules in prompt 00 and prompts 06 and
07 tell the assistant to write those assertions. The view builders in `tools/views/`
compute their own counts and day intervals from the record and refuse a number typed
into prose (`tools/views/checks.py`). The last section of this file lists what the shipped
tools check today. No asserted number survives without a source.

## 2. Evidence discipline

- **A screenshot proves only what is visible in it.** If the call-log screenshot shows
  a date but no duration, your record states a date and no duration. Never "reconstruct"
  times or numbers from memory or from an earlier AI conversation — if it has no primary
  source, it does not enter the record.
- **Quotes are verbatim.** If the dealer wrote "no repair available," quote exactly
  that, in quotation marks, and keep the document.
- **Curate what you release, and delete nothing.** Duplicates, blurry captures, and
  incidents you cannot tie to the defect waste the reviewer's attention and leak doubt.
  Leave them off the outward page (section 7a). In the inward record, fold duplicates into
  the one you keep and show weaker items quietly. Strength comes from density of verified
  fact, not volume.
- **Mark the gaps honestly.** Where you failed to capture an incident, say so and cite
  the contemporaneous written report instead ("reported in writing the same day — no
  video exists"). Gaps stated plainly read as honesty; gaps papered over read as
  fabrication the moment anyone checks.
- **The omission rule.** Leave weak items off the outward page, but never omit a document
  whose absence would make you look dishonest when the other side produces it. If the
  manufacturer has a written position against you, host it yourself and let your
  timeline answer it.

## 2a. Triage: grade by what is shown, and let the owner watch

Every capture gets a grade, and the grade means one thing to the reader:

- **A: shown on camera.** The fault itself is visible in the recording. A caption may
  explain what you are looking at, but the footage has to carry the fault.
- **B1: supporting, described.** You describe the fault in narration; the recording does
  not clearly show it. Well documented, not conclusive on its own.
- **B2: supporting, context.** Context, a comparison, a retake, or a timestamp to check,
  on a recording that documents an incident.
- **C: weaker.** Little usable content, no clear link to a defect, or a clip that is only
  a timestamp. It stays in the catalogue; it is not part of the argument.

Rules that came from getting this wrong once:

1. **Stills cannot judge motion or sound.** An assistant grading video from sampled
   frames will demote real evidence (a window that moves the wrong way, a handle that
   never extends, a connector that will not release all happen between frames) and will
   sometimes promote weak evidence. It may propose grades from what is visible. Anything
   whose grade depends on movement or audio is a question for the owner, not a verdict.
   In the case this method came from, a stills-only first pass cut the top grade to a
   fraction of its size; watching the clips restored roughly half of what it cut, including
   clips that looked like nothing in stills and were the owner's best evidence, and the owner
   rated some of the assistant's keepers lower. Both errors ran in both directions.
2. **The owner watches, and the owner's call wins.** Build a watch list (`tools/triage/`):
   one offline page, one question per item, where to look, a place to note the second.
3. **The watch list is a living queue.** Order it by how likely each item is to change
   grade. Answered items leave it once the answer is applied; new questions join it as
   answers raise them (a clip that looked like nothing but was top-grade means the clips
   like it get queued too).
4. **Count a piece of evidence once.** Find duplicates by comparing footage, not captions:
   the same recording exported twice can look different and carry two captions. Fold a
   duplicate into the one you keep: hidden, not counted, never deleted, with a note on the
   survivor. A retake is not a duplicate.
5. **An excerpt is never separate evidence.** Show it, label it with its parent, and leave
   it out of every count.
6. **Counts are computed, and stored counters are recomputed.** Any total kept in the data
   (per period, per category) drifts when items are removed; your build recomputes it and
   fails on a mismatch. The shipped tools compute counts fresh and do not read stored
   counters, so a check that compares a stored counter with the data is planned.
   `tools/triage/apply_answers.py` prints its counts with folded items and excerpts left out.
7. **Captions use the owner's own words, lightly edited.** Keep every direct quote
   (`tools/triage/quotecheck.py` checks a grades file when you run it; no site build runs it
   yet), attribute on-screen text to the screen and not to the speaker, and ask how a
   control is physically operated before describing it: "pulled" and "pressed" are
   different complaints, and the wrong verb can make a defect look like user error. Leave
   grading remarks and advocacy out of captions.
8. **Flag at triage, not at publication.** Faces, plates, third-party names, birth dates,
   employer material, anything inside a settlement or release you have already signed, and
   timestamps that conflict with the footage. The owner decides what is flagged; questions
   about legal scope go to counsel.
9. **Lead with the strongest grade, and hide nothing in the inward record.** The first view
   shows the A recordings, with the counts of every other grade one click away; weaker
   recordings stay visible and quieter. On the outward page you release what you choose,
   and the omission rule in section 2 still applies. Featured recordings must be A grades
   the owner has confirmed (`reviewed_by` is `owner`). `tools/views/checks.py` flags an
   unconfirmed grade on a featured still or recording (a note while drafting, an error with
   `--strict`); `grades.csv` itself is checked by `tools/triage/apply_answers.py`.

This is one instance of a general loop that works at every level of the record: a queue of
open questions, answered by the owner on a private page, applied by the assistant to the
single source of truth, rebuilt, with a plain account of exactly what changed, then cleared
and refilled. If you also track the status of facts (verified, asserted, open, computed),
write the status in words wherever grades appear; the letters overlap.

## 3. The record argues by existing

The narrative states facts in plain language and never makes a legal argument. "The
car was at the dealership 84 days" needs no adjective. State each figure for the interval
its source covers: if the only odometer readings are on two repair orders, give the miles
between those two dated readings and both dates, and do not stretch that figure over the
whole stay. Legal
vocabulary (the statutory standard you must meet) appears exactly once, factually, in
the cover email — not in the record. Reviewers, arbitrators, and opposing counsel all
discount advocacy; none of them can discount a dated repair order.

Related: no advocacy labels in filenames or titles ("STRONGEST", "damning", etc.).
If a document is strong, its contents will say so.

## 4. Organize by demonstrated problem

Group evidence per problem (windows, door handles, displays, charging, …), not per
date alone. A reviewer deciding "substantial impairment" thinks in problems: when was
it first reported, what did the manufacturer do, did it recur after repair. Your
component ledger should answer, for every part touched: what was done, the
manufacturer's own stated basis for doing it, and whether the symptom recurred.

Recurrence after repair is the spine of a repurchase case. Make it impossible to miss.

## 5. Their own records are evidence — request them

(The general form of this — the counterparty-file principle — is: whoever is
deciding against you holds records about your case; request them, organized
around your timestamps, before you argue. Every sibling method has its
instance: diagnostic logs here, the claim file in insurance, the public permit
record in construction.)

Manufacturers retain diagnostic session logs, fault memory, and telematics that
outlive what the dealer clears at service. Request them in writing, organized by your
timestamped incidents (full calendar day around each), plus complete logs from every
service visit. Ask that any fault found in those records be treated as reported by
you. Do not ask for specific fault codes — you do not know their taxonomy, and a
specific list invites a narrow answer.

## 6. Adversarial review before sending

Before anything leaves your hands, have it attacked from six perspectives (see
`prompts/08`): a sympathetic insider who wants to say yes cheaply, the manufacturer's
lawyer who wants an easy no, a journalist, another law firm, another claimant using
your work as a template, and a regulator. Fix what the hostile readings find:
hyperbole, padded counts, overstated captions, missing context. The pass that hurts
most is the one that saves you.

## 7. Presentation is respect

A clean abstract up front (what happened, in four sentences, and what you are asking
for). A timeline a reviewer can navigate in one screen. Every document one click from
the claim it supports, at full resolution. Exhibit numbers stable across website, PDF,
and email. You are making it easy to say yes — the reviewer who can verify your claim
in thirty seconds is a reviewer who stops looking for reasons to doubt you.

## 7a. Two pages from one record

The record is published two ways, and no third. The **outward** page is what anyone you
send it to may read: public, light, phone-first. It carries only the items you released,
scrubbed of private details; it argues nothing; "Last updated" and a snapshot id sit at the
top. The **inward** record is the full linked record plus material meant only for your
attorney: for you and your attorney, maintained deliberately, nothing deleted. There is no
page in between, so anything family should see goes on the outward page. Both are generated
from the one source of truth (section 1), and nothing moves from inward to outward except by
being released. A record built before you hire a lawyer is generally not privileged, and
"held back" is not "privileged." The plain-language version is
`docs/claimant-journeys/two-layer-model.md`.

## 7b. Money, authority, and whose claim it is

Some disputes are about money that moved: a deposit, a payout, an estate's accounts. Put
each transaction in the record's `ledger`, one row per transaction, with the amount exactly
as the statement writes it and the statement as its source. Never type a total; write
`{sum:...}` and the build adds up the rows. A row whose amount is not in the document it
cites is an error.

Some disputes turn on who was allowed to act for whom: an agent under a power of attorney,
a trustee, a co-owner, a contractor's office manager. Record each `authority` as the
document that created it and the two facts that bound it in the record. The build places
each transaction before, inside, or after those dates, by date alone. It never says a
transaction was or was not allowed, and it never decides when an authority ended. Those
are questions for a lawyer.

The person building a record is often not the person who can bring the claim. Say whose
claim it is (`meta.standing`), how they agreed to the record, and who confirmed it. Until a
lawyer has, write "nobody has confirmed this yet," and the build will.

When the record accuses a named person, keep it off the outward page (`meta.outward:
false`) until a lawyer has read it. Use roles, not characterizations ("the agent named in
the document"), and list the words this case never uses in `meta.banned`. Families can be
on both sides of these disputes, and a record shared early can be read by the wrong one.

## 8. Timing and publication

If you intend to share your method or template publicly, do it **before** you sign
anything. Settlement agreements commonly include confidentiality clauses; a generic
template published before any agreement existed is cleanly yours to share, while the
same material published after signing may not be. Keep every case-specific fact (VIN,
names, case numbers, documents, media) out of anything public, permanently. And have
any confidentiality clause you are offered reviewed before you sign it — this repo is
not legal advice.

## 9. What the tools check today

Section by section, this file says what the record should be. This table says what the
shipped tools enforce, checked against the code on 2026-10-04. If it and the code
disagree, the code is right and this table is the bug. Do not tell a reader that "the
build checks" something that is not marked built here.

| Rule | Where it is enforced today | Status |
|---|---|---|
| Counts, day intervals and totals computed from the record | `tools/views/build_views.py` and `build_home.py` (counts, intervals, the outward "Day N" tile); `tools/triage/apply_answers.py` (grade counts) | built |
| A number typed into prose matches the data | `tools/views/checks.py`, run by both builders: a number with a unit (days, visits, miles, repair orders, entries and the rest of the list in `tools/views/README.md`) is an error unless it comes from a placeholder or the cited document states it; every dollar figure in prose must be in a cited document | built |
| A stored counter matches the data | Nothing; the builders do not read stored counters | planned |
| Money totals are added up from ledger rows, and each row's amount is in the document it cites | `checks.py`, both builders: a `{sum:...}` placeholder is computed from the rows; an amount missing from the cited document's text is an error, and one with no document text is listed as unchecked; `{sum}` is refused on the outward page | built |
| Each transaction is placed against the dates of an authority, by date alone | `build_views.py` (the Money page); `checks.py` checks that an authority starts and ends at day-dated facts. Nothing decides whether a transaction was allowed | built |
| The record says whose claim it is | `checks.py` notes a record with a ledger or authorities and no `meta.standing`; the brief shows it as unconfirmed until someone confirms it | built |
| A record that accuses a named person stays off the outward page | `build_home.py` refuses a record with `meta.outward: false` | built |
| A fact marked documented has a source, every source names a real exhibit, and the document shows the fact | `checks.py`, both builders (the last part is a rough key-word test, `tools/views/README.md` says what it cannot catch) | built |
| A quote in prose appears in its exhibit's text, word for word | `checks.py`, both builders: only case, spacing and quote marks are ignored; dropping "not" fails; a quote with no document text is "unchecked" (an error with `--strict`); a quote clipped before if/or/unless is flagged | built |
| A rewritten caption kept the quotes of the original | `tools/triage/quotecheck.py`, run by hand on `grades.csv`; no site build runs it | built (not in any build) |
| Advice, advocacy, prognosis and asserted-deadline wording is rejected | `checks.py`, both builders, in text the claimant or assistant wrote (never inside quotes or exhibit text) | built |
| Deadlines are claimant-entered with a source, never computed | `build_views.py` fails on a deadline with no source or one marked computed. Deadlines never render on the outward page | built |
| Held-back items, deadlines, the lawyer field and strategy never render outward | By construction (`build_home.py` has no code path that renders them); counsel markers and held phrases also stop the outward build | built |
| A document goes outward only if released | `build_home.py`: `share` must be explicitly true; a fact must be `outward: true`; thumbnails and page images only for released documents; a link to a private host stops the build | built |
| Grades are A, B or C; a B has a tier; folds and excerpts point at real items; counts leave out folded items and excerpts | `tools/triage/apply_answers.py`, on `grades.csv` only. No site or PDF builder reads `grades.csv` | built (grades file only) |
| Featured recordings and stills show only grades the owner confirmed | `checks.py` (note while drafting, error with `--strict`) | built |
| "Last updated" at the top of every page | Both builders print the record's `updated` field | built |
| Snapshot id on the outward page | `build_home.py` hashes every published file and keeps the private share report and manifest outside the published folder; sent copies are not yet kept in a dated folder by the tool | partial |
| Share gate and review states | `build_home.py` stamps the page DRAFT and omits the snapshot id until `meta.share_gate` is complete. Nothing asks the gate's questions yet (a wizard step) | partial |
| Leftover private details in what goes outward (names, address, account numbers, file metadata) | `build_home.py` strips metadata from every published file and fails on any left; emails, phone numbers and addresses are listed in the private report for the owner to clear (not blocked; masking is a separate step) | partial |
