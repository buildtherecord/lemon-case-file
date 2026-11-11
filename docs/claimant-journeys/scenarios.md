# Scenarios and journeys

## Template (every journey uses it)

| Stage | Claimant does | Tool shows | Observable pass signal | Failure risk |
|---|---|---|---|---|
| 1 Notice | | | | |
| 2 Preserve and collect | | | | |
| 3 Understand options | | | | |
| 4 Decide | | | | |
| 5 Escalate (chosen path) | | | | |
| 6 Keep the record live | | | | |
| 7 Resolve | | | | |
| 8 Close and archive | | | | |

A scenario is **testable** only when every stage names a concrete action, a screen or artifact, and a pass signal someone can observe. "Feels" is gathered by asking, not asserted.

Scenario types (each names what the record looks like; none is a verdict about filing, and the tool never gives one):
- **Documented** — a record that supports the claim on its face.
- **Thin record** — little evidence beyond the claimant's account.
- **Cost vs. recovery** — the amount at stake is small relative to the effort; an offer may exist.
- **Time uncertain** — the claim may be outside a time limit; nobody has checked.

## Worked journeys (three, to show the template)

### V2 · Retiree, new pickup, intermittent noise — *Thin record*
| Stage | Claimant does | Tool shows | Pass signal | Risk |
|---|---|---|---|---|
| 1 | Hears the noise again after the 4th visit | "Start a log" with a 30-second voice or video capture; large type | Saves a capture on first try, with date | Fault is intermittent; capture too late |
| 2 | Daughter helps collect work orders in a shoebox | Photo-first scan, auto-naming, "original untouched" label | Has all visit dates; doesn't rename originals | Orders missing; claimant edits documents |
| 3 | Reads what the warranty says | Warranty text shown as written, with a link; no interpretation | Can say in own words what the warranty covers *and that the tool doesn't tell them whether they qualify* | Treating signposts as advice |
| 4 | Considers options | Generic list of paths (dealer escalation, manufacturer, arbitration program if offered, legal-aid or attorney consult, stop) with "ask a person who can advise you" block | Names two paths and finds *stop* and *get advice* unprompted | Skipping a prior-step requirement |
| 5 | Takes the record to a free consult | One-page brief; the *claimant* fills in "deadline I know of / who told me" | Attorney can read brief in under 5 minutes | Held-back notes leaking |
| 6 | Logs the next visit | Reminder; "Last updated" visible | Adds an entry within a day | Drift |
| 7–8 | Settles or stops | Reminder that stopping does not stop any deadline; archive export | Archive opens on another device | Giving up rights unknowingly |

### S2 · Renter, withheld deposit — *Time uncertain*
Stage 1: lease ended three weeks ago; list of "damages" arrives. Stage 2: move-in photos, lease, texts. Stage 3: the tool shows the *text* of the local deposit-return rule if known for the claimant's state (state required as first input), with "deadlines may apply that you and this tool don't know about." Stage 4: options include a demand letter template *prepared by a legal-aid or court self-help source*, small claims, mediation, or stopping; a "retaliation worry" branch keeps the record private by default and routes to tenant counseling. Pass signal: the tester can say what to do if they fear the landlord's reaction.

### I1 · Employer-plan member, denied treatment — *Documented*
Stage 1: the denial letter arrives; the first screen asks for the plan type and the *date on the letter*. Stage 2: policy and plan documents, letter, provider notes; exact quotes beside the exact denial language. Stage 3: tool shows that internal appeal and external review exist and that appeal windows can be short ("find the deadline on your letter; ask your plan or a qualified person to confirm"). Stage 4: continue treatment? That is not a tool decision — route to provider and a patient advocate. Pass signal: the tester states the appeal deadline from the letter and who confirmed it.

### M1 · Partner of an heir, an agent under a power of attorney — *Documented, accuses a named person*
Stage 1: a parent has died; the family learns an agent under a power of attorney moved money. The first screen asks who was harmed, whose claim it might be, and whether that person agreed to the record (recorded in `meta.standing`; "nobody has confirmed this yet" until a lawyer does). Stage 2: the power of attorney, the death certificate, bank statements; each transaction becomes a ledger row with the amount as the statement writes it. Stage 3: the Money page shows each row before, inside or after the authority's recorded dates, by date alone, with totals computed from the rows; it never says a transaction was allowed or not. Stage 4: routes are listed without ranking (probate court, a civil claim, police, the bank's fraud department, stop), each with "ask a person who can advise you." Stage 5: the record stays off the outward page (`meta.outward: false`); the inward brief goes to a lawyer. Pass signal: the tester can say whose claim it is, find the total dated after the recorded end, and say that the page did not call anything theft. Risk: a characterization in the organizer's own words; sharing with family members on the other side. Worked example: `tools/views/example/seed.py`, FULL3.

## The remaining scenarios (outline; to be written to the template)
V1 Thin record · V3 Cost vs. recovery (income loss, lease) · V4 Documented (two warranties) · V5 Time uncertain (counterparty changed) · V6 Documented (repeated faults, open recalls) · S1 Documented (deposit, no work) · S3 Cost vs. recovery · S4 Time uncertain (chargeback window) · S5 Documented (possession of goods; coercion) · S6 Thin record (many similarly harmed) · I2 Documented (estimate gap) · I3 Cost vs. recovery (valuation) · I4 Time uncertain (short appeal windows) · I5 Cost vs. recovery · I6 Thin record

## Interrupt journeys (apply to any scenario)

1. **The other side contacts the claimant** (call, goodwill offer, apology plus release). *Before you reply:* log the contact; don't sign anything; what a release can do (it may end claims); who can review it. Pass: tester pauses and logs instead of replying.
2. **Claimant in crisis tonight.** Pause, save, resume later; no deadline reveals at night; 988 and a trusted-person handoff; no required next step. Pass: tester can stop in one tap and returns to the same place.
3. **Deadline may already have passed.** The tool never says "too late." It shows: "Time limits can be paused or extended, and some claims have different limits. Ask a qualified person now. Keep everything." Preserve the record.
4. **Retaliation or dependency fear** (insurer, landlord, employer, dealer holding the car, contractor who knows where you live). Private by default; no sharing links until chosen; a "talk to someone first" route.
5. **Co-claimants and proxies.** Who owns the record, who can edit, whose messages are included, consent before anything goes on the outward page. An elder with an adult child: proxy mode with the elder's consent recorded.
6. **Non-English or low-literacy claimant.** Audio and photo-first capture; a bilingual proxy can read aloud; plain-language checks in the user's language when translations are verified.
7. **Evidence the claimant should not have** (secret recordings where consent laws apply; the other side's internal documents). Stop and ask a qualified person before using or sharing.
8. **The claimant wins.** Settlement terms may include confidentiality or limits on publishing. Before posting or sharing anything, check the terms. What to archive.
9. **The counterparty disappears** (closed business, bankruptcy, changed owner). The record outlives them; routes: licensing boards, recovery funds, bankruptcy claims process (a qualified person confirms).
10. **Multiple deadlines.** The tool lists *every* deadline the claimant reports, with source, and never ranks them. A claimant-entered "earliest" is shown first.

## Professional-side journey
1. Intake — attorney reads the one-page brief from the inward record (claimant-supplied deadline and source, dollar range, documents, cast, conflicts, prior lawyer, what has been sent to the other side, log of what the tool showed).
2. Verify — paralegal checks provenance (hashes, original metadata) and marks gaps.
3. Theory — attorney builds the elements chart. *The claimant-facing tool does not.*
4. Build — claimant keeps the record live; paralegal merges.
5. Escalate — letters and exhibits prepared by or under the attorney.
6. Resolve and close — outcome logged; archive.
