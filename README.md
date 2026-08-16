# The Case-File Method

A method, a set of AI prompts, and a small amount of infrastructure for a vehicle owner
to build a professional-grade defect case file — the kind of evidence presentation a
manufacturer's repurchase reviewer, an arbitrator, or an attorney takes seriously —
without hiring anyone.

It was developed during a real, self-represented lemon-law repurchase claim, working
with an AI assistant (Claude) as the builder. Everything case-specific has been removed;
what remains is the process that made the record persuasive.

## What you end up with

- **A single source-of-truth catalogue** of every incident you recorded, every repair
  order, every recall and technical bulletin, every call and email — dated, verified,
  deduplicated.
- **A password-protected evidence website** (free Cloudflare tier) with a plain-language
  narrative, an interactive timeline, a filterable evidence grid, and playable video
  exemplars — plus an access log so you can see when the manufacturer actually reviews it.
- **A printable case-file PDF** with a component repair ledger, chronological record,
  and a numbered exhibit index.
- **A diagnostic-records request** organized per demonstrated problem, so the
  manufacturer's own telemetry has to answer your timestamps.
- **A short cover email** that states what you are asking for in the first sentence.

## How to use this repo

1. Read `METHOD.md` — ten minutes; it is the part that matters most.
2. Open an AI assistant that can work with your files, and walk through
   `prompts/00-START-HERE.md`. The prompts are numbered in working order; each one
   produces a concrete artifact and tells the assistant what rules to enforce.
3. When you are ready to share evidence with the manufacturer, use `site/` and
   `prompts/06` to put the record online behind a password.

You do not need to be technical. The prompts are written so the assistant does the
technical work and you make the decisions only you can make.

## What this is not

This is not legal advice, and no file in this repo is a substitute for a lawyer.
Lemon-law and consumer-protection standards differ by state and country; deadlines are
real; some situations (crashes, injuries, fraud) need counsel immediately. What this
repo automates is the part lawyers and manufacturers both respect regardless of venue:
a complete, honest, verifiable record.

## Principles (the short version)

The record argues by existing. State facts; never argue law in the record itself.
Every number is verified against a source at build time. A screenshot proves only what
is visible in it. Quote documents verbatim. Leave out weak evidence — and never omit
something whose absence would make you look dishonest. The full doctrine is in
`METHOD.md`.

## License

Apache-2.0. Use it, adapt it, share it.
