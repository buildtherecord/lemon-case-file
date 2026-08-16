# Jurisdiction notes

The method in this repo is jurisdiction-neutral. The law that decides your case is
not. This directory holds per-jurisdiction signpost files so that you — and the AI
assistant working your prompts — start from a map instead of from zero.

## What these files are, and are not

Each file is a set of **dated, cited signposts**: the statute names, the bodies,
the thresholds, the deadline *rules* — each with a source link and a
`last_verified` date. They are contributions from people who ran the method in
that jurisdiction. They are **not legal advice and not current law**.

## The staleness rule (non-negotiable)

Laws change; repo files rot. Every entry here is a **lead to re-verify, never a
fact to rely on**:

- The assistant must re-verify every deadline, threshold, and notice requirement
  against the primary source (the statute, the regulator's page, the plan
  document) **at the time of use**, before it appears in anything you send or file.
- Entries whose `last_verified` is more than 12 months old should be treated as
  historical hints only.
- **No deadline is ever taken from this directory.** A signpost tells you a clock
  exists and where its rule lives; the current rule text sets the date.

## Contributing a jurisdiction file

Copy `TEMPLATE.md`, fill in what you verified (leave blank what you didn't —
a partial file with real citations beats a complete file with guesses), set
`last_verified` to the date you checked the sources, and open a PR. Run
`python3 tools/validate_jurisdictions.py` first. Cite primary sources
(statutes, courts, regulators) wherever possible; mark secondary sources as such.
