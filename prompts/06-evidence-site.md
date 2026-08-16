# Prompt 06 — The evidence site

One self-contained HTML page (thumbnails inlined; videos and documents fetched from
the same protected origin), deployed behind the password gate in `site/`
(see `site/DEPLOY.md`).

---

Build the case homepage from the bundle. Structure, top to bottom:

1. **Banner** — what this is prepared for, with the case number.
2. **Abstract** — four to six sentences, academic-abstract style, visually
   distinct: the pattern of defects, the repair history in one line, the present
   state, and a final line stating plainly what I am asking for and the decision
   date if one is set. I will write or approve every word of this.
3. **The record** — a few paragraphs of dated fact in plain language. Where a term
   could be misread, define it in place (which screen, which part). Where we chose
   not to film or couldn't, say so. No legal vocabulary, no adjectives doing
   argument's work.
4. **Component ledger** — the table from prompt 03, expandable rows.
5. **Timeline strip** — horizontal swimlanes: recalls/bulletins as duration bars
   (filing date → fix available → fix performed, with tick marks for milestones in
   between), out-of-service stays as bars, calls as ticks, my reports and captures
   as ticks. Tooltips carry date/title; clicking opens a modal with the thumbnail,
   detail lines, and an "Open the full document" link.
6. **Exemplar players** — the strongest few videos per problem, grouped by problem,
   each captioned: title, date, and the one contextual fact that matters (e.g.
   "N days after <part> was replaced under <RO>"). Short and factual.
7. **Evidence grid** — every capture and every document as thumbnails with year
   markers, filterable by problem and by kind (car evidence vs. paper). Documents
   visually distinct from captures.
8. **Records-request block** — summary of prompt 05's request with download links.
9. **Download cards** — the case PDF and the records request.

Interaction rules learned the hard way:
- Every document opens ITS OWN full-resolution original (PDF/image) in a new tab —
  host the originals; never link a modal to some other summary page, and never
  make a reviewer squint at a 400px thumbnail.
- Videos: `preload="none"`, poster images, Range-friendly hosting (the worker in
  `site/` handles this) so scrubbing works.
- Every count shown on the page is computed from the bundle at build time, with
  assertions that fail the build on drift.
- Exhibit numbers (see `templates/exhibit-scheme.md`) appear in modals, grid
  captions, and document links, matching the PDF exactly.
- No analytics, no external CDNs, no third-party requests: everything served from
  the protected origin. The access log is the only telemetry.

Before I send anything: screenshot the rendered page (including an open modal and
a player) and show me.

---

## Checklist for you afterward

- Click ten random grid cells and two timeline ticks; confirm each opens the right
  full document.
- Read the abstract out loud. If any sentence sounds like a lawyer wrote it,
  rewrite it plainer.
