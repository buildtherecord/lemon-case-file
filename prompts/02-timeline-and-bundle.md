# Prompt 02 — Timeline and the bundle

---

From the approved inventory (prompt 01), build a single JSON file — the bundle —
that every later artifact will be generated from. Use the shape in
`schema/bundle.schema.json` (adapt fields as needed, but keep: a `timeline` of dated
events, `video`/`photos` catalogues with problem tags, a `componentLedger`, and any
out-of-service stays with start/end dates).

Rules:
- Every entry carries its source: the file it came from, or the document that
  states it. An event with no source does not go in.
- Purchase, each defect report, each repair visit (arrival and pickup dates), each
  recall (federal filing date, the date any stop-sale or "no repair available"
  notice reached dealers, the date the fix reached this vehicle), each manufacturer
  contact, each written communication.
- Compute and store durations (days out of service, days from recall filing to
  repair availability) as code, not as typed numbers. Where a long stay splits into
  "waiting for a remedy to exist" vs. "in repair", compute both parts.
- Anything I told you from memory goes in a `scopeReviewQueue`, not the timeline,
  until a source is found.
- Cross-check dates: an RO's printed dates beat a filename, which beats memory.
  Record conflicts in the entry rather than silently choosing.
- Sanity assertions at the end: no event before purchase; no repair pickup before
  drop-off; every media item's problem tag is one of the declared categories; every
  timeline driveId/file reference resolves.

Then print me: total events by type, total captures by problem, the five longest
out-of-service spans, and everything in the review queue.

---

## Checklist for you afterward

- Read the review queue completely. Approve, source, or delete each item.
- Verify the out-of-service math against your own calendar memory once — then trust
  the bundle, not your memory, forever after.
