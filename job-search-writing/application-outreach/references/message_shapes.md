# Worksheet and message shapes

Reference for `application-outreach` Steps 4–5.

---

## 1 · The worksheet (Approval 1)

One block per recommended recipient. Fill everything that research can fill. The user confirms or swaps the lines marked ◆. Add a HOOK line only for a fact the user confirms that isn't in the ledger (for example, having used the company's product); it is passed to the validator with `--hooks`.

```
ROLE          <Company> · <Role> · status: <not_applied | applied M/D | in_process>
RECIPIENT     <Name> · <Title> · <type> · involvement: <Confirmed|Likely|Possible> (<evidence>)
CHANNEL       <email to address (Confirmed|Verified: evidence) | LinkedIn connect ≤N chars | reply on thread> 
◆ PROBLEM     [STATED|INFERRED] <one problem from jd-five-problems, ≤20 words> — "<JD quote>" if stated
◆ PROOF       <claim ID> · "<exact ledger wording or a faithful compression>" · fit: <direct|adjacent>
              must keep: <scope / qualifiers / attribution from the ledger>
◆ ANGLE       A: <recommended, one line>   B: <alternative, one line, or "none">
◆ ASK         <conversation | pointer to hiring manager | confirm recruiter | perspective | referral>
◆ HOOK        (optional) <a fact the user confirms that isn't in the ledger>
```

Rules:

- One problem. Show the second-ranked pairing only as angle B, and only if it is genuinely different.
- **STATED** means the JD says it (quote it). **INFERRED** means `jd-five-problems` reasoned it, and the message must frame it as a guess ("My guess is…", "From the posting, it looks like…").
- **fit: adjacent** means the evidence is analogous rather than the same problem. The message must not present it as direct experience.
- No proof line for a recruiter note or a routing note unless it carries a single qualification phrase.

---

## 2 · What changes by recipient and status

| Recipient | Problem | Proof | Angle | Ask |
|---|---|---|---|---|
| **Hiring manager** | The one they own, in their language | One ledger claim, with its figure only if it survives the qualifiers | Why this problem is the hard part, and what the user did about a version of it | A short conversation, in first person |
| **Functional leader** | The business outcome above the role | One claim at business altitude | Connect the role to the outcome | A conversation, or a pointer to the hiring manager |
| **Recruiter** | Usually none, or a single phrase | One qualification phrase at most | Make the user easy to place: role, date applied, fit in one line | "Are you the recruiter on it?" or confirming the req is live |
| **Peer** | A shared craft question, never a pitch | Optional, light | Curiosity about how the team works | Perspective, or a pointer to the hiring manager. Never ask a peer for the job. |
| **Warm path** | Why the role fits | Optional | The relationship comes first | A referral or an introduction, asked plainly |

| Status | Changes |
|---|---|
| **not_applied** | Never say "I applied." Lead with interest in the role or the problem. The ask can be perspective, a pointer, or (warm path only) a referral before applying. No résumé attachment unless the user chooses one. |
| **applied** | Name the role and date once. Ask for a conversation or a pointer. Attach the résumé that was sent, if email. |
| **in_process** | Outreach to the hiring manager or peers is optional and light. It must not go around the recruiter. Usually no outreach; prepare for the interview instead. |

---

## 3 · Channel shapes

**LinkedIn connection note** (`linkedin_note`). Hard maximum 300 characters, or the account limit. One block of text; paragraph breaks are lost.

- Greeting with first name.
- One line of context: the role, and "applied" only if true.
- One specific line: the problem, a hook, or a qualification.
- A first-person close ("I'd like to connect"). Questions are optional.

**LinkedIn message after acceptance** (`linkedin_message`). About 90 words or fewer. Thank them in a few words, give the angle and the proof, then the ask. Don't repeat the note.

**Email, first contact** (`email`). About 150 words or fewer, usually 90–130.

- Subject: the role title, plain.
- Paragraph 1: role and status (one or two sentences).
- Paragraph 2: the problem, stated or framed as a guess.
- Paragraph 3: the proof.
- Last line: the ask, in first person.
- Signature: name, phone, LinkedIn.

**Reply on an existing thread** (`email_reply`, `linkedin_reply`). About 60 words or fewer. Don't re-supply context the thread already holds.

**Follow-up.** One to three sentences that add one new thing, on the same thread.

---

## 4 · Patterns worth keeping, and patterns the validator blocks

Patterns that hold up:

- **Unconfirmed hiring manager, handled honestly:** "My guess is that it sits on your team, so I wanted to reach out directly." Later: "If the role sits on another team, a pointer to the right person would be just as helpful."
- **Recruiter routing:** "I applied for <Company>'s <Role> on <date>. … Could you tell me who the recruiter on it is?"
- **Product-experience hook:** a true, specific use of the company's product earns its line, once the user confirms it as a HOOK. Present it plainly.

Typical blocks (these come from real drafts, generalized):

| Pattern | Why it blocks |
|---|---|
| "measured against holdout groups" on a claim recorded as platform attribution | Measured-impact language the claim doesn't support |
| "$150K+" when the ledger says $150K | Adds a "+" |
| "spot churn risk" for a program the ledger says is NOT a predictive churn-risk model | Echoes a ledger NOT-safeguard for that program |
| "we found that 90%…" for a finding the ledger credits to an analyst and marks unverified | Unverified finding stated as observed |
| "three enterprise upgrades" when the number lives only in an "ambiguous / deck-only" note | Figure from a flagged quantitative note |
| "I grew revenue 3x" when the ledger says "Never 'I grew it 3x'" | The ledger's own prohibited form |
| "At <employer> I launched X" with no claim or hook | Unsupported accomplishment |

Style findings ("Would you be open…", an em dash, a long email) are warnings with suggestions, never blocks.
