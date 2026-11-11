# Prompt 01b — Evidence triage

Run after 01 (inventory) and before 02 (bundle). It turns the inventory into a graded,
de-duplicated, owner-confirmed catalogue, and leaves you with a watch list you keep using
as new questions come up. The doctrine is `METHOD.md` section 2a; the tools are in
`tools/triage/`.

Paste to the assistant, then point it at the inventory and the video folder:

---

Triage my evidence catalogue. Grade every item with the rubric in METHOD.md 2a:
A shown on camera, B1 supporting-described, B2 supporting-context, C weaker.

1. **Make the material reviewable.** Run `tools/triage/proxy_clips.py` for small review
   copies and `tools/triage/contact_sheets.py` for dense frame grids. Never touch an
   original. Report any clip that is unreadable (note it; do not drop it).
2. **Propose a grade and a one-line reason for every item.** In each reason, separate what
   is visible in the frames from what is only narrated or inferred. Do not grade anything
   whose grade depends on movement or sound from stills. Put it on the watch list instead
   and say which it is, so I know what to look for.
3. **Find duplicates by footage.** Run `tools/triage/dupcheck.py` and list every
   same-footage and very-similar pair. Propose; do not fold anything until I agree. A retake
   is not a duplicate.
4. **Build the queue.** Write `review-queue.csv`: only what stills could not settle, anything
   you are unsure of, and anything flagged. One question per item and where to look
   (seconds if you know). Order it by how likely each item is to change grade. Then run
   `tools/triage/make_watchlist.py` and tell me how to open it and send the answers back.
5. **Flag, do not decide.** List faces, plates, third-party names, birth dates, employer
   material, anything that may fall inside a release or settlement, and timestamps that
   conflict with the footage. These go to my decisions queue; anything about legal scope
   goes to my lawyer, not to you.
6. **When my answers come back,** run `tools/triage/apply_answers.py`, show me the changes and
   the counts, and ask before changing anything my answers did not cover. Count each piece of
   evidence once; excerpts are never counted; folded items are hidden, never deleted.
7. **Learn from the answers.** If an item you graded low turned out to be top-grade (or the
   reverse), find the items like it and add them to the queue.
8. **Captions.** Draft them from my own words, lightly edited. Keep every direct quote and run
   `tools/triage/quotecheck.py`. Attribute on-screen text to the screen, not to me. Ask me how a
   control is physically operated before you describe it. No grading remarks or advocacy.
9. **Show the strongest first.** When the site is built, the first view shows the A recordings
   with the counts of every other grade one click away; featured exemplars must be A.
10. **Record every ruling** I make in the decisions file.

---

## Checklist for you afterward

- Watch the clips on the list. You are the only one who has seen the car; a clip that looks
  like nothing in stills may be your best evidence, and the reverse.
- Answer "same footage" only when you have seen it is. Similar is not the same.
- Read every caption before it is published. Your quotes should still be in it.
- Look at the counts the tool prints. Each should match what you would count by hand.
- Keep the watch list. When something new turns up, it joins the list.
