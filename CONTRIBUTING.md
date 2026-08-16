# Contributing

This repo exists so the next owner doesn't start from zero. The most valuable
contributions come from people who have actually run the method.

## What helps most

- **Prompt improvements from real use.** If a prompt produced something weak and you
  fixed it, PR the fix with one sentence on what went wrong. Keep the discipline
  rules intact — PRs that soften the evidence rules (source-or-it-doesn't-enter,
  verbatim quotes, no padded counts) will be declined.
- **Jurisdiction notes.** Short files under `jurisdictions/` (e.g. `us-ca.md`,
  `us-il.md`, `de.md`): the statute name, the repurchase standard in one paragraph,
  deadlines, the arbitration body, and any quirk of the mileage-offset formula.
  Cite the statute; no legal advice, just signposts.
- **Manufacturer notes.** What the diagnostic system is called (ODIS, Techstream,
  PIWIS, …), what records they retain, what worked in a request.
- **Anonymized outcomes.** A short writeup of how the method held up — what the
  reviewer engaged with, what they ignored. Strip every identifying detail; see
  `prompts/09` for the scope-B checklist. Do not include settlement terms if you
  agreed to keep them confidential.
- **Accessibility and translation.** Plain-language rewrites and translations of
  the prompts.

## What we won't take

- Real case documents, even redacted, even yours — this repo stays 100% synthetic.
- Content attacking a specific manufacturer. The method's power is that it doesn't
  editorialize.
- Anything that turns prompts into legal argument templates. The record states
  facts; the cover email names the standard once. That's the design.

## Mechanics

Fork, branch, PR. Keep files in the existing voice: short, concrete, no hype.
For demo-site changes, include a screenshot. By contributing you license your
contribution under Apache-2.0.
