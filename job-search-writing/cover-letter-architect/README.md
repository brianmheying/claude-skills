# Cover Letter Architect

## What it does

Builds the underlying argument for a cover letter — a differentiated, company-specific case connecting the candidate's real, defensible evidence to the specific role — before any prose gets written. It works from a diagnosis of the role (see `jd-five-problems`) and the candidate's actual track record, not generic template language.

## Why it exists

Most cover letters fail before a single sentence is drafted, because they skip straight to prose without first architecting a specific, non-generic argument for why this candidate fits this role at this company. This skill forces that argument to exist first.

## When I use it

After diagnosing a job description (typically with `jd-five-problems`), when I'm about to write a cover letter and want the underlying argument nailed down before drafting.

## Live Ledger Gate

Before handing off an architecture or issuing READY, the skill checks every substantive claim (accomplishments, metrics, mechanisms, attribution, scope) against the canonical claim ledger in my Career OS data folder. Ordinary facts such as tools, responsibilities and employment history are checked against appropriate evidence instead of being blocked for lacking a ledger row. The ledger stays authoritative: new firsthand evidence that conflicts with it is flagged for adjudication, not used to override it. Without the ledger, READY is not available.

## Files included

- `Skill.md` — the skill definition (installed as `SKILL.md`)
- `tests/run_checks.py`, `tests/cases_ledger_gate.json` — regression checks for the Live Ledger Gate (synthetic data only)

Build the installable zip with `python3 tools/package_skill.py job-search-writing/cover-letter-architect --out <path>.zip` from the repo root.
