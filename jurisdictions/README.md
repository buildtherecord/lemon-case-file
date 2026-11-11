<!-- DRAFT: needs licensed-attorney review before publishing -->
# Jurisdiction notes

The method in this repo is jurisdiction-neutral. The law that decides your case is
not. This directory holds per-jurisdiction signpost files so that you — and the AI
assistant working your prompts — start from a map instead of from zero.

## What these files are, and are not

Each file is a set of **dated, cited signposts**: the statute names, the bodies,
the thresholds, where the deadline *rules* are written — each with a source link
and a `last_verified` date. They are contributions from people who ran the method in
that jurisdiction. They are **not legal advice and not current law**.

## The staleness rule (non-negotiable)

Laws change; repo files rot. Every entry here is a **lead, never a fact to rely
on**. Re-verifying a rule is for a person who can confirm it, not for this
directory or an assistant:

- For any deadline, threshold, or notice rule an entry mentions, the assistant
  shows you the primary source's own words (the statute, the agency's page, the
  warranty booklet), quoted exactly, with the citation and the date it read them,
  marked "not confirmed by anyone yet". It does not calculate or confirm anything,
  and it does not compare today's date against any rule. Whoever re-verifies a
  rule starts from the source's current text, not from this file.
- Who can confirm: legal aid, a courthouse self-help center, a lawyer (your state
  bar's referral service can point you to one).
- Entries whose `last_verified` is more than 12 months old should be treated as
  historical hints only.
- **No deadline is ever taken from this directory.** A signpost tells you that a
  rule exists and where it is written; this file does not set, count, or confirm
  anyone's date.
- Deadlines may apply that you and this tool don't know about. Stopping or waiting
  does not stop a deadline and may give up rights. Ask someone who can advise you
  about your situation.

## Contributing a jurisdiction file

Copy `TEMPLATE.md`, fill in what you verified (leave blank what you didn't —
a partial file with real citations beats a complete file with guesses), set
`last_verified` to the date you checked the sources, and open a PR. Run
`python3 tools/validate_jurisdictions.py` first. Cite primary sources
(statutes, courts, regulators) wherever possible; mark secondary sources as such.
