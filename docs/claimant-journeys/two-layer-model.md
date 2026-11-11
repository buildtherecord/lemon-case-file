# Two layers: outward and inward

Status: draft. Not legal advice. Status words used here: **built** (code in this repo does it today), **partial** (some of it does), **planned** (a design, nothing builds it yet).

One person's dispute becomes **one record**. The record is published two ways, and there is no third way.

| | **Outward** | **Inward** |
|---|---|---|
| What it is | The page you could hand to anyone: the other side, a reviewer, a mediator, a journalist, a relative | The full linked record, plus material meant only for counsel |
| Who may see it | Anyone you give it to. Write it as if everyone will read it | You, and your attorney (including staff working for your attorney's office) |
| What is on it | Only what you released: dated entries and the documents marked shareable, scrubbed of private details. It states what the documents say and argues nothing | Every fact, document, person and topic in the record, linked both ways; the brief for intake; the gaps; deadlines you entered, each with where it is written |
| How it looks | Public, light, phone-first. "Last updated" and a snapshot id at the top | Complete and linked. "Last updated" at the top. Maintained deliberately: changes are made on purpose, and nothing is deleted |
| Built by | `tools/views/build_home.py` | `tools/views/build_views.py` |

## What is generated from what

```
the record (one file) --> outward page    only what was released
                      --> inward record   everything in the record that renders
counsel-only material: written in the inward layer, not generated from the record, never feeds the outward page
```

- Counsel-only material exists only once an attorney is involved and directs the work. The attorney decides what goes in it. How it is stored so that the claimant's tools cannot read or leak it is an open question (**planned**).
- Items marked `held_back` stay in the record file. Neither builder renders them.
- Nothing moves from inward to outward except by being released. Deadlines, the lawyer field and strategy notes never render on the outward page (**built**).

## What "released" means

Two switches, per item: the fact (`outward`) and its document (`share`). A document with other people's information, health data, financial identifiers or a full message export should start as not shared, with a masking step offered. Today the builder shows an item unless it is switched off; making release opt-in is **planned**. Scrubbing private details happens before release (`prompts/09-redaction-and-publishing.md`); a build-time check for what a scrub missed is **planned**.

## No layer in between

There is no page for family or for people you trust. Anything family should see goes on the outward page. A page meant only for people you trust can still be forwarded, and it is still not privileged, so it would be one more place for a private detail to leak. If someone needs to see something, release it, and it goes through the share gate like everything else.

## The share gate

Before an outward page is sent, the claimant answers: who is receiving it; whether settlement or confidentiality terms exist; whether it names people or businesses beyond what the documents say; whether an attorney has read it. Defamation and confidentiality reminders appear at that point, not buried in help (**planned**; nothing asks these questions yet).

## The snapshot (sent copy)

The record keeps changing. What you sent must not. Each send saves a dated copy of the outward page with an id computed from its content, so you can show exactly what left your hands and to whom. Today the builder computes the id and writes `snapshot.json` (**partial**); it clears the output folder on each build, and saving each sent copy with its recipient is **planned**.

## Privilege, plainly

Privilege protects attorney-client communications and attorney work product. It does not protect facts or documents that already exist. A record built before you hire a lawyer is generally not privileged. "Held back" means not released yet; it is not "privileged." A counsel-only space exists once an attorney directs the work, and the tools never imply more than that.

## Where the rest is written

`intake-and-ux.md` (what changes in the wizard and the screens), `safety-gates.md` (the ten gates and which layer each applies to), `decision-check.md`, `scenarios.md`.
