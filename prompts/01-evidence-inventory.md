# Prompt 01 — Evidence inventory

Paste to the assistant, then point it at your folders (photo library exports, cloud
drive, email, downloads):

---

Inventory every piece of potential evidence for my vehicle defect claim. Sources to
sweep: my photo/video exports, my documents folder, my email (search the dealer's
name, the manufacturer's name, "recall", "repair", "case #"), and any cloud folders
I give you access to.

For each item record: filename, capture/creation date and time (from metadata where
available — note when the date comes from metadata vs. filename vs. my memory), what
it shows (one factual sentence describing only what is visible/audible), which
problem it relates to, and a stable ID.

Rules:
- Byte-identical and near-duplicate captures: keep one, mark the rest as duplicates
  with a pointer to the kept item. Never delete originals.
- Grade honestly: does the capture demonstrate the defect, merely support context,
  or show nothing usable? I will cut the last group later — your job now is honest
  description, not selection.
- OCR every screenshot (call logs, chat transcripts, app screens) and record only
  the text actually legible in it.
- Videos: note duration, and whether the defect is visible/audible or only narrated.
- Flag items whose capture date conflicts with what they appear to show.
- Do not rename or move any original file. Output a manifest (CSV or JSON) I can
  review, with your duplicate/grade annotations.

Also build the paper side: every repair order (RO), invoice, recall letter,
technical service bulletin, dealer communication, and manufacturer letter. For each:
date, document type, the exact quote of any decisive line (e.g. their stated reason
for a repair, or "could not verify"), and where the original lives.

---

## Checklist for you afterward

- Did it find your earliest evidence? Owners usually have older material than they
  remember — carrier-app screenshots, listing-app rejections, texts to family. Say
  what you remember reporting and when; ask the assistant to hunt for corroboration.
- Review every "duplicate" call before accepting it.
- The manifest date column is the spine of everything later. Spot-check ten rows.
