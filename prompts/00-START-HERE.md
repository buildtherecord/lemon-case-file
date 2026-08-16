# How to use these prompts

These are working instructions for an AI assistant (Claude or comparable) that can
read your files, run code, and produce documents. Each numbered file produces one
artifact. Work in order; later prompts consume earlier outputs.

## Session order

| # | Prompt | Produces |
|---|--------|----------|
| 01 | evidence-inventory | Catalogue of every capture and document, deduplicated |
| 02 | timeline-and-bundle | The single source-of-truth JSON (`bundle.json`) |
| 03 | repair-ledger | Component ledger: what was done, their stated basis, recurrence |
| 04 | phone-and-contact-log | Verified call/contact record from carrier data + screenshots |
| 05 | diagnostic-records-request | Per-problem records request (PDF + CSV) |
| 06 | evidence-site | Password-gated website (uses `site/`) |
| 07 | case-pdf | Printable case file with exhibit index |
| 08 | adversarial-review | Six-perspective attack pass on everything above |
| 09 | redaction-and-publishing | PII scrub before anything goes online or to media |
| 10 | cover-email-and-monitoring | The short email + how to watch reviewer activity |

## Ground rules to give the assistant once, at the start

Paste this at the top of your first session:

> You are helping me build a vehicle-defect case file I may submit to the
> manufacturer, an arbitrator, or a court. Non-negotiable rules:
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

## What only you can decide

The assistant builds; you rule. Decisions that stay yours: what gets omitted, what
goes online, wording of anything with your name on it, redaction scope, whether and
when to send, and anything irreversible. A good assistant will queue these for you
instead of guessing.
