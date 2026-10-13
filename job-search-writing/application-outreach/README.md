# Application Outreach

## What it does

Turns a role worth pursuing into a conversation with someone who can move it. It ranks the people connected to the role (hiring manager, functional leader, recruiter, peers) by their likely involvement, researches whether a professional email address is confirmed or verified, and picks one channel per person under hard rules: email only for confirmed or verified addresses, otherwise a LinkedIn request within the note limit, never two channels at once. It shows a small worksheet (problem, proof, angle, ask) for approval, then drafts and validates the message. It never sends anything.

## Why it exists

Strong applications often go unread. Earlier outreach by hand showed the real risk wasn't generic messaging but **evidence drift**: claims in messages slowly stopped matching the canonical claim ledger (an added "+", a causal verb the ledger forbids, an unverified finding stated as fact). This skill makes the ledger the only evidence source and blocks drift before a draft is ever shown.

## When I use it

After deciding a role is worth pursuing and running `jd-five-problems`, either before, during or after applying. It runs in parallel with résumé and cover-letter work and doesn't depend on them.

## How the validator decides

- **BLOCK:** unsupported or quarantined claims, figures not in the ledger, violated ledger qualifiers, an accomplishment with no claim or approved hook, invalid channel decisions (pattern-only email, a simultaneous channel, a spent follow-up), saying "I applied" before applying, and connection notes over the limit.
- **WARN:** voice and style (dashes, subject-dropped phrasing, length, ask placement). Each warning comes with a suggestion, and none of them stops a draft.
- **Context-aware:** a claim's restrictions apply only to sentences about that claim or the same program, never to an unrelated claim at the same employer.

## Data and privacy

The skill holds no personal data. It reads a separate data folder (the "Career OS"), found through `--root`, `$CAREER_OS_DIR`, a private config, or auto-discovery by the claim-ledger path. Personal settings go in `config.local.json` or `~/.config/application-outreach/config.json`. Both are git-ignored.

**Where it can read data.** Installed in Claude, the skill runs in Claude's cloud sandbox, which can't see your computer's folders. In a session linked to your computer, Claude stages a read-only snapshot of the ledger (and any outreach records the run needs) into that session. In an unlinked session, the skill says it can't reach the ledger and stops at the worksheet. Run on your own computer, it finds the data folder directly. `scripts/outreach_tools.py where` shows what it found and where it looked.

## Install

```
python3 scripts/package_skill.py --out <folder where you keep skill zips>/application-outreach.zip
```

This builds the zip (SKILL.md, references, scripts, tests and fixtures; executables marked), then extracts it and runs the synthetic suite from the extracted copy. Upload the zip to Claude the same way as any custom skill, replacing the previous version. Leave out `config.local.json` with `--no-local-config` if you don't want personal settings in the upload.

## Files included

- `SKILL.md`: the skill definition
- `config.template.json`: defaults, with no personal data
- `references/recipients_and_channels.md`: involvement tiers, email confidence classes, channel decision order, follow-up rules
- `references/message_shapes.md`: the worksheet, and message shapes by recipient, status and channel
- `scripts/package_skill.py`: builds and verifies the installable zip
- `scripts/outreach_tools.py`: data-folder discovery, ledger lookups, prior-contact and warm-path checks, the validator, and log rows (Python 3, standard library only)
- `tests/run_cases.py`, `tests/cases_synthetic.json`, `tests/fixtures/test_ledger.csv`: a synthetic regression suite with fictional claims (`python3 tests/run_cases.py`)
