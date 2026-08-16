# Prompt 03 — Component repair ledger

---

From the repair orders in the bundle, build the component ledger: one row per
part/system the manufacturer's dealers touched.

Each row: date range and RO number · component · what was done (replaced /
reprogrammed / reset / inspected) · the dealer's or manufacturer's OWN stated basis,
quoted verbatim from the RO ("internal malfunction", "concern verified, fault codes
stored", "could not verify", "working as designed") · odometer · and the recurrence
column: did the same symptom recur after this work, with the date and catalogue ID
of the recurring capture.

Rules:
- The stated-basis quote must come off the RO text. If the RO is a photo, OCR it
  and verify the quote against the image before using it.
- Recurrence links must point to a specific dated capture or report in the bundle —
  "it kept happening" is not a ledger entry.
- Order rows so the story is visible: repeated work on the same component adjacent.
- Compute the headline sentence from the ledger (e.g. "N repairs to electrical
  systems across M visits since <date>; K of N in the last year") with a build-time
  assertion, and flag if the honest computation is weaker than what I've been
  saying — I need to know that before the other side tells me.

---

## Why this artifact matters most

Repurchase standards everywhere turn on some version of: reported early, repaired
repeatedly, recurred anyway. The ledger is that argument as a table, made entirely
of the manufacturer's own paper. Put it on page 1 of the PDF and near the top of
the site.
