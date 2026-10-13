#!/usr/bin/env python3
"""
package_skill.py: build an installable zip for a skill folder in this repo, then verify it.

  python3 tools/package_skill.py job-search-writing/resume-adjudicator --out /path/resume-adjudicator.zip

For skills without their own packager (application-outreach has scripts/package_skill.py).
The zip has one top-level folder named after the skill. Skill.md is stored as SKILL.md,
the filename Claude's skill format specifies. README.md, references/, scripts/ and tests/
are included when present.

Excluded always: .git, __pycache__, *.pyc, .DS_Store, *.zip, tests/private/, *.local.json,
*.private.json. Executable bits: scripts/*.py and tests/*.py are stored as 0755.

Verification extracts the zip to a temporary folder, checks SKILL.md is present, and runs
tests/run_checks.py from the extracted copy when the skill has one.
"""
import argparse, os, shutil, subprocess, sys, tempfile, zipfile

EXCLUDE_DIRS = {"__pycache__", ".git", "private"}
EXCLUDE_SUFFIX = (".pyc", ".zip", ".local.json", ".private.json")
EXCLUDE_NAMES = {".DS_Store"}

def collect(skill_dir):
    out = []
    for dirpath, dirnames, filenames in os.walk(skill_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for fn in sorted(filenames):
            if fn in EXCLUDE_NAMES or fn.endswith(EXCLUDE_SUFFIX):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), skill_dir).replace(os.sep, "/")
            out.append(rel)
    return out

def build(skill_dir, out):
    name = os.path.basename(os.path.normpath(skill_dir))
    files = collect(skill_dir)
    defs = [f for f in files if f in ("SKILL.md", "Skill.md")]
    if len(defs) != 1:
        sys.exit(f"Expected exactly one of SKILL.md / Skill.md in {skill_dir}, found {defs}")
    tmp = out + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        seen = set()
        def adddir(d):
            if d not in seen:
                zi = zipfile.ZipInfo(d + "/"); zi.external_attr = (0o40755 << 16) | 0x10
                z.writestr(zi, ""); seen.add(d)
        adddir(name)
        stored = []
        for rel in files:
            arc = "SKILL.md" if rel == "Skill.md" else rel
            parts = arc.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                adddir(name + "/" + "/".join(parts[:i]))
            zi = zipfile.ZipInfo(f"{name}/{arc}")
            ex = arc.endswith(".py") and arc.split("/")[0] in ("scripts", "tests")
            zi.external_attr = (0o100000 | (0o755 if ex else 0o644)) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            with open(os.path.join(skill_dir, rel), "rb") as f:
                z.writestr(zi, f.read())
            stored.append((arc, ex))
    os.replace(tmp, out)
    return name, stored

def verify(out, name):
    d = tempfile.mkdtemp(prefix="skill-verify-")
    try:
        with zipfile.ZipFile(out) as z:
            if f"{name}/SKILL.md" not in z.namelist():
                sys.exit("VERIFY FAILED: SKILL.md missing from zip")
            z.extractall(d)
        root = os.path.join(d, name)
        test = os.path.join(root, "tests", "run_checks.py")
        if os.path.isfile(test):
            r = subprocess.run([sys.executable, test], capture_output=True, text=True)
            print(r.stdout.strip())
            if r.returncode != 0:
                sys.exit("VERIFY FAILED: tests/run_checks.py did not pass from the packaged copy")
        else:
            print("(no tests/run_checks.py)")
    finally:
        shutil.rmtree(d, ignore_errors=True)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-verify", action="store_true")
    a = ap.parse_args()
    name, stored = build(a.skill_dir, a.out)
    print(f"Built {a.out} with {len(stored)} files:")
    for arc, ex in stored:
        print(f"  {'x' if ex else '-'} {name}/{arc}")
    if not a.skip_verify:
        verify(a.out, name)
        print("Verified: SKILL.md present; checks pass from the zip.")

if __name__ == "__main__":
    main()
