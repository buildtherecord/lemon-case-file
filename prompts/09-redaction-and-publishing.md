# Prompt 09 — Redaction and publishing scope

Two different audiences, two different scopes. Decide which one each artifact is
for BEFORE building it, and never promote a manufacturer-scoped artifact to public
without re-scrubbing.

## Scope A — for the manufacturer (password-gated site)

They already know who you are. Redact anyway anything a leaked copy shouldn't
carry: financial account numbers, date of birth, driver's license, signatures if
feasible. Purchase agreements: redact last names, street address, phone numbers,
email, DOB — keep the deal terms, dates, VIN, and dealer visible.

## Scope B — public or media

Everything in Scope A, plus: no VIN, no case numbers, no employee names, no
family names, no address fragments, no license plates in frames, no voices in
audio you haven't cleared, no EXIF GPS in any image.

---

Prompt:

Redact <document> for scope <A|B>. Method: rasterize each page, draw opaque boxes,
rebuild the PDF from the rasters — never rely on PDF annotation layers, which can
be lifted. After redacting, render every page back to me as images at readable
zoom over each boxed region so I can verify no partial characters leak at the box
edges. List every field you covered and every field you deliberately left visible,
and wait for my approval before the file goes anywhere.

Also sweep the whole publishable set: grep every HTML/PDF/CSV output for my last
names, address, phone numbers, email, account numbers, and (for scope B) VIN and
case numbers, and strip EXIF from every image. Report matches before fixing.

---

## Publishing the method itself

If you plan to share your template/method publicly (like this repo): publish
BEFORE signing any settlement, keep it 100% generic, and don't link it from the
case site or the case site from it. Whether to attach your name is a real choice —
credibility versus permanence — and it is yours, not the assistant's.
