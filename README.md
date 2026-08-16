# lemon-case-file

**A method, a set of AI prompts, and a small amount of free infrastructure for a
vehicle owner to build a professional-grade defect case file** — the kind of
evidence presentation a manufacturer's repurchase reviewer, an arbitrator, or an
attorney takes seriously — without hiring anyone.

It was developed during a real, self-represented lemon-law repurchase claim,
working with an AI assistant (Claude) as the builder. Everything case-specific has
been removed; what remains is the process that made the record persuasive.

**See what you end up with:** the [demo case file](https://buildtherecord.org/lemon-case-file/)
— a fully fictional exemplar (every name, document, and image invented; fact
pattern modeled on published appellate opinions — see [`EXEMPLARS.md`](EXEMPLARS.md)).

## What you end up with

- **A single source-of-truth catalogue** of every incident you recorded, every
  repair order, every recall and technical bulletin, every call and email — dated,
  verified, deduplicated.
- **A password-protected evidence website** (free Cloudflare tier) with a
  plain-language narrative, an interactive timeline, a filterable evidence grid,
  and playable video exemplars — plus an access log so you can see when the
  manufacturer actually reviews it.
- **A printable case-file PDF** with a component repair ledger, chronological
  record, and a numbered exhibit index.
- **A diagnostic-records request** organized per demonstrated problem, so the
  manufacturer's own telemetry has to answer your timestamps.
- **A short cover email** that states what you are asking for in the first sentence.

## How to use it

1. Get a copy: `git clone` this repo, or use GitHub's **Code → Download ZIP**
   button (no git required).
2. Read [`METHOD.md`](METHOD.md) — ten minutes; it is the part that matters most.
3. Open an AI assistant that can work with your files, and walk through
   [`prompts/00-START-HERE.md`](prompts/00-START-HERE.md). The prompts are numbered
   in working order; each produces a concrete artifact and tells the assistant what
   rules to enforce. You do not need to be technical — the assistant does the
   technical work; you make the decisions only you can make.
4. When you're ready to share evidence with the manufacturer, deploy the
   password-gated site with [`site/DEPLOY.md`](site/DEPLOY.md).
5. Before anything is sent anywhere: run the adversarial pass
   ([`prompts/08`](prompts/08-adversarial-review.md)). It is the highest
   value-per-hour step in the method.

## Repository map

| Path | What it is |
|------|-----------|
| `METHOD.md` | The doctrine — evidence discipline, "the record argues by existing" |
| `prompts/00–10` | Working-order prompts: inventory → bundle → ledger → phone log → records request → site → PDF → adversarial review → redaction → cover email |
| `site/` | Cloudflare Worker evidence viewer + deploy runbook (free tier) |
| `schema/` | The bundle (source-of-truth JSON) schema + fictional example |
| `templates/` | Exhibit numbering scheme, repurchase finance worksheet |
| `docs/` | The fictional demo case file (GitHub Pages) |
| `EXEMPLARS.md` | Real published opinions worth reading, and why the demo is fictional |

## Contributing back

If you run the method — win, lose, or settle — the next owner benefits from what
you learned. Prompt fixes from real use, jurisdiction notes, manufacturer
diagnostic-system notes, and anonymized outcome writeups are all welcome; real
case documents are not (this repo stays 100% synthetic). See
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## What this is not

This is not legal advice, and no file in this repo is a substitute for a lawyer.
Lemon-law and consumer-protection standards differ by state and country; deadlines
are real; some situations (crashes, injuries, fraud) need counsel immediately.
What this repo automates is the part lawyers and manufacturers both respect
regardless of venue: a complete, honest, verifiable record.

## Principles (the short version)

The record argues by existing. State facts; never argue law in the record itself.
Every number is verified against a source at build time. A screenshot proves only
what is visible in it. Quote documents verbatim. Leave out weak evidence — and
never omit something whose absence would make you look dishonest. The full
doctrine is in [`METHOD.md`](METHOD.md).

## License

Apache-2.0. Use it, adapt it, share it.
