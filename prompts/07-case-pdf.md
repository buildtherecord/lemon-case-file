# Prompt 07 — The case-file PDF

The website is for review; the PDF is the record that gets attached, forwarded, and
filed. Same bundle, same numbers, same exhibit labels — different medium.

---

Generate the printable case file from the bundle:

1. Title page/header: vehicle, VIN, case numbers, "prepared for <review>", date.
2. The component ledger on page 1 — a reviewer who reads only one page should hit
   the repair history, their own stated bases, and the recurrence column.
3. The chronological record: every timeline event, dated, each with its exhibit
   number, decisive quotes verbatim.
4. Per-problem sections mirroring the site's grouping.
5. Exhibit index appendix: every exhibit number → date → one-line description, in
   order, with class totals.

Rules:
- Exhibit numbers assigned deterministically (see `templates/exhibit-scheme.md`)
  by code shared with the site build, so the two can never diverge.
- Every computed number asserted at build. Filename includes the month and year.
- Keep it under ~35 pages; the media catalogue is a listing here, not embedded
  images (the site and full-resolution originals carry the media).
- Render via headless browser to PDF; merge the appendix programmatically; verify
  page count and spot-read pages 1, 2, and the appendix before delivering to me.

---

## Checklist for you afterward

- Print page 1. If the ledger doesn't fit or doesn't land the recurrence story,
  fix that before anything else.
- Check three exhibit numbers against the site's modals — they must match.
