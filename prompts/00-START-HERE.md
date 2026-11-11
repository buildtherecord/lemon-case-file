<!-- DRAFT: needs licensed-attorney review before publishing -->
# How to use these prompts

These are working instructions for an AI assistant (Claude or comparable) that can
read your files, run code, and produce documents. Each numbered file produces one
artifact. Work in order; later prompts consume earlier outputs.

## First: what kind of case is this?

Before any numbered prompt, answer four questions in plain words. They decide which
modules below apply. Nothing here assumes what happened.

1. **What happened**, in a sentence or two, in your own words.
2. **Who was harmed**, and is that you? If not, whose claim might it be (an heir, an
   executor, a policyholder, a co-owner)? Write down how that person agreed to this
   record. Who can bring a claim is for a lawyer to confirm.
3. **What do you want?** Money back, a repair, a correction, an accounting, for it to stop.
4. **Does the record accuse a named person** of doing something wrong? If so, it stays off
   the outward page until a lawyer has read it (`METHOD.md` section 7b).

| If the case involves | Add |
|---|---|
| A product that keeps failing (a vehicle, an appliance) | 03 repair ledger, 05 records request (diagnostic logs) |
| Money that moved (deposits, payouts, accounts, an estate) | The record's `ledger`, with `{sum:...}` totals (`METHOD.md` 7b) |
| Someone acting for someone else (a power of attorney, a trustee, an agent) | The record's `authorities` (`METHOD.md` 7b) |
| An insurer, a contractor, a landlord, a bank | 05 records request, aimed at that party's own file (`METHOD.md` section 5) |

Every case uses 01, 01b, 02, 04, 08 and 09.

## Session order

| # | Prompt | Produces |
|---|--------|----------|
| 01 | evidence-inventory | Catalogue of every capture and document, deduplicated |
| 01b | evidence-triage | Graded, de-duplicated, owner-confirmed catalogue + a living watch list |
| 02 | timeline-and-bundle | The single source-of-truth JSON (`bundle.json`) |
| 03 | repair-ledger | Component ledger: what was done, their stated basis, recurrence (product cases) |
| 04 | phone-and-contact-log | Verified call/contact record from carrier data + screenshots |
| 05 | diagnostic-records-request | Records request to the other side's own file (diagnostic logs, a claim file, bank records) |
| 06 | evidence-site | Password-gated website (uses `site/`) |
| 07 | case-pdf | Printable case file with exhibit index |
| 08 | adversarial-review | Six-perspective attack pass on everything above |
| 09 | redaction-and-publishing | PII scrub before anything goes online or to media |
| 10 | cover-email-and-monitoring | The short email + how to watch reviewer activity |

## Ground rules to give the assistant once, at the start

Paste this at the top of your first session:

> You are helping me build a case record I may give to a lawyer, the other side, a
> reviewer, or a court. Do not assume what happened or who is at fault; ask me.
> Non-negotiable rules:
> 1. Never state a fact without a primary source I actually possess. A screenshot
>    proves only what is visible in it. No reconstructed times, numbers, or quotes.
> 2. Every count or duration in any output must be computed from the catalogue at
>    build time, with an assertion that fails the build on mismatch.
> 3. Quote documents verbatim or not at all.
> 4. State facts; never write legal argument into the record.
> 5. Flag anything that reads as hyperbole, advocacy, or a padded count — including
>    things I wrote.
> 6. If I ask for something that would misstate the record, say so plainly.
> 7. Keep a running decisions file (append-only) recording every ruling I make, so
>    later sessions do not re-litigate them.
> 8. Money totals are added up from transaction rows, each from a statement; never type
>    a total. Say where a transaction falls against someone's authority by date only;
>    never say whether it was allowed.
> 9. Use roles, not labels, for people ("the agent named in the document"). No
>    characterizations, even if I use them.
> 10. A grade is a proposal until I have watched the clip. Stills cannot judge motion
>    or sound; queue those for me. Count each piece of evidence once, and never count
>    an excerpt as separate evidence.

## What only you can decide

The assistant builds; you rule. Decisions that stay yours: what gets omitted, what
goes online, wording of anything with your name on it, redaction scope, whether and
when to send, and anything irreversible. A good assistant will queue these for you
instead of guessing.

## Jurisdiction files

If `jurisdictions/` contains a file matching my jurisdiction or plan type, load
it as a MAP of leads — statutes, bodies, thresholds. Repo entries are dated
signposts, not current law; entries over 12 months old are historical hints. For
any deadline, threshold, or notice rule a lead mentions, show me the primary
source's own words, quoted exactly, with the citation and the date you read it,
marked "not confirmed by anyone yet". You do not calculate or confirm deadlines,
and no deadline is ever taken from the repo or from you: tell me who can confirm
it (legal aid, a courthouse self-help center, a lawyer — my state bar's referral
service can point me to one). If no file exists for my jurisdiction, find the
equivalent official sources and quote them the same way, and offer to draft a
new jurisdictions file from what we collect — that contribution is the repo's
whole point.

Deadlines may apply that you and this tool don't know about. Stopping or waiting
does not stop a deadline and may give up rights. Ask someone who can advise you
about your situation.
