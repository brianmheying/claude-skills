---
name: Application Outreach
description: Find the right people for a pursued role, pick email or LinkedIn under hard rules, and draft ledger-verified outreach for approval. Runs in parallel with application prep; never sends.
---

# Application Outreach

## Purpose

Turn a role worth pursuing into a conversation with a person who can move it.

Outreach is a parallel path, not a downstream step. It starts once the user has decided a role is worth pursuing and `jd-five-problems` has run. It may happen before, during or after the application. It never requires a tailored résumé, a Resume Adjudicator verdict or a cover letter.

The skill researches recipients, verifies contact information, recommends one recipient and channel per person under hard rules, and presents a small worksheet for approval. Only after approval does it draft. Every draft is validated before the user sees it. Nothing is ever sent by Claude.

## Two locations: this skill, and the user's data

**This skill folder** holds the instructions, references, validator and tests. It contains no personal data.

```
SKILL.md                          this file
README.md
config.template.json              defaults (no personal data)
config.local.json                 optional, private overrides (never published)
references/recipients_and_channels.md
references/message_shapes.md
scripts/outreach_tools.py         lookups + validator (Python 3, standard library)
scripts/package_skill.py          builds and verifies the installable zip
tests/run_cases.py                regression runner
tests/cases_synthetic.json        synthetic cases (fictional data)
tests/fixtures/test_ledger.csv    synthetic ledger
```

**The Career OS data folder** is the source of truth for the claim ledger, application history and outreach records. The skill reads it and never edits historical records. Paths inside it are set in `config.template.json` under `paths`.

## Reaching Career OS (do this first)

Run `python3 <this skill>/scripts/outreach_tools.py where` before Step 1. It reports the data folder it found, or exactly where it looked and why it failed.

Where the skill runs decides what it can reach:

| Where it's running | Can it reach Career OS? | What to do |
|---|---|---|
| **Installed in Claude, session linked to the user's computer** (device tools such as `device_stage_files` are available) | Not directly. Skills run in Claude's cloud sandbox, which can't see the computer's folders. | Stage a read-only snapshot of the files the run needs from the Career OS folder with `device_stage_files`: the claim ledger (always), plus the outreach log, the past outreach batches and the LinkedIn connections/messages exports when Steps 1–3 need them. They land under `/mnt/user-data/uploads/<Career OS folder name>/…` with their relative paths kept, and `where` discovers them. The snapshot lives only in this session. Re-stage if the ledger changes mid-session. Never copy any of it into the skill folder or a repository. |
| **Linked session with a device shell**, and this skill's source folder connected | Yes | Run the script through the device shell from the connected skill folder. Discovery checks connected folders under `~/mnt`. |
| **On the user's computer** (Terminal or Claude Code) | Yes | Discovery checks `~/Desktop` and `~/Documents`, or pass `--root` / set `CAREER_OS_DIR`. |
| **Installed in Claude, session not linked** | **No** | Say so plainly: "This session isn't linked to your computer, so I can't read the claim ledger." Steps 1–3 can run, but the worksheet marks every accomplishment `UNVERIFIED: ledger unavailable` and the skill stops there. Don't work around it. |

Discovery order: `--root`, then `$CAREER_OS_DIR`, then `career_os_dir` in a private config, then auto-discovery. Auto-discovery looks for a folder containing the *exact* configured ledger path in the current directory and its parents, then one level inside `~/mnt`, `/mnt/user-data/uploads`, `~/Desktop` and `~/Documents`. It never falls back to another ledger copy (archives hold older versions).

## Hard rules

1. **Never send.** Claude drafts; the user sends. Do not create email drafts, send connection requests or message anyone unless the user explicitly asks for that specific action after approving the final text.
2. **The live ledger is the only evidence source.** Every substantive accomplishment maps to a ledger claim with `resume_use` = `Use` or `Use with qualification`. Preserve its exact figures, scope, qualifiers and attribution. `Do not use`, `Hold`, `Context only` (as an accomplishment), and anything absent from the ledger are blocked. Facts the user confirms outside the ledger (for example, having used the company's product) may appear only as worksheet HOOKs the user approved.
3. **Email first, only when the address is confirmed or verified.** Pattern-only addresses are never sendable. With no reliable email, use a LinkedIn connection request where appropriate.
4. **Ranking is independent of reachability.** Never choose a less relevant recipient because their email is easier to find.
5. **One channel per person at a time.** No simultaneous email and LinkedIn outreach to the same recipient. A later switch follows `discipline.channel_switch_after_business_days`.
6. **Reuse live conversations.** An existing email thread or LinkedIn conversation with the recipient is the channel for that recipient.
7. **LinkedIn connection notes: hard maximum of 300 characters, including spaces and punctuation, or the lower `linkedin.account_note_limit`.** Count with the script, never by eye.
8. **One follow-up, only if it adds something new, 5–7 business days after first touch. Then stop.** No follow-up on an unaccepted connection request.
9. **Validate before presenting.** The user never sees a draft that is BLOCKED.
10. **Do not rerun completed analysis.** Use the `jd-five-problems` output, prior scoring, research and application status already in the thread.
11. **Do not edit historical outreach records.** Append a new log row only after the user approves it.

## Inputs

Take these from the thread first. Ask only for what is missing and needed.

- **Job description.**
- **`jd-five-problems` output.** If it's absent, invoke the `jd-five-problems` skill once; do not improvise a problem analysis.
- **Application status:** `not_applied`, `applied` (with date), or `in_process`.
- **Prior opportunity scoring:** context only, never mentioned to recipients.
- **Anything the user already knows:** names, referrals, prior conversations, product experience with the company.

A résumé is optional. If one has been sent, outreach must not contradict it. If it carries a claim the ledger has since restricted, outreach omits that claim rather than repeating it.

## Procedure

### Step 1 · Recipient candidates

Follow `references/recipients_and_channels.md` §1.

- First run `prior-contact --company "<Company>"` and `warm-paths --company "<Company>"`, and search the user's email for the company's domain.
- Identify hiring managers, functional leaders, recruiters and relevant peers.
- Classify hiring involvement as **Confirmed**, **Likely** or **Possible**, with evidence and source.
- Rank by involvement, then functional relevance. Reachability doesn't enter the ranking.

Output: a short ranked table with name, title, recipient type, involvement tier, evidence and source, and relationship.

### Step 2 · Contact research

Follow §2. For each recommended recipient (normally the top two), classify the professional email address as **Confirmed**, **Verified**, **Pattern-only** or **Not found**, and record the evidence. Never present a pattern-only address as an email option.

### Step 3 · Recipient and channel

Apply the decision order in §3: existing conversation, then confirmed or verified email, then LinkedIn message (1st degree), then LinkedIn connection request, then no approved channel. Respect `max_concurrent_recipients_per_company` and the no-duplicate rule.

### Step 4 · Worksheet (Approval 1)

Present the worksheet from `references/message_shapes.md` §1, one block per recipient:

- the selected problem (STATED or INFERRED)
- the verified accomplishment (claim ID, exact wording, must-keep qualifiers)
- the angle (no more than two options)
- the ask
- optional HOOKs

Pick the strongest one or two problem/evidence pairings. Use `claims --search`, then `claims --ids`.

**Stop and wait for the user's approval or edits. Do not draft.**

### Step 5 · Draft and validate

Draft using `references/message_shapes.md` §2–3 and the voice preferences. Save each draft to a scratch file and run:

```
python3 scripts/outreach_tools.py validate --file draft.txt \
  --channel <email|email_reply|linkedin_note|linkedin_message|linkedin_reply> \
  --status <not_applied|applied|in_process> --claims <IDs> \
  [--hooks "<approved hook>; <…>"] [--email-class <confirmed|verified|pattern|risky|not_found>] \
  [--prior-touches N --touch <first|follow_up|switch>] [--other-channel-active]
```

The validator has two severities:

- **BLOCK** (exit 1). The draft cannot be presented as final. Blocks cover:
  - figures or claims the ledger doesn't support
  - quarantined or context-only claims
  - a violated ledger qualifier (a prohibited verb, an added "+", the ledger's own "Never…" or "NOT…" forms, unverified findings stated as observed, figures drawn from flagged quantitative notes)
  - an accomplishment with no claim or approved hook
  - invalid channel or recipient decisions (non-sendable email, simultaneous channel, spent follow-up, InMail when disabled)
  - saying "I applied" before applying
  - exceeding the note limit

  Fix each one and rerun.
- **WARN** (exit 0). Style and judgment, each with a suggestion: dashes, subject-dropped phrasing, an ask without "I", length, question count, ask position, exclamation marks, mentions of the user's own products. Apply the suggestion, or keep the wording and say why. Warnings never stop a draft.

Claim checks are context-aware. Each sentence is matched to the claim(s) it describes, and a claim's restrictions apply only to sentences about that claim or the same program (same ledger adjudication group). A restriction on one claim does not affect an unrelated, properly supported claim at the same employer.

The validator can't judge everything. Still check by hand:

- The problem is quoted from the JD or labelled as a guess.
- Each claim keeps its business unit, period and shared credit.
- Nothing re-supplies context the reader already has.
- A claim isn't reframed into a different purpose. For example, a revenue reconciliation is not "a shared view for lifecycle and sales."

### Step 6 · Present for send approval (Approval 2)

Per recipient, present:

- recipient and channel
- the address with its confidence class, or the profile URL
- subject (for email)
- the final text
- the validator verdict, with character or word count
- a claim map (sentence → claim ID → qualifier kept)
- remaining warnings, and why each was kept
- the follow-up plan

The user sends it. When the user confirms it was sent, format a row with `log-row` and append it only after they approve the row.

## Voice preferences (warnings, not blocks)

Defaults live in `config.template.json` under `voice_style`, and each traces to a stated preference or a measured trait. Read the voice profile in the data folder when one is configured.

- Avoid em and en dashes.
- Keep "I" in sentences written as the user ("I'd…", not "Would you be open…").
- No thesis-statement openings. No manufactured enthusiasm.
- One ask, landing late.
- Length tracks how much context the reader already has.
- Short sentences with a wide spread, and short paragraphs. No lists in messages.
- Don't perform the voice. A draft that reads like an impression is wrong even with zero warnings.

## When things are missing

| Missing | What happens |
|---|---|
| **Data folder or claim ledger** (see *Reaching Career OS*) | Steps 1–3 can run. The worksheet marks every accomplishment `UNVERIFIED: ledger unavailable`, and the skill stops there. No drafts containing accomplishments. A claim-free routing note may be drafted if the user asks, and it is still checked for channel and limits. |
| **Python unavailable** | Count characters with any code execution available. Check claims by quoting each ledger row beside its sentence. Label the output `validated manually`. |
| **No confirmed or verified email** | Recommend a LinkedIn connection request to the same recipient. Never downgrade to an easier-to-reach person. |
| **No LinkedIn connect option** | Report that the top recipient can't be reached by approved channels. Offer the next-ranked recipient separately, labelled as a substitute. No InMail unless enabled. |
| **No identifiable recipient** | Say so and stop. Name what would unlock it (a hiring post, a reporting line, a mutual connection). |
| **No `jd-five-problems` output** | Invoke the `jd-five-problems` skill once, then continue. |
| **Earlier contact found** | Show it first, and apply the follow-up and channel-switch rules. If the follow-up is spent, recommend no further contact with that person. |
| **LinkedIn account limit unknown** | Enforce 300 and warn above 200. Ask the user once and record the answer in their private config. |

## Output standard

Be brief and concrete. Separate stated facts, reasonable inference and speculation, especially about who is hiring. Never claim an address is verified, a person is the hiring manager, or a claim is approved unless the evidence shows it.
