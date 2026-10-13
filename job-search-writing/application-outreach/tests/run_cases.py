#!/usr/bin/env python3
"""
Run validator cases and compare against expected outcomes.

  python3 tests/run_cases.py                                  # synthetic suite (repo fixtures)
  python3 tests/run_cases.py --cases PRIVATE.json --root DIR  # private regression against a real ledger

A case file is JSON: {"ledger": optional path relative to the case file, "cases": [ {
  "id", "label", "text", "channel", "status", "claims", "hooks", "email_class",
  "prior_touches", "touch", "other_channel_active",
  "expect": "BLOCK" | "PASS", "expect_block_contains": [..], "expect_no_block_contains": [..] } ] }
Exit code 1 if any case disagrees with its expectation.
"""
import argparse, json, os, sys, types, csv

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import outreach_tools as ot  # noqa: E402


def load_ledger_file(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return {r["claim_id"].strip(): r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(HERE, "cases_synthetic.json"))
    ap.add_argument("--root", help="Career OS data folder (for cases without their own ledger)")
    ap.add_argument("--config")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--assume-verified-email", action="store_true", help="Treat every email address as verified, to isolate content checks")
    a = ap.parse_args()
    with open(a.cases, encoding="utf-8") as f:
        spec = json.load(f)
    if spec.get("use_template_config"):
        with open(os.path.join(os.path.dirname(HERE), "config.template.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["_source"] = "template (suite setting)"
    else:
        cfg = ot.load_config(a.config)
    if spec.get("config_overrides"):
        cfg = ot.deep_merge(cfg, spec["config_overrides"])
    if spec.get("ledger"):
        led = load_ledger_file(os.path.join(os.path.dirname(os.path.abspath(a.cases)), spec["ledger"]))
    else:
        root, _ = ot.discover_root(cfg, a.root)
        led, _, _ = ot.load_ledger(root, cfg)
    bad = 0
    for c in spec["cases"]:
        ns = types.SimpleNamespace(channel=c["channel"], status=c.get("status", "applied"), claims=c.get("claims", ""),
                                   hooks=c.get("hooks", ""), email_class=("verified" if a.assume_verified_email and c["channel"] == "email" else c.get("email_class")),
                                   prior_touches=c.get("prior_touches", 0), touch=c.get("touch", "first"),
                                   other_channel_active=c.get("other_channel_active", False))
        ccfg = ot.deep_merge(cfg, c["config_overrides"]) if c.get("config_overrides") else cfg
        blocks, warns, _, stats = ot.evaluate(c["text"], ns, ccfg, led)
        got = "BLOCK" if blocks else "PASS"
        exp = c.get("expect_content", c.get("expect", got)) if a.assume_verified_email else c.get("expect", got)
        ok = got == exp
        for frag in ([] if a.assume_verified_email else c.get("expect_block_contains", [])):
            if not any(frag.lower() in b.lower() for b in blocks):
                ok = False
        for frag in c.get("expect_no_block_contains", []):
            if any(frag.lower() in b.lower() for b in blocks):
                ok = False
        bad += (not ok)
        print(f"{'ok  ' if ok else 'FAIL'} {c['id']:<10} got={got:<5} expect={exp:<5} blocks={len(blocks)} warns={len(warns)} chars={stats['chars']}  {c.get('label','')}")
        if a.verbose or not ok:
            for b in dict.fromkeys(blocks):
                print(f"        BLOCK {b}")
            if a.verbose:
                for w, _ in warns:
                    print(f"        warn  {w}")
    print(f"\n{len(spec['cases']) - bad}/{len(spec['cases'])} cases match expectations")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
