# Safety gates — information vs. legal advice

Reviewer finding (consumer-law review of v0): features that apply law to a claimant's own facts risk crossing from information into advice and, in most states, into unauthorized practice of law. This file is the gate every screen and export passes.

## The information/advice test (apply to every screen, template, and generated sentence)
A screen is **information** only if it: states law or policy as written, with its source; explains terms generally; lists routes and sources of help; organizes the claimant's own facts in their words. It becomes **advice** if it: applies law to the claimant's facts; says whether a deadline passed or a claim is strong; recommends a route; chooses or fills legal forms; drafts a letter that asserts legal rights. Anything in the second list needs an attorney in the loop or is removed.

## Gates
1. **State required before any date or path screen and before anything can be shared** (see decision-check.md). The first screen of the app is a capture and needs none.
2. **Unknown-deadline banner** on every date or path screen the claimant sees: the wizard and the inward record. The outward page is exempt (see the table).
3. **"Stopping doesn't stop the clock"** on every close or archive screen.
4. **Fee-shifting note** wherever cost is shown.
5. **Discovery and recording notice** before capture features: everything may be demanded; a pre-lawyer record is generally not privileged, and "held back" is not "privileged"; recording-consent rules vary; never delete.
6. **Share gate** before any export to a reviewer, journalist, or the public: confidentiality terms, naming of people and businesses, attorney review, defamation-risk reminder.
7. **Claimant-entered judgments:** deadline known, denial correct, evidence strength — entered by the claimant or a professional, never computed by the tool.
8. **Volunteer conduct policy:** coaches share information and sources, not advice; no case-specific legal opinions; no fee-taking; no promises.
9. **Data policy:** retention and deletion options; what is stored where; health-data handling; what happens on a subpoena; no sale or ad use.
10. **Comprehension check in testing:** "What does this tool not do?" must be answerable by testers, including ill, low-literacy, and non-English-speaking ones.

## Which gate applies where

There are two layers (see `two-layer-model.md`): the **outward page** that anyone may read, and the **inward record** for the claimant and the claimant's attorney. The **wizard** is the intake and editing app; it is not in this repository, so every wizard cell is a design, not a feature. Status words: **built**, **partial**, **planned**.

| Gate | Outward page | Inward record | Wizard |
|---|---|---|---|
| 1 State first | No. The page states what the documents say; nothing on it depends on the state. | Yes, partial. The brief shows the jurisdiction field ("not entered" if blank); the build does not stop without it. | Yes, planned. Asked right after the first capture, before anything can be shared. |
| 2 Unknown-deadline banner | No banner of its own. The page lists no deadlines and no routes and is read by people other than the claimant, so a banner written to the claimant would reach the wrong reader. Its footer says it is information, not legal advice (built). A footer link to a plain-language deadline notice is planned. | Yes, partial. On the brief and the gaps page; the chronology, exhibits, people and issues pages do not carry it yet. | Yes, planned. On every date or path screen and on the share gate. |
| 3 Stopping doesn't stop the clock | No. It has no close or archive screen. | No for now. Static pages have no close or archive action. The archive export, when built, repeats the line on its cover. | Yes, planned. Every close, pause or archive screen. |
| 4 Fee-shifting note | No. It shows no cost of any route; the amount asked for is the claimant's own words. | No for now. The brief shows the amount as claimant-reported and no route costs. If route costs are ever shown, the note goes with them. | Yes, planned. Wherever routes or their costs are listed. |
| 5 Discovery and recording notice | No. It captures nothing. | No. It is generated from what was already captured. | Yes, planned. Before any capture feature, including that a pre-lawyer record is generally not privileged. |
| 6 Share gate | Yes, planned. This is the page the gate protects: nothing is sent without it. Nothing asks the questions yet. | No. It is never sent to anyone but the claimant and counsel. If someone else needs to see something, release it to the outward page, through the gate. | Yes, planned. It asks the questions and keeps the answers with the sent copy. |
| 7 Claimant-entered judgments | Yes, built by omission. No deadline, strength or correctness judgment is rendered. The status labels are the claimant's own: shows in a document, claimant's account, disputed. | Yes, built. A deadline needs a source and shows "nobody yet" until someone confirms it; a deadline marked computed fails the build; advice-like phrases fail the build. | Yes, planned. Entry fields ask "where is this written?" and "who told you?" |
| 8 Volunteer conduct policy | No. It is a rule for people, not pages. | No. Same. | Yes, planned, for any volunteer who helps a claimant use it: information and sources, not advice. |
| 9 Data policy | Yes, planned. Say where the published copy is hosted and for how long; a copy that was sent cannot be recalled. | Yes, partial. The builders write local files and upload nothing. Retention and deletion options are planned; closing never deletes. | Yes, planned. Retention, storage, health data, subpoena, no sale or ad use. |
| 10 Comprehension check | Yes, in testing. A reader can say the page argues nothing and is not legal advice. | Yes, in testing. Counsel can say what the brief does not do: it judges no strength and computes no deadline. | Yes, in testing. "What does this tool not do?" (`test-plan.md`, pass signal 4). |
| 11 A record that accuses a named person | Yes, built. A record marked `meta.outward: false` has no outward page; `build_home.py` refuses it. Characterizations listed in `meta.banned` fail the build. | Yes, built. The Money page places transactions against an authority's dates by date alone and says it does not decide whether one was allowed; the brief shows whose claim it is, unconfirmed until someone confirms it. | Yes, planned. Asked at intake ("does this record accuse a named person?"), with a reminder that family members can be on different sides. |

## Privilege, plainly
Privilege protects attorney-client communications and attorney work product, not facts or documents that already exist. A record built before hiring a lawyer is generally not privileged. "Held back" means not released yet; it is not "privileged." A counsel-only space exists only once an attorney is involved and directs the work, and no screen implies more than that.

## Open items for a licensed attorney (per state)
- Review of the information/advice line and non-lawyer document-preparer rules.
- Review of the "where to get advice" source list (lead-generation sites excluded).
- Review of the retaliation and recording notices.
- Whether the outward page should carry a link to a deadline notice, where that notice should live, and its exact wording.
