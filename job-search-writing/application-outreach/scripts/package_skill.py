#!/usr/bin/env python3
"""
package_skill.py: build the installable zip for this skill, then verify it.

  python3 scripts/package_skill.py --out /path/to/application-outreach.zip
  python3 scripts/package_skill.py --out ... --no-local-config   # leave personal settings out
  python3 scripts/package_skill.py --out ... --skip-verify

The zip has one top-level folder named after the skill (the format Claude's skill
upload expects) and contains SKILL.md, README.md, config.template.json, references/,
scripts/ and tests/ (with fixtures). config.local.json is included when present unless
--no-local-config is given: it holds personal settings, so only ever upload that zip
to your own account; never publish it.

Excluded always: __pycache__, *.pyc, .DS_Store, tests/private/, *.private.json, *.zip.
Executable bits: scripts/*.py and tests/run_cases.py are stored as 0755, everything else 0644.

Verification extracts the zip to a temporary folder and runs the synthetic test suite
from the extracted copy, so what gets tested is exactly what gets installed.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SKILL_NAME = os.path.basename(SKILL_DIR)

REQUIRED = [
    "SKILL.md",
    "README.md",
    "config.template.json",
    "references/recipients_and_channels.md",
    "references/message_shapes.md",
    "scripts/outreach_tools.py",
    "scripts/package_skill.py",
    "tests/run_cases.py",
    "tests/cases_synthetic.json",
    "tests/fixtures/test_ledger.csv",
]
EXECUTABLE = {"scripts/outreach_tools.py", "scripts/package_skill.py", "tests/run_cases.py"}
EXCLUDE_DIRS = {"__pycache__", ".git", "private"}
EXCLUDE_SUFFIX = (".pyc", ".zip", ".private.json")
EXCLUDE_NAMES = {".DS_Store"}


def collect(include_local):
    files = []
    for dirpath, dirnames, filenames in os.walk(SKILL_DIR):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for fn in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, fn), SKILL_DIR).replace(os.sep, "/")
            if fn in EXCLUDE_NAMES or fn.endswith(EXCLUDE_SUFFIX):
                continue
            if rel == "config.local.json" and not include_local:
                continue
            if fn.endswith(".local.json") and rel != "config.local.json":
                continue
            files.append(rel)
    return files


def build(out, include_local):
    missing = [r for r in REQUIRED if not os.path.isfile(os.path.join(SKILL_DIR, r))]
    if missing:
        sys.exit("Missing required files: " + ", ".join(missing))
    if os.path.isfile(os.path.join(SKILL_DIR, "Skill.md")) and os.path.isfile(os.path.join(SKILL_DIR, "SKILL.md")) \
            and not os.path.samefile(os.path.join(SKILL_DIR, "Skill.md"), os.path.join(SKILL_DIR, "SKILL.md")):
        sys.exit("Both Skill.md and SKILL.md exist; keep only SKILL.md.")
    files = collect(include_local)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        d = zipfile.ZipInfo(SKILL_NAME + "/")
        d.external_attr = (0o40755 << 16) | 0x10
        z.writestr(d, "")
        dirs_done = set()
        for rel in files:
            parts = rel.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                sub = "/".join(parts[:i])
                if sub not in dirs_done:
                    di = zipfile.ZipInfo(f"{SKILL_NAME}/{sub}/")
                    di.external_attr = (0o40755 << 16) | 0x10
                    z.writestr(di, "")
                    dirs_done.add(sub)
            info = zipfile.ZipInfo(f"{SKILL_NAME}/{rel}")
            mode = 0o755 if rel in EXECUTABLE else 0o644
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(os.path.join(SKILL_DIR, rel), "rb") as f:
                z.writestr(info, f.read())
    os.replace(tmp, out)
    return files


def verify(out):
    tmpdir = tempfile.mkdtemp(prefix="skill-verify-")
    try:
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
            for r in REQUIRED:
                if f"{SKILL_NAME}/{r}" not in names:
                    sys.exit(f"VERIFY FAILED: {r} missing from zip")
            z.extractall(tmpdir)
            for info in z.infolist():
                rel = info.filename[len(SKILL_NAME) + 1:]
                if rel in EXECUTABLE:
                    p = os.path.join(tmpdir, info.filename)
                    os.chmod(p, (info.external_attr >> 16) & 0o777)
        root = os.path.join(tmpdir, SKILL_NAME)
        for rel in EXECUTABLE:
            if not os.access(os.path.join(root, rel), os.X_OK):
                sys.exit(f"VERIFY FAILED: {rel} is not executable in the zip")
        r = subprocess.run([sys.executable, os.path.join(root, "tests", "run_cases.py")], capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr)
        if r.returncode != 0:
            print(r.stdout)
            sys.exit("VERIFY FAILED: synthetic tests did not pass from the packaged copy")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="Where to write the zip")
    ap.add_argument("--no-local-config", action="store_true", help="Leave config.local.json out of the zip")
    ap.add_argument("--skip-verify", action="store_true")
    a = ap.parse_args()
    files = build(a.out, include_local=not a.no_local_config)
    print(f"Built {a.out} with {len(files)} files:")
    for f in files:
        print(f"  {'x' if f in EXECUTABLE else '-'} {SKILL_NAME}/{f}")
    if "config.local.json" in files:
        print("Note: includes config.local.json (personal settings). Upload only to your own account.")
    if not a.skip_verify:
        verify(a.out)
        print("Verified: required files present, executables marked, synthetic suite passes from the zip.")


if __name__ == "__main__":
    main()
