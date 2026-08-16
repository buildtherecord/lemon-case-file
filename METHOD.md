# The method

Everything below was learned the hard way on a real claim. The prompts in `prompts/`
operationalize these rules; this file is the why.

## 1. One source of truth

Build a single machine-readable catalogue (the "bundle", see `schema/`) holding every
incident capture, repair order, recall, bulletin, communication, and call. Every
artifact you produce — website, PDF, records request, cover email — is generated from
the bundle, never hand-edited. When something is wrong, you fix the bundle and rebuild.
This is what keeps a 30-page record internally consistent under hostile reading.

Every number that appears in prose (days out of service, incident counts, repair
counts) is computed from the bundle at build time and the build fails if the prose and
the data disagree. No asserted number survives without a source.

## 2. Evidence discipline

- **A screenshot proves only what is visible in it.** If the call-log screenshot shows
  a date but no duration, your record states a date and no duration. Never "reconstruct"
  times or numbers from memory or from an earlier AI conversation — if it has no primary
  source, it does not enter the record.
- **Quotes are verbatim.** If the dealer wrote "no repair available," quote exactly
  that, in quotation marks, and keep the document.
- **Curate ruthlessly.** Duplicates, blurry captures, and incidents you cannot tie to
  the defect waste the reviewer's attention and leak doubt. Cut them. Strength comes
  from density of verified fact, not volume.
- **Mark the gaps honestly.** Where you failed to capture an incident, say so and cite
  the contemporaneous written report instead ("reported in writing the same day — no
  video exists"). Gaps stated plainly read as honesty; gaps papered over read as
  fabrication the moment anyone checks.
- **The omission rule.** Leave out what is weak, but never omit a document whose
  absence would make you look dishonest when the other side produces it. If the
  manufacturer has a written position against you, host it yourself and let your
  timeline answer it.

## 3. The record argues by existing

The narrative states facts in plain language and never makes a legal argument. "The
car was at the dealership 177 days with 13 miles driven" needs no adjective. Legal
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

## 8. Timing and publication

If you intend to share your method or template publicly, do it **before** you sign
anything. Settlement agreements commonly include confidentiality clauses; a generic
template published before any agreement existed is cleanly yours to share, while the
same material published after signing may not be. Keep every case-specific fact (VIN,
names, case numbers, documents, media) out of anything public, permanently. And have
any confidentiality clause you are offered reviewed before you sign it — this repo is
not legal advice.
