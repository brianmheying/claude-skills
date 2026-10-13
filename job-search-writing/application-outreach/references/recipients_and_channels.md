# Recipients, contact verification and channel rules

Reference for `application-outreach` Steps 1–3. The settings named here live in `../config.template.json` (overridden by the private local config).

---

## 1 · Recipient candidates

### Recipient types

| Type | Who | What they can do for the user |
|---|---|---|
| **Hiring manager** | Owns the req; the role reports to them | Pull the application forward, take a conversation |
| **Functional leader** | Leads the function above or beside the hiring manager (VP, CMO, CCO) | Route to the hiring manager, signal interest internally |
| **Recruiter** | Talent partner on the req, or the function's recruiter | Move the application to a screen, confirm the req is live |
| **Peer** | Would work alongside the role (same team, current lifecycle lead) | Point to the hiring manager, give perspective, sometimes refer |
| **Other stakeholder** | Partner function the role serves (CS, Sales, Product, BDR lead) | Perspective; rarely the first contact |
| **Warm path** | 1st-degree connection or referrer at the company | Referral or an introduction; outranks cold contact when the person is relevant |

### Hiring-involvement tiers

| Tier | Evidence required |
|---|---|
| **Confirmed** | Named as the reporting line in the JD; posted that they are hiring this role; or a recruiter or company email names them as hiring manager or recruiter on this req |
| **Likely** | Title and team match the reporting line or function the JD describes, with no contrary evidence. For example, "Reports to the VP of Digital & Growth" and the person holds that title. |
| **Possible** | Functionally relevant only (the right department, a plausible level), with nothing tying them to the req |

State the tier and the evidence in one line, with a source: JD text, URL, post, email, or LinkedIn profile seen on a date. Do not upgrade "Likely" to "Confirmed" because it makes the message easier to write. When the hiring manager is unknown, say so; the message then asks for a pointer.

### Ranking

1. Involvement tier (Confirmed > Likely > Possible).
2. Functional relevance to the selected problem.
3. Warm path, as a tie-breaker that can lift a peer or stakeholder above a cold Possible.

Reachability is **not** a ranking factor (hard rule 4). It is decided in §3, after the ranking is fixed.

### Research sources, in order

1. **Thread context:** JD, Career OS notes, earlier research in this conversation.
2. **Local history:** `prior-contact --company`, `warm-paths --company`, `04_Output/Outreach_Queue_*.md`.
3. **Gmail:** `from:@domain OR to:@domain` for prior threads, recruiter notes, application confirmations.
4. **Public web:** company team and leadership pages, press releases, conference speaker pages, the person's own posts.
5. **LinkedIn in the user's browser,** when available. Viewing a profile shows up under the user's name in that person's "who viewed your profile" list. That is acceptable for recommended recipients only; don't browse broadly.

Confirm current employment for every recommended recipient. The LinkedIn export is dated (see `_export_date`), and people move.

---

## 2 · Contact research and email confidence

| Class | Evidence that qualifies | Sendable? |
|---|---|---|
| **Confirmed** | (a) The person has emailed the user from the address (an email search shows it). (b) The address appears on their record in the LinkedIn connections export (they shared it as a 1st-degree connection). (c) The person published it: their own site, company page, press release with contact, speaker or author bio, public filing, GitHub commit email on the company domain | Yes |
| **Verified** | An independent email-verification tool (for example Clay, Hunter, NeverBounce or ZeroBounce) returned **valid/deliverable**, on a domain that is **not** catch-all/accept-all, and the user has seen that result (pasted it, or Claude read it in the user's browser). Record the tool and date | Yes |
| **Pattern-only** | Built from the company's address format, however common the format (for example "first.last at 92%") | **No** |
| **Risky / accept-all / unknown** | A verifier returned risky, unknown or accept-all | **No** |
| **Not found** | Nothing above | — |

Rules:

- Claude cannot run deliverability checks from its own workspace. Verification requires the user's tool, run by the user or by Claude in the user's browser.
- A bounce downgrades the address permanently. Record it.
- Personal emails (Gmail and similar) are not professional addresses and are not used unless the person gave it to the user for this purpose.
- Present the evidence: "Confirmed: emailed you 2026-02-12 (thread '<subject>')", not just "high confidence."

---

## 3 · Channel decision

Apply in order, per recipient:

1. **Existing conversation.** A live email thread or LinkedIn conversation exists. Reply there (`email_reply` or `linkedin_reply`). Do not open a second channel.
2. **Already contacted on another channel.** If the follow-up window is still open, wait. A switch is allowed only after the first channel and its one follow-up have gone `channel_switch_after_business_days` business days without reply, and that switch is the final touch to that person.
3. **Email is Confirmed or Verified.** Use email.
4. **1st-degree connection, no email.** Send a LinkedIn message (`linkedin_message`).
5. **2nd- or 3rd-degree, Connect available** (including under More). Send a connection request (`linkedin_note`), within the note limit.
6. **None of the above.** No approved channel. Report it. The next-ranked recipient may be recommended separately and labelled as a substitute.

InMail is used only when `linkedin.inmail_allowed` is true.

### Concurrency and sequencing

- At most `max_concurrent_recipients_per_company` people at one company at once, each on one channel.
- A third person only after both earlier recipients have gone quiet past their follow-up window.
- Contacting a recruiter and a hiring manager the same day is allowed (they are different people). Avoid sending each the same text.
- Pre-application: if a warm path exists, recommend asking that person first, because referral credit usually has to come before submission. The user decides whether to hold the application.

### Follow-ups

- One per person, 5–7 business days after the first touch, only if it adds something new: a relevant observation, a referral, a changed status. "Just checking in" does not qualify.
- Email: reply on the same thread.
- LinkedIn connection request: no follow-up until accepted. After acceptance, the first message is the follow-through, not a follow-up.
- After the follow-up, stop. A reply that routes elsewhere ends outreach to that person; thank them in one line.
- A rejection ends outreach for that req. A short thank-you to a hiring manager the user spoke with is optional and contains no pitch.
