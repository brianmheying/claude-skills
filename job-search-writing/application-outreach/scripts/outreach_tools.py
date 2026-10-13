#!/usr/bin/env python3
"""
outreach_tools.py: deterministic helpers for the application-outreach skill.

Standard library only. Reads the Career OS data folder (the source of truth for the
claim ledger, application history and outreach records). It never writes there except
`log-row --append`, which the skill runs only after the user approves the row.

Subcommands
  where         Show which config and data folder were resolved, and why
  claims        Look up or search approved claims in the canonical claim ledger
  prior-contact Check every outreach record for earlier contact with a person or company
  warm-paths    List 1st-degree LinkedIn connections at a company (from the export)
  count         Exact character and word count of a draft
  validate      Validate a draft: BLOCK on integrity/channel/limit problems, WARN on style
  log-row       Format (and optionally append) a row for the outreach log

Config resolution (first found wins)
  --config PATH > $APPLICATION_OUTREACH_CONFIG > <skill>/config.local.json
  > ~/.config/application-outreach/config.json > <skill>/config.template.json

Data-folder resolution (first found wins; nothing machine-specific is hardcoded)
  --root PATH > $CAREER_OS_DIR > "career_os_dir" in a local config
  > auto-discovery: a folder containing the configured claim-ledger path, searched in
    the current directory and its parents, then one level inside $HOME/mnt, /mnt/user-data/uploads,
    ~/Desktop and ~/Documents.

Exit codes: 0 = PASS (warnings allowed), 1 = BLOCKED, 2 = setup error.
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)

APPROVED_USE = {"Use", "Use with qualification"}
csv.field_size_limit(10_000_000)


# ---------------------------------------------------------------- setup
def config_candidates(explicit=None):
    c = []
    if explicit:
        c.append(("--config", explicit))
    if os.environ.get("APPLICATION_OUTREACH_CONFIG"):
        c.append(("$APPLICATION_OUTREACH_CONFIG", os.environ["APPLICATION_OUTREACH_CONFIG"]))
    c.append(("skill config.local.json", os.path.join(SKILL_DIR, "config.local.json")))
    c.append(("~/.config/application-outreach/config.json", os.path.expanduser("~/.config/application-outreach/config.json")))
    c.append(("skill config.template.json", os.path.join(SKILL_DIR, "config.template.json")))
    return c


def deep_merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(explicit=None):
    """Template supplies defaults; the first local config found overrides them."""
    tpl_path = os.path.join(SKILL_DIR, "config.template.json")
    with open(tpl_path, encoding="utf-8") as f:
        cfg = json.load(f)
    src = "skill config.template.json"
    for label, p in config_candidates(explicit)[:-1]:
        if p and os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                cfg = deep_merge(cfg, json.load(f))
            src = label
            break
    cfg["_source"] = src
    return cfg


SEARCH_BASES = ["~/mnt", "/mnt/user-data/uploads", "~/Desktop", "~/Documents"]


def discover_root(cfg, explicit=None, trace=None):
    """Find the Career OS data folder. Never falls back to a partial or archived ledger:
    a candidate qualifies only if it contains the exact configured claim-ledger path."""
    rel = cfg["paths"]["claim_ledger"]
    log = trace if trace is not None else []
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit)), "--root"
    if os.environ.get("CAREER_OS_DIR"):
        return os.path.abspath(os.path.expanduser(os.environ["CAREER_OS_DIR"])), "$CAREER_OS_DIR"
    if cfg.get("career_os_dir"):
        return os.path.abspath(os.path.expanduser(cfg["career_os_dir"])), f"career_os_dir in {cfg['_source']}"
    seen = []
    d = os.getcwd()
    while True:
        seen.append(d)
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    log.append(f"current directory and parents ({len(seen)} folders)")
    for base in SEARCH_BASES:
        b = os.path.expanduser(base)
        if os.path.isdir(b):
            try:
                kids = [os.path.join(b, x) for x in sorted(os.listdir(b))]
            except OSError:
                kids = []
            log.append(f"{base}: {len(kids)} folder(s) checked")
            seen += kids
        else:
            log.append(f"{base}: not present in this environment")
    for cand in seen:
        if os.path.isfile(os.path.join(cand, rel)):
            return cand, "auto-discovered"
    return None, "not found"


ACCESS_HELP = """The Career OS data folder is not reachable from where this script is running.

Where the script runs matters:
  - Installed in Claude (claude.ai / Claude app): skills run in Claude's cloud sandbox,
    which cannot see your computer's folders. A session linked to your computer can
    stage a read-only snapshot of the needed Career OS files into the session
    (they land under /mnt/user-data/uploads/<folder name>/...), and discovery finds them.
    A session that is not linked cannot reach Career OS at all.
  - On your computer (Terminal, Claude Code, or a linked session's device shell):
    discovery checks ~/Desktop, ~/Documents and connected folders under ~/mnt.
  - Anywhere: pass --root PATH or set CAREER_OS_DIR.

Without the ledger, no claim can be marked verified. Stop at the worksheet."""


def rpath(root, rel):
    return os.path.join(root, rel)


def load_ledger(root, cfg):
    if not root:
        print("SETUP ERROR: Career OS data folder not found (looked for " + cfg["paths"]["claim_ledger"] + ").", file=sys.stderr)
        print(ACCESS_HELP, file=sys.stderr)
        sys.exit(2)
    p = rpath(root, cfg["paths"]["claim_ledger"])
    if not os.path.exists(p):
        print(f"SETUP ERROR: claim ledger not found under the data folder ({cfg['paths']['claim_ledger']}).", file=sys.stderr)
        print("No claim can be marked verified without the live ledger. Stop at the worksheet.", file=sys.stderr)
        sys.exit(2)
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    mtime = dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
    if p.startswith("/mnt/user-data/uploads"):
        mtime = f"snapshot staged {mtime}"
    return {r["claim_id"].strip(): r for r in rows}, p, mtime


def cmd_where(a, cfg):
    print(f"config:      {cfg['_source']}")
    print(f"looking for: {cfg['paths']['claim_ledger']}")
    if a.root_source == "not found":
        print("data folder: (not found)")
        print("searched:    " + "\n             ".join(a.trace))
        print()
        print(ACCESS_HELP)
        sys.exit(2)
    print(f"data folder: {a.root}  [{a.root_source}]")
    p = rpath(a.root, cfg["paths"]["claim_ledger"])
    ok = os.path.exists(p)
    print(f"ledger:      {'present' if ok else 'MISSING at that path'}")
    if ok:
        with open(p, encoding="utf-8-sig", newline="") as f:
            n = sum(1 for _ in csv.DictReader(f))
        mtime = dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
        if a.root.startswith("/mnt/user-data/uploads"):
            print(f"             {n} claims, snapshot staged {mtime}")
            print("note:        a read-only snapshot in this session, not the live folder; the time shown is when it")
            print("             was staged, not when the ledger was last edited. Re-stage if the ledger changes.")
        else:
            print(f"             {n} claims, modified {mtime}")
    sys.exit(0 if ok else 2)


# ---------------------------------------------------------------- claims
def claim_block(r, full=False):
    lim = None if full else 260
    cut = (lambda s: s if lim is None or len(s) <= lim else s[:lim] + "…")
    out = [
        f"[{r['claim_id']}] {r['employer']} · {r['period']} · {r['category']}",
        f"  USE: {r['resume_use']}   STATUS: {cut(r['evidence_status'])}",
        f"  WORDING: {cut(r['canonical_wording'])}",
    ]
    if r.get("quantitative_result"):
        out.append(f"  NUMBERS: {r['quantitative_result']}")
    if r.get("scope_and_attribution"):
        out.append(f"  SCOPE/ATTRIBUTION (must preserve): {r['scope_and_attribution']}")
    if r.get("notes"):
        out.append(f"  NOTES: {cut(r['notes'])}")
    return "\n".join(out)


def cmd_claims(a, cfg):
    led, path, mtime = load_ledger(a.root, cfg)
    print(f"Ledger: {path} (modified {mtime}, {len(led)} claims)\n")
    if a.ids:
        bad = 0
        for cid in [x.strip() for x in a.ids.split(",") if x.strip()]:
            r = led.get(cid)
            if not r:
                print(f"[{cid}] NOT IN LEDGER: BLOCKED\n"); bad += 1; continue
            print(claim_block(r, full=True))
            if r["resume_use"] not in APPROVED_USE:
                print(f"  >>> BLOCKED for outreach: resume_use = '{r['resume_use']}'"); bad += 1
            print()
        sys.exit(1 if bad else 0)
    terms = [t.lower() for t in (a.search or "").split()]
    hits = []
    for r in led.values():
        if r["resume_use"] not in APPROVED_USE and not a.include_blocked:
            continue
        if a.employer and a.employer.lower() not in r["employer"].lower():
            continue
        blob = " ".join(r.values()).lower()
        if all(t in blob for t in terms):
            hits.append(r)
    for r in hits:
        print(claim_block(r)); print()
    print(f"{len(hits)} claim(s) matched" + ("" if a.include_blocked else " (approved for use only)"))


# ---------------------------------------------------------------- history
def xlsx_rows(path):
    """Minimal stdlib xlsx reader: yields (sheet_name, [cell strings])."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid = {r.get("Id"): r.get("Target") for r in rels}
        for s in wb.find("m:sheets", ns):
            target = rid[s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")]
            target = target.lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            sheet = ET.fromstring(z.read(target))
            for row in sheet.iter(f"{{{ns['m']}}}row"):
                vals = []
                for c in row.findall("m:c", ns):
                    v = c.find("m:v", ns)
                    t = c.get("t")
                    if t == "s" and v is not None:
                        vals.append(shared[int(v.text)])
                    elif t == "inlineStr":
                        vals.append("".join(x.text or "" for x in c.iter(f"{{{ns['m']}}}t")))
                    else:
                        vals.append(v.text if v is not None else "")
                yield s.get("name"), vals


def cmd_prior_contact(a, cfg):
    name = (a.name or "").strip()
    company = (a.company or "").strip()
    keys = [k for k in [name, company] if k]
    if not keys:
        print("Give --name and/or --company", file=sys.stderr); sys.exit(2)
    found = 0

    def hit(src, line):
        nonlocal found
        found += 1
        print(f"  [{src}] {line.strip()[:240]}")

    def matches(text):
        t = text.lower()
        if name and company:
            return name.lower() in t or (company.lower() in t and a.company_wide)
        return any(k.lower() in t for k in keys)

    print(f"Prior-contact check for: name='{name}' company='{company}'\n")
    files = [rpath(a.root, cfg["paths"]["outreach_log"])] + sorted(glob.glob(rpath(a.root, cfg["paths"]["outreach_history_glob"])))
    for f in files:
        if not os.path.exists(f):
            print(f"  (missing: {f})"); continue
        with open(f, encoding="utf-8") as fh:
            for ln in fh:
                if matches(ln):
                    hit(os.path.basename(f), ln)
    xp = rpath(a.root, cfg["paths"]["job_tracker_xlsx"])
    if os.path.exists(xp):
        try:
            for sheet, vals in xlsx_rows(xp):
                line = " | ".join(v for v in vals if v)
                if line and matches(line):
                    hit(f"Job Search Tracker/{sheet}", line)
        except Exception as e:  # noqa
            print(f"  (could not read tracker: {e})")
    mp = rpath(a.root, cfg["paths"]["linkedin_messages"])
    if name and os.path.exists(mp):
        with open(mp, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if name.lower() == (r.get("counterparty_name") or "").strip().lower():
                    hit("LinkedIn messages export", f"{r['message_date']} {r['direction']}: {r['content'][:160]}")
    cp = rpath(a.root, cfg["paths"]["linkedin_connections"])
    if name and os.path.exists(cp):
        with open(cp, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if name.lower() == (r.get("name_key") or "").strip().lower():
                    em = r.get("email_address") or ""
                    hit("LinkedIn connections export", f"1st-degree since {r['connected_on']} · {r['position_raw']} @ {r['company_raw']}" + (f" · email on file: {em}" if em else ""))
    print(f"\n{found} record(s) found. Local records only: also search Gmail (from:/to: the person and domain) and check LinkedIn for activity after the export date.")


def cmd_warm_paths(a, cfg):
    cp = rpath(a.root, cfg["paths"]["linkedin_connections"])
    if not os.path.exists(cp):
        print("LinkedIn connections export not found.", file=sys.stderr); sys.exit(2)
    c = a.company.lower()
    n = 0
    with open(cp, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if c in (r.get("company_key") or "").lower() or c in (r.get("company_raw") or "").lower():
                n += 1
                em = r.get("email_address") or ""
                print(f"  {r['display_name']} · {r['position_raw']} · connected {r['connected_on']} · {r['profile_url']}" + (f" · email: {em}" if em else ""))
    with open(cp, encoding="utf-8", newline="") as fh:
        exp = next(csv.DictReader(fh), {}).get("_export_date", "?")
    print(f"\n{n} 1st-degree connection(s) at '{a.company}' in the export dated {exp}. Current employer may have changed; confirm before relying on one.")


# ---------------------------------------------------------------- validate
#
# Two severities:
#   BLOCK  factual or integrity problems: a figure or claim the ledger does not support,
#          a violated ledger qualifier, an unsupported accomplishment, a channel or
#          recipient decision that breaks the hard rules, or a character-limit breach.
#          Exit code 1. The message must not be presented as final.
#   WARN   style and judgment: voice preferences, length, ask placement, phrasing.
#          Each comes with a suggestion. Exit code 0.
#
# Claim checks are context-aware: each sentence is matched to the mapped claim(s) it
# describes, and a claim's guards apply only to sentences about that claim (or about the
# same program, per the ledger's adjudication group). A restriction on one claim at an employer
# does not affect a sentence about a different, properly supported claim at the same employer.

NUM_RE = re.compile(r"(?<![\w/])(~|about |approximately |over |more than )?(\$?\d[\d,]*(?:\.\d+)?)\s?(%|[KkMmBb](?![a-z])|x(?![a-z]))?(\+)?")
IGNORE_AFTER = re.compile(r"^\s?(-|\s)?(minute|minutes|min|hour|hours|day|days|week|weeks|month|months|year|years|th|st|nd|rd|in\s+10)\b", re.I)
DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b")
MONTH_DATE_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}\b(,?\s+\d{4})?", re.I)
PHONE_RE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
GREETING_RE = re.compile(r"^(hi|hey|hello|dear|thanks for connecting|thank you for connecting|thanks|thank you)\b[^,.!]*[,.!]\s*", re.I)
NUM_WORDS = {"two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
             "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13", "twenty": "20"}

def employer_aliases(led, cfg):
    """Employers come from the ledger's own `employer` column; extra spellings come from local config."""
    non_work = {"credential", "education", "technical competency"}
    out = {}
    for r in led.values():
        e = (r.get("employer") or "").strip()
        cat = (r.get("category") or "").strip().lower()
        if not e or e in ("—", "-", "Cross-employer") or cat in non_work or e.lower().startswith("disputed"):
            continue
        out.setdefault(e, {e.lower()})
    for e, al in (cfg.get("employer_aliases") or {}).items():
        if e.startswith("_") or not isinstance(al, list):
            continue
        out.setdefault(e, set()).update(a.lower() for a in al)
    return out
FIRST_PERSON_ACTION = re.compile(
    r"\b(I|I've|I'd|we|we've)\s+(?:also\s+|then\s+|personally\s+)?"
    r"(built|rebuilt|led|grew|designed|ran|launched|created|turned|redesigned|compared|routed|used|took over|"
    r"managed|owned|drove|found|recovered|increased|reduced|cut|raised|shipped|worked|helped|moved|"
    r"developed|implemented|migrated|delivered|generated|influenced|doubled|tripled|scaled|saved|won|closed|have been|have built|have led)\b",
    re.I)
MEASURED_TERMS = ["holdout", "hold-out", "measured against", "incremental", "lift", "statistically significant", "validated", "proved", "proven"]
FINDING_LANG = re.compile(r"\b(found that|we found|I found|showed that|proved|turned out|almost always|confirmed that|discovered that)\b", re.I)
UNVERIFIED_OUTCOME = re.compile(r"unverified|hypothesis|not confirmed|unresolved|not observed", re.I)
SHAKY_QUANT = re.compile(r"ambiguous|deck-only|disputed|unverified|unresolved|unsupported|quarantin", re.I)
STOP = {"a", "an", "the", "of", "and", "or", "new", "to", "in", "for", "on", "with", "as", "be", "is", "that",
        "this", "from", "into", "their", "they", "them", "were", "was", "have", "has", "had", "been", "about",
        "over", "more", "than", "your", "you", "our", "who", "what", "which", "when", "where", "while", "then",
        "also", "just", "very", "most", "much", "work", "role", "team", "would", "could", "like", "it's", "i'd",
        "i've", "i'm", "there", "here", "some", "same", "other", "each", "every", "only", "through", "across"}


def norm_num(tok):
    """',500' -> '1500'; '1.0' -> '1'; '7.00' -> '7' (so '1%' matches the ledger's '~1.0%')."""
    t = tok.replace(",", "").replace("$", "").lower()
    m = re.match(r"^(\d+)\.(\d+)(.*)$", t)
    if m and set(m.group(2)) == {"0"}:
        t = m.group(1) + m.group(3)
    return t


def numbers_in(text, keep_small=False):
    out = []
    text = DATE_RE.sub(" ", MONTH_DATE_RE.sub(" ", text))
    for m in NUM_RE.finditer(text):
        core, unit, plus = m.group(2), (m.group(3) or ""), (m.group(4) or "")
        start, end = m.span()
        if IGNORE_AFTER.match(text[end:]) and not unit:
            continue
        bare = norm_num(core)
        raw = bare + unit.lower()
        is_year = (not unit and "." not in bare and len(bare) == 4 and bare.startswith(("19", "20")))
        if not keep_small and not unit and bare.isdigit() and int(bare) < 10:
            continue
        out.append({"token": text[start:end].strip(), "key": raw, "plus": bool(plus), "year": is_year})
    return out


def stems(text):
    toks = re.findall(r"[a-z][a-z'\-]+", text.lower())
    out = set()
    for t in toks:
        for part in t.split("-"):
            if len(part) >= 4 and part not in STOP:
                out.add(part[:6])
    return out


def claim_text(r):
    return " ".join([r.get("canonical_wording", ""), r.get("quantitative_result", ""), r.get("scope_and_attribution", "")])


def adj_group(r):
    m = re.search(r"ADJ \d{4}-\d{2}-\d{2}: ([A-Z]{2}-\d+) (?:decision|safeguard)", r.get("notes", ""))
    return m.group(1) if m else None


def related_claims(led, r):
    """The claim itself plus claims decided together in the same adjudication (same program)."""
    g = adj_group(r)
    if not g:
        return [r]
    return [x for x in led.values() if adj_group(x) == g and x["employer"] == r["employer"]]


GUARD_WORDS = {"generated", "generate", "incremental", "annual", "arr", "additive", "drove", "caused",
               "sole", "predictive", "causal", "validated", "proven"}


def guards_for(r):
    """Ledger-stated prohibitions for one claim:
       words  - single terms after 'Never …' or 'not …' (e.g. EQ-04 'Never generated / incremental / annual')
       quotes - quoted 'Never' phrases (e.g. US-06 "Never 'I grew it 4.6x'") -> first-person verb patterns
       nots   - capitalised NOT phrases (e.g. EQ-05 'NOT a new predictive churn-risk model') -> bigrams"""
    src = " ".join([r.get("notes", ""), r.get("scope_and_attribution", ""), r.get("canonical_wording", "")])
    words, quotes, nots = set(), [], []
    for m in re.finditer(r"[Nn]ever (.+?)(?:\.(?=\s|$)|;|\]|$)", src):
        seg = m.group(1)
        for q in re.findall(r"'([^']{3,60})'", seg):
            quotes.append(q)
        for w in re.split(r"[/,]| or | and ", re.sub(r"'[^']*'", "", seg) + " " + " ".join(re.findall(r"'([^']{3,20})'", seg))):
            w = w.strip().strip("'\"").lower()
            if w in GUARD_WORDS:
                words.add(w)
    for m in re.finditer(r"\bnot (?:an? )?(?:new )?([a-z\-]+)", src.lower()):
        if m.group(1) in GUARD_WORDS:
            words.add(m.group(1))
    for m in re.finditer(r"\bNOT (?:an? |the )?([A-Za-z][A-Za-z \-/']{3,60}?)(?=[.;,)\]]|$)", src):
        toks = [t for t in re.split(r"[\s/\-]+", m.group(1).lower()) if t and t not in STOP]
        grams = [f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1)]
        if grams:
            nots.append((m.group(1).strip(), grams))
    return words, quotes, nots


def quote_pattern(q):
    """'I grew it 4.6x' -> regex for 'I grew' ; other quotes -> literal phrase."""
    m = re.match(r"I (\w+)", q)
    if m:
        return re.compile(r"\bI\s+" + re.escape(m.group(1)) + r"\b", re.I)
    return re.compile(re.escape(q), re.I)


def signoff_re(cfg):
    names = [re.escape(n) for n in (cfg.get("sender", {}).get("signoff_names") or [])]
    alt = "|".join(names + ["Thanks,?", "Best,?", "Thank you,?", "Cheers,?"])
    return re.compile(r"^\s*(" + alt + r")\s*$", re.I)


def split_body(text, cfg):
    body = []
    so = signoff_re(cfg)
    for ln in text.strip().splitlines():
        if PHONE_RE.search(ln) or "linkedin.com/in/" in ln.lower() or so.match(ln) or re.match(r"^\s*subject\s*:", ln, re.I):
            continue
        body.append(ln)
    return "\n".join(body).strip()


def sentences(text):
    # don't split after single-letter abbreviations ("U.S. Electrical", "e.g. this")
    return [s.strip() for s in re.split(r"(?<=[.?!])(?<!\b[A-Za-z]\.)\s+|\n+", text) if s.strip()]


def employers_in(s, aliases):
    sl = s.lower()
    return {e for e, al in aliases.items() if any(re.search(r"\b" + re.escape(a) + r"\b", sl) for a in al)}


def cmd_count(a, cfg):
    text = read_text(a)
    print(f"characters (incl. spaces/punctuation): {len(text)}")
    print("words:", len(re.findall(r"\S+", text)))


def read_text(a):
    if a.file:
        with open(a.file, encoding="utf-8") as f:
            t = f.read()
    else:
        t = a.text
    return t.rstrip("\n")


def evaluate(text, a, cfg, led):
    """Returns (blocks, warns, notes, stats). Pure function, used by validate and the test runners."""
    blocks, warns, notes = [], [], []
    ch, st = a.channel, a.status
    body = split_body(text, cfg)
    aliases = employer_aliases(led, cfg)
    words = len(re.findall(r"\S+", body))
    chars = len(text)
    sents = sentences(body)
    low = body.lower()

    # ---------- 1. channel and recipient decisions (BLOCK)
    li = cfg["linkedin"]
    hard_max = li["connection_note_hard_max"]
    acct = li.get("account_note_limit")
    if ch == "linkedin_note":
        limit = min(hard_max, acct) if acct else hard_max
        if chars > limit:
            blocks.append(f"Connection note is {chars} characters; the limit is {limit}.")
        elif not acct and chars > 200:
            warns.append((f"Note is {chars} characters; a free LinkedIn account cuts notes at 200.",
                          "Set linkedin.account_note_limit in your local config, or keep a ≤200 version ready."))
        if "\n\n" in text:
            warns.append(("Connection notes render as one block; paragraph breaks are lost.", "Write it as one paragraph."))
    if ch == "linkedin_inmail" and not li.get("inmail_allowed"):
        blocks.append("InMail is not an approved channel (config: linkedin.inmail_allowed = false).")
    if ch == "email":
        ec = getattr(a, "email_class", None)
        sendable = set(cfg["email"]["sendable_confidence_levels"])
        if not ec:
            blocks.append("First-contact email needs --email-class (confirmed | verified | pattern | risky | not_found).")
        elif ec not in sendable:
            blocks.append(f"Email address is '{ec}'. Only {sorted(sendable)} addresses may be emailed; use a LinkedIn connection request instead.")
    if getattr(a, "other_channel_active", False):
        blocks.append("This recipient already has an active touch on another channel. No simultaneous email and LinkedIn outreach.")
    pt = getattr(a, "prior_touches", 0) or 0
    if pt >= 2:
        blocks.append(f"{pt} prior touches to this recipient. The one follow-up is already spent; stop.")
    if pt == 1 and ch == "linkedin_note":
        blocks.append("A connection request cannot be a follow-up. No follow-up on an unaccepted request, and a switch to LinkedIn after email follows the channel-switch rule (use --touch switch).")
    if pt == 1 and getattr(a, "touch", "first") == "first":
        warns.append(("One prior touch exists, but --touch is 'first'.", "Mark it --touch follow_up, and make sure it adds something new."))

    # ---------- 2. application status (BLOCK: factual)
    if st == "not_applied" and re.search(r"\bI applied\b|\bapplied for\b|\bmy application\b|\bI've applied\b|\bI've since applied\b", body, re.I):
        blocks.append("Says the sender applied, but --status is not_applied.")
    if st == "not_applied" and re.search(r"\battached\b", body, re.I):
        warns.append(("Mentions an attachment before applying.", "Decide which résumé, if any, goes out pre-application."))

    # ---------- 3. claims: existence and use status (BLOCK)
    ids = [x.strip() for x in (a.claims or "").split(",") if x.strip()]
    claims = []
    for cid in ids:
        r = led.get(cid)
        if not r:
            blocks.append(f"Claim {cid} is not in the ledger."); continue
        if r["resume_use"] not in APPROVED_USE:
            blocks.append(f"Claim {cid} is '{r['resume_use']}' in the ledger and cannot support outreach.")
        claims.append(r)
    claim_nums = {r["claim_id"]: {n["key"] for n in numbers_in(claim_text(r), keep_small=True)} for r in claims}
    claim_wording_nums = {r["claim_id"]: {n["key"] for n in numbers_in(r.get("canonical_wording", ""), keep_small=True)} for r in claims}
    claim_stems = {r["claim_id"]: stems(r.get("canonical_wording", "") + " " + r.get("scope_and_attribution", "")) for r in claims}
    # document frequency across the whole ledger: common lifecycle words don't count as evidence of a match
    df = {}
    for r in led.values():
        for t in stems(r.get("canonical_wording", "")):
            df[t] = df.get(t, 0) + 1
    rare_cut = max(3, len(led) // 25)
    hooks = [h.strip() for h in (getattr(a, "hooks", "") or "").split(";") if h.strip()]
    hook_stems = [stems(h) for h in hooks]
    used_claims = set()

    # ---------- 4. sentence-level, context-aware checks
    for s in sents:
        s_core = GREETING_RE.sub("", s)
        s_low = s_core.lower()
        s_norm = re.sub(r"[\-/]", " ", s_low)
        figs = numbers_in(s_core)
        emps = employers_in(s_core, aliases)
        first_person = bool(FIRST_PERSON_ACTION.search(s_core))
        about_sender = first_person or bool(emps)
        st_ = stems(s_core)

        # which mapped claims does this sentence describe?
        matched = []
        for r in claims:
            cid = r["claim_id"]
            by_fig = any(f["key"] in claim_nums[cid] for f in figs if not f["year"])
            overlap = st_ & claim_stems[cid]
            rare = {t for t in overlap if df.get(t, 0) <= rare_cut}
            by_words = len(rare) >= 2 or len(overlap) >= 5
            by_emp = (r["employer"] in emps) and len([c for c in claims if c["employer"] == r["employer"]]) == 1 and first_person
            if by_fig or by_words or by_emp:
                matched.append(r)
        used_claims.update(r["claim_id"] for r in matched)
        hook_hit = any(len(st_ & hs) >= 2 for hs in hook_stems)

        # 4a. figures
        for f in figs:
            owners = [cid for cid, ks in claim_nums.items() if f["key"] in ks]
            if not owners:
                if about_sender or not claims:
                    if f["year"]:
                        warns.append((f"Year '{f['token']}' in: \"{s[:80]}\" is not in a mapped claim.", "Check it against the claim's period."))
                    elif about_sender:
                        blocks.append(f"Figure '{f['token']}' is not supported by any mapped claim ({', '.join(ids) or 'none mapped'}): \"{s[:90]}\"")
                    else:
                        warns.append((f"Figure '{f['token']}' is not about the sender's work: \"{s[:80]}\"", "Make sure the company's own figure is quoted accurately and sourced."))
                else:
                    warns.append((f"Figure '{f['token']}' does not appear in a mapped claim and the sentence doesn't read as the sender's work: \"{s[:80]}\"",
                                  "If it is the company's figure, confirm the source; if it is the sender's, map the claim."))
                continue
            if f["plus"] and not any((f["key"] + "+") in norm_num(claim_text(led[c])).lower() for c in owners):
                blocks.append(f"'{f['token']}' adds a '+' the ledger does not carry ({', '.join(owners)}).")
        # figures drawn from two unrelated claims in one sentence
        fig_owners = set()
        for f in figs:
            for cid, ks in claim_nums.items():
                if f["key"] in ks:
                    fig_owners.add(cid)
        groups = {adj_group(led[c]) or c for c in fig_owners}
        if len(groups) > 1:
            warns.append((f"One sentence combines figures from {', '.join(sorted(fig_owners))}: \"{s[:80]}\"",
                          "Ledger rule: never combine two true facts into one accomplishment. Split the sentence or confirm they describe one result."))

        # 4b. shaky quantities: a number that appears only in a flagged quantitative_result
        word_nums = [NUM_WORDS[w] for w in re.findall(r"[a-z]+", s_low) if w in NUM_WORDS]
        for r in matched:
            q = r.get("quantitative_result", "")
            if not q or not SHAKY_QUANT.search(q):
                continue
            q_nums = {n["key"] for n in numbers_in(q, keep_small=True)}
            for k in list({f["key"] for f in figs}) + word_nums:
                if k in q_nums and k not in claim_wording_nums[r["claim_id"]]:
                    blocks.append(f"Uses '{k}' from {r['claim_id']}'s quantitative note, which the ledger marks as \"{q[:90]}\". Leave it out.")

        # 4c. ledger guards: only for claims this sentence describes, plus same-program siblings
        if matched:
            scope = {}
            for r in matched:
                for x in related_claims(led, r):
                    scope[x["claim_id"]] = x
            for cid, r in scope.items():
                gw, gq, gn = guards_for(r)
                for w in gw:
                    if re.search(r"\b" + re.escape(w) + r"\b", s_low):
                        blocks.append(f"'{w}' is prohibited for {cid} (ledger: \"{(r.get('notes') or r.get('scope_and_attribution'))[:80]}…\"): \"{s[:90]}\"")
                for q in gq:
                    if quote_pattern(q).search(s_core):
                        blocks.append(f"Echoes the ledger's prohibited form for {cid} (Never '{q}'): \"{s[:90]}\"")
                for phrase, grams in gn:
                    if any(g in s_norm for g in grams):
                        blocks.append(f"{cid} says NOT '{phrase}', and this sentence describes that program that way: \"{s[:90]}\"")
            # measured-impact language must be supported by the claim itself
            for t in MEASURED_TERMS:
                if re.search(r"\b" + re.escape(t) + r"\b", s_low) and not re.search(r"\bno\b|\bnot\b|without", s_low):
                    ctext = " ".join(claim_text(r).lower() for r in matched)
                    negated = re.search(r"(no|not|without|prevented)[^.]{0,90}\b" + re.escape(t.split()[0]), ctext)
                    if t.split()[0] not in ctext or negated:
                        blocks.append(f"'{t}' asserts measured impact that {', '.join(r['claim_id'] for r in matched)} does not support: \"{s[:90]}\"")
            # findings the ledger marks unverified or credits to someone else
            if FINDING_LANG.search(s_core):
                for r in matched:
                    src = (r.get("notes", "") + " " + r.get("scope_and_attribution", "") + " " + r.get("quantitative_result", ""))
                    if UNVERIFIED_OUTCOME.search(src):
                        blocks.append(f"States as an observed finding what {r['claim_id']} marks unverified or as a hypothesis: \"{s[:90]}\"")
            # causal juxtaposition for claims the ledger says are not causally attributed
            for r in matched:
                src = (r.get("canonical_wording", "") + " " + r.get("notes", "") + " " + r.get("scope_and_attribution", "")).lower()
                if re.search(r"not (sole causation|attributed|causally attributed|caused)|causal language", src):
                    if re.search(r"\b(by|so|and then|which led|resulting|after which|, and)\b", s_low) and any(f["key"] in claim_nums[r["claim_id"]] for f in figs):
                        warns.append((f"{r['claim_id']} is not causally attributed, and this sentence may read as cause and effect: \"{s[:90]}\"",
                                      f"Keep the ledger's framing: {r.get('scope_and_attribution') or 'see notes'}"))
            # soft causal verbs
            for v in ["drove", "drive", "generated", "resulted in", "led to", "caused"]:
                if re.search(r"\b" + v + r"\b", s_low) and not any(v in guards_for(r)[0] for r in scope.values()):
                    warns.append((f"Causal verb '{v}' in a sentence about {', '.join(r['claim_id'] for r in matched)}.",
                                  "Confirm the claim's attribution supports it, or use the ledger's verb."))
        else:
            # 4d. accomplishment with no supporting claim
            if first_person and not hook_hit:
                past_sender = re.search(r"\b(I|we)\s+(?:also\s+)?(built|rebuilt|led|grew|designed|ran|launched|created|turned|redesigned|compared|routed|took over|managed|owned|drove|found|recovered|increased|reduced|cut|raised|migrated|delivered|generated|influenced|doubled|tripled|scaled|saved|worked|used)\b", s_core, re.I)
                if emps and past_sender:
                    blocks.append(f"Accomplishment at {', '.join(sorted(emps))} with no ledger claim mapped: \"{s[:100]}\". Map a claim, record it as a user-confirmed hook (--hooks), or cut it.")
                elif past_sender or emps:
                    warns.append((f"Reads as a claim about the sender's experience but maps to no ledger claim: \"{s[:90]}\"",
                                  "If it's a general capability statement, fine. If it describes specific work, map the claim."))
            if FINDING_LANG.search(s_core) and about_sender and not hook_hit:
                warns.append((f"Finding language with no mapped claim: \"{s[:90]}\"", "Map the claim that records the finding, or soften it."))
            if any(re.search(r"\b" + re.escape(t) + r"\b", s_low) for t in MEASURED_TERMS) and about_sender:
                blocks.append(f"Measured-impact language about the sender's work with no claim mapped: \"{s[:90]}\"")

    for r in claims:
        if r["claim_id"] not in used_claims:
            warns.append((f"Mapped claim {r['claim_id']} was not detected in any sentence.",
                          "Check the --claims list matches what the message says, or that wording hasn't drifted far from the ledger."))
        notes.append(f"{r['claim_id']}: preserve → {r.get('scope_and_attribution') or '(no scope note)'}")

    # ---------- 5. voice and style (WARN with suggestions)
    vs = cfg["voice_style"]
    for d in vs["dash_characters"]:
        if d in body:
            warns.append((f"Uses '{d}'. The configured voice avoids it.", "Use a comma or a period, unless the sentence truly needs the interruption."))
    for s in sents:
        s_clean = GREETING_RE.sub("", s)
        for op, sug in vs["subject_dropped_openers"].items():
            if s_clean.lower().startswith(op.lower()):
                warns.append((f"Drops 'I': \"{s[:70]}\"", f"The configured voice keeps 'I'. Try: {sug}"))
    for ph, sug in vs["style_flags"].items():
        if re.search(r"\b" + re.escape(ph) + r"\b", low):
            warns.append((f"'{ph}'", sug))
    qs = [s for s in sents if s.endswith("?")]
    if qs:
        ask = qs[-1]
        if vs.get("ask_should_contain_I") and not re.search(r"\bI\b|\bI'(d|m|ll|ve)\b|\bme\b|\bmy\b", ask):
            warns.append((f"The ask has no first person: \"{ask}\"", "Configured preference: phrase the ask with 'I' (\"I'd welcome…\", \"Could I…\")."))
        if len(qs) > 1:
            warns.append((f"{len(qs)} questions.", "Keep one ask; keep the ask that matters."))
        pos = body.rfind(ask) / max(len(body), 1)
        if pos < 0.6 and ch != "linkedin_note":
            warns.append(("The ask lands early.", "Asks should land late, about 85% of the way through."))
    elif ch not in ("linkedin_note",) and not re.search(r"\bI'd (like|love|welcome|appreciate)|\bif you're open\b|\bif you have\b", low):
        warns.append(("No clear ask found.", "End with one first-person ask."))
    gl = cfg["length_guidance_words"]
    cap = {"email": gl["email_first_contact"], "linkedin_message": gl["linkedin_message_after_accept"],
           "email_reply": gl["continuing_thread"], "linkedin_reply": gl["continuing_thread"]}.get(ch)
    if cap and words > cap:
        warns.append((f"{words} words; guidance for {ch} is about {cap}.", "Length should track how much context the reader already has."))
    if "!" in body and ch == "email":
        warns.append(("Exclamation mark in a cold email.", "Fine in warm threads; reconsider for first contact."))
    if re.search(r"\bRSF\b|Resume Signal Framework", text):
        warns.append(("Mentions RSF.", "Only for product- or AI-adjacent roles, and only as 'built and launched a public tool'; never users, revenue or adoption."))

    return blocks, warns, notes, {"chars": chars, "words": words}


def cmd_validate(a, cfg):
    text = read_text(a)
    led, lpath, lmtime = load_ledger(a.root, cfg)
    blocks, warns, notes, stats = evaluate(text, a, cfg, led)
    blocks = list(dict.fromkeys(blocks))
    seen, uw = set(), []
    for w in warns:
        if w[0] not in seen:
            seen.add(w[0]); uw.append(w)
    verdict = "BLOCKED" if blocks else ("PASS WITH WARNINGS" if uw else "PASS")
    print(f"VALIDATION: {verdict}   channel={a.channel}  status={a.status}")
    print(f"characters={stats['chars']}  body_words={stats['words']}  ledger={os.path.basename(lpath)} ({lmtime if lmtime.startswith('snapshot') else 'modified ' + lmtime})")
    for b in blocks:
        print(f"  BLOCK  {b}")
    for w, sug in uw:
        print(f"  WARN   {w}\n         → {sug}")
    if notes:
        print("  Claim qualifiers the human check must confirm:")
        for n_ in notes:
            print(f"    - {n_}")
    print("  Human checks: problem framing is quoted or labelled as a guess; nothing re-supplies context the reader already has;"
          " each claim keeps its scope (business unit, period, shared credit).")
    sys.exit(1 if blocks else 0)


# ---------------------------------------------------------------- log
def cmd_log_row(a, cfg):
    row = f"| {a.company} | {a.applied} | {a.contact} | {a.title} | {a.channel} | {a.date or ''} | {a.status_text} | {a.follow_up or ''} |"
    print(row)
    if a.append:
        p = rpath(a.root, cfg["paths"]["outreach_log"])
        with open(p, "a", encoding="utf-8") as f:
            f.write(row + "\n")
        print(f"Appended to {p}")


# ---------------------------------------------------------------- main
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="Career OS data folder (overrides $CAREER_OS_DIR and discovery)")
    ap.add_argument("--config", help="Config file (overrides the default resolution order)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("where")
    c = sp.add_parser("claims"); c.add_argument("--ids"); c.add_argument("--search"); c.add_argument("--employer")
    c.add_argument("--include-blocked", action="store_true")
    p = sp.add_parser("prior-contact"); p.add_argument("--name"); p.add_argument("--company")
    p.add_argument("--company-wide", action="store_true", help="With --name, also report any line mentioning the company")
    w = sp.add_parser("warm-paths"); w.add_argument("--company", required=True)
    for nm in ("count", "validate"):
        x = sp.add_parser(nm); g = x.add_mutually_exclusive_group(required=True)
        g.add_argument("--file"); g.add_argument("--text")
        if nm == "validate":
            add_validate_args(x)
    lr = sp.add_parser("log-row")
    for f_ in ("company", "applied", "contact", "title", "channel", "status-text"):
        lr.add_argument("--" + f_, required=True)
    lr.add_argument("--date"); lr.add_argument("--follow-up"); lr.add_argument("--append", action="store_true")
    return ap


def add_validate_args(x):
    x.add_argument("--channel", required=True,
                   choices=["email", "email_reply", "linkedin_note", "linkedin_message", "linkedin_reply", "linkedin_inmail"])
    x.add_argument("--status", required=True, choices=["not_applied", "applied", "in_process"])
    x.add_argument("--claims", default="", help="Comma-separated ledger claim IDs used in the message")
    x.add_argument("--hooks", default="", help="Semicolon-separated facts the user confirmed outside the ledger (worksheet HOOK)")
    x.add_argument("--email-class", choices=["confirmed", "verified", "pattern", "risky", "not_found"],
                   help="Confidence class of the address (required for channel=email)")
    x.add_argument("--prior-touches", type=int, default=0, help="Earlier touches to this recipient on any channel")
    x.add_argument("--touch", choices=["first", "follow_up", "switch"], default="first")
    x.add_argument("--other-channel-active", action="store_true", help="Recipient has an open touch on another channel")


def main():
    pre = argparse.ArgumentParser(add_help=False); pre.add_argument("--config"); pre.add_argument("--root")
    known, _ = pre.parse_known_args()
    cfg = load_config(known.config)
    a = build_parser().parse_args()
    a.trace = []
    a.root, a.root_source = discover_root(cfg, a.root, a.trace)
    {"where": cmd_where, "claims": cmd_claims, "prior-contact": cmd_prior_contact, "warm-paths": cmd_warm_paths,
     "count": cmd_count, "validate": cmd_validate, "log-row": cmd_log_row}[a.cmd](a, cfg)


if __name__ == "__main__":
    main()
