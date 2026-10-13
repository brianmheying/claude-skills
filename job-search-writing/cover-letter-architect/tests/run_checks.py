#!/usr/bin/env python3
"""
Regression checks for the Live Ledger Gate in this skill's Skill.md / SKILL.md.

The gate is an instruction to Claude, so these checks guard the written contract:
each rule the gate depends on must stay present, and each synthetic case in
cases_ledger_gate.json must point at a rule that still exists. No personal data:
the cases use invented claims and a synthetic ledger.

  python3 tests/run_checks.py      # exit 0 = all pass, 1 = failure
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILL = next((os.path.join(ROOT, n) for n in ("SKILL.md", "Skill.md") if os.path.isfile(os.path.join(ROOT, n))), None)
CASES = os.path.join(HERE, "cases_ledger_gate.json")

def norm(s):
    return re.sub(r"\s+", " ", s).lower()

def main():
    if not SKILL:
        print("FAIL: no SKILL.md or Skill.md"); return 1
    text = norm(open(SKILL, encoding="utf-8").read())
    spec = json.load(open(CASES, encoding="utf-8"))
    rules = spec["rules"]
    skill_name = os.path.basename(ROOT)
    fails, n = [], 0
    for rid, r in rules.items():
        if r.get("only") and skill_name not in r["only"]:
            continue
        n += 1
        for phrase in r["must_contain"]:
            if norm(phrase) not in text:
                fails.append(f"rule {rid}: missing \"{phrase}\"")
    for c in spec["cases"]:
        n += 1
        rid = c["rule"]
        if rid not in rules:
            fails.append(f"case {c['id']}: unknown rule {rid}")
        elif rules[rid].get("only") and skill_name not in rules[rid]["only"]:
            continue
    for f in fails:
        print("FAIL", f)
    print(f"{n - len(fails)}/{n} checks passed ({skill_name})")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
