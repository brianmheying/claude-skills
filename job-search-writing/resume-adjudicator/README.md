# Resume Adjudicator

## What it does

Independently adjudicates a near-final, tailored resume against its target job description (and, where used, its `jd-five-problems` analysis) and decides one of three outcomes: ship it, surgically revise specific parts, or reopen it for larger rework.

## Why it exists

It's easy to keep polishing a resume without a clear signal for when it's actually done and targeted correctly versus needs real rework. This skill acts as a final, decisive checkpoint instead of another round of open-ended editing.

## When I use it

At the end of the resume-tailoring process, once a draft feels close to final, to get a clear ship/revise/reopen call rather than more unstructured feedback.

## Live Ledger Gate

Before issuing SHIP AS-IS, the skill checks every substantive claim (accomplishments, metrics, mechanisms, attribution, scope) against the canonical claim ledger in my Career OS data folder. Ordinary facts such as tools, responsibilities and employment history are checked against appropriate evidence instead of being blocked for lacking a ledger row. The ledger stays authoritative: new firsthand evidence that conflicts with it is flagged for adjudication, not used to override it. Without the ledger, SHIP AS-IS is not available.

## Files included

- `Skill.md` — the skill definition (installed as `SKILL.md`)
- `tests/run_checks.py`, `tests/cases_ledger_gate.json` — regression checks for the Live Ledger Gate (synthetic data only)

Build the installable zip with `python3 tools/package_skill.py job-search-writing/resume-adjudicator --out <path>.zip` from the repo root.
