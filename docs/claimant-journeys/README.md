# Claimant journeys — personas, scenarios, journeys

Status: **draft v1 — revised after an attorney-lens review (unauthorized practice of law) and a service-design review; updated to the two-layer model on 2026-10-04.** Not legal advice. De-identified: every person and fact below is a composite or generic pattern; nothing here is a real party's data.

Purpose: design the Build the Record method and tools around the people who use them, for three product types (vehicle repurchase, contractor dispute, insurance denial), and make sure each journey has an honest way to stop or pause, and a route to people who can give advice about the claimant's situation. The tool never says whether anyone should file.

## Principles

1. **The record is the product; the claimant is its best source.** Help people be a great source: capture early, label memory as memory, never alter originals.
2. **Never push toward or away from filing.** Every journey ends in a decision the claimant owns, with a defined route to people who can advise (legal aid, bar referral, courthouse self-help, a first consultation with an attorney). The tool says plainly that it cannot tell anyone whether to file, whether they are in time, or what the law means for them.
3. **Every claim is dated and sourced.** A "Last updated" stamp is visible at the top of every page. Facts show a status: documented / claimant's account / disputed.
4. **One source of truth, two pages.** The **outward** page (what anyone the claimant sends it to may read: the other side, a reviewer, a mediator, family, the media) and the **inward** record (for the claimant and the claimant's attorney, with counsel-only material once an attorney directs the work). Both are generated from the same record. There is no middle layer: anything family should see goes on the outward page. Held-back material never reaches the outward page. See `two-layer-model.md`.
5. **Statute is a signpost.** Law and policy shown as written, linked to the primary source with a "verified on" date, and kept separate from the claimant's facts (the tool does not apply law to facts). Deadlines are claimant-entered; the tool never computes or confirms them. See `safety-gates.md`.
6. **Care, not therapy.** Link real, current support (988 for crisis; peer-support lines such as NAMI's helpline; low-cost counseling directories). Do not promise "free therapy" as a product feature.
7. **Pace the news.** No worst-case reveals at night; always offer to pause.

## Stakeholder needs (summary: what each asks for, not what the tool shows)

| Who | Needs |
|---|---|
| Claimant | Cost/time clarity per path; a "what happens next" calendar; 30-second capture on a phone; privacy and an access log; plain language; a graceful exit and archive |
| Attorney / paralegal | One-page triage (deadlines, dollar range, strongest/weakest evidence, conflicts); provenance per document; a privilege boundary they trust; export to their case tool |
| Other side's reviewer | A short, verifiable file and a clear ask; verbatim quotes; no argument |
| Neutral (mediator, AG staff, arbitrator) | A chronology and exhibits verifiable in ten minutes |
| Journalist | Verifiable summary, permission to quote; will find the weakest fact first |
| Platform | Visible corrections process; verified-vs-account labels; clear limits on what the tool is; human review near legal-advice territory |

## Method

1. One persona per product, from real de-identified cases (goals, fears, tech comfort, time, who else is involved).
2. Name each scenario for what the record looks like, never for a verdict: documented, thin record, cost vs. recovery, time uncertain (`scenarios.md`). No scenario type says whether anyone should file, and the tool never gives that verdict.
3. A journey map per scenario: stages × (claimant does / tool shows / observable pass signal / failure risk).
4. Professional personas, including legal-aid screeners and volunteer coaches (first-hour needs).
5. Test with two or three real people on a prototype before building more.

## Stages used in every journey

1. Notice something is wrong 2. Preserve and collect 3. Understand options 4. Decide (the claimant's choice of route, including waiting or stopping) 5. Escalate through the chosen path 6. Keep the record live 7. Resolve 8. Close and archive

Files: `personas.md` (18 claimant patterns across three products, plus professionals), `scenarios.md` (template, worked journeys, interrupt journeys), `decision-check.md` (the "Where do I stand?" check and handoffs), `safety-gates.md` (information vs. advice, and which gate applies to which layer), `two-layer-model.md` (outward and inward, in one page), `intake-and-ux.md` (what the two layers change in the wizard and screens, with built / partial / planned marked), `test-plan.md` (two-week prototype test).
