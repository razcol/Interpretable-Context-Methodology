#!/usr/bin/env python3
"""Print the exact subagent call fields for a harness and tier, or check the mapping.

  models.py pick  --harness {claude-code,cursor} --tier {mid,strong}
                  [--family {claude,grok}] [--hardest] [--retry]
                  [--available SLUG,SLUG,...] [--json]
  models.py check --harness {claude-code,cursor}

Every slot in tiers.json is a ranked list of at most 3: the primary call fields plus
"fallbacks", best fit first. pick prints the primary and the ordered fallbacks. With
--available it picks the first of the 3 whose model is in that set and lists only the
later available ones as fallbacks; when none of the 3 is available it exits 2.
--retry raises the tier one step (mid -> strong, strong -> strong hardest).
For Grok in Cursor, strong hardest is claude-opus-5-5-high (no grok-4.7-xhigh).
check verifies every primary and fallback: never below mid, never in "never", and for
cursor listed by `cursor-agent models`. When that command fails or lists nothing
(offline, sandboxed) it prints SKIP and does not fail the slugs.
Exit codes: 0 ok, 1 check found a problem, 2 bad request (unknown tier/family, banned
value, none of the top 3 available).
Standard library only.
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TIERS = os.path.join(HERE, "..", "references", "tiers.json")
FAST = re.compile(r"(^fast$|-fast$|^auto$|^inherit$|^composer-|haiku)")
BELOW_MID = re.compile(r"-(none|minimal|low)$")
EFFORTS = ("medium", "high", "xhigh", "max")
MAX_RANKED = 3
ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
SLUG_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s+-\s+\S")


def load():
    with open(TIERS, encoding="utf-8") as fh:
        return json.load(fh)["harnesses"]


def banned(value, never):
    if FAST.search(value) or BELOW_MID.search(value):
        return True
    return any(fnmatch.fnmatch(value, pat) for pat in never if "*" in pat or pat == value)


def entries(h):
    for tier in ("mid", "strong"):
        for variant, fields in h[tier].items():
            yield tier, variant, fields


def ranked(fields):
    primary = {k: v for k, v in fields.items() if k != "fallbacks"}
    return [primary] + [dict(f) for f in fields.get("fallbacks", [])]


def floor_problems(entry, harness, never):
    model = entry.get("model")
    if not model:
        return ["no model"]
    why = []
    if banned(model, never):
        why.append(f"{model} is banned")
    effort = entry.get("effort")
    if harness == "claude-code" and effort is None:
        why.append("no effort")
    if effort is not None and effort not in EFFORTS:
        why.append(f"effort {effort} is below mid")
    if not entry.get("subagent_type"):
        why.append("no subagent_type")
    return why


def slot_for(h, args):
    tier, hardest = args.tier, args.hardest
    if args.retry:
        if tier == "mid":
            tier = "strong"
        else:
            hardest = True
    family = args.family or "claude"
    key = "default" if family == "claude" else family
    if hardest:
        key = "hardest" if key == "default" else key + "-hardest"
    variants = h[tier]
    if key not in variants:  # no hardest variant -> plain one
        key = key.replace("-hardest", "").replace("hardest", "default")
    if key not in variants:
        return None, (f"no {family} model for {args.harness} {tier}; "
                      f"available: {', '.join(variants)}")
    return (tier, hardest, family, key), None


def pick(args):
    h = load()[args.harness]
    slot, err = slot_for(h, args)
    if err:
        sys.stderr.write(err + "\n")
        return 2
    tier, hardest, family, key = slot
    never = h.get("never", [])
    chain = ranked(h[tier][key])
    for entry in chain:
        why = floor_problems(entry, args.harness, never)
        if why:
            sys.stderr.write(f"refusing {tier}/{key} in tiers.json: {'; '.join(why)} (run check)\n")
            return 2
    skipped = []
    if args.available is not None:
        available = {s.strip() for s in args.available.split(",") if s.strip()}
        skipped = [e["model"] for e in chain if e["model"] not in available]
        chain = [e for e in chain if e["model"] in available]
        if not chain:
            sys.stderr.write(f"none of the top {len(skipped)} for {args.harness} {tier}/{key} is available "
                             f"({', '.join(skipped)}); do not go below mid or to a fast model, report it\n")
            return 2
    chosen, fallbacks = chain[0], chain[1:]
    if args.json:
        print(json.dumps({"harness": args.harness, "tool": h["tool"], "slot": f"{tier}/{key}",
                          "call": chosen, "fallbacks": fallbacks, "skipped": skipped}, indent=2))
        return 0
    print(f"# {args.harness} {tier}{' hardest' if hardest else ''} ({family}) via {h['tool']}")
    if skipped:
        print(f"# not available, skipped: {', '.join(skipped)}")
    for k, v in chosen.items():
        print(f"{k}: {v}")
    print(f"fallbacks: {json.dumps(fallbacks)}")
    return 0


def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, None, str(exc)
    return ANSI.sub("", out.stdout + out.stderr), out.returncode, None


def parse_slugs(text):
    return {m.group(1) for m in map(SLUG_LINE.match, text.splitlines()) if m}


def first_line(text):
    return next((line.strip()[:200] for line in text.splitlines() if line.strip()), "no output")


def check(args):
    h = load()[args.harness]
    never = h.get("never", [])
    problems = 0
    rows = []
    for tier, variant, fields in entries(h):
        chain = ranked(fields)
        if len(chain) > MAX_RANKED:
            print(f"FAIL {tier}/{variant}: {len(chain)} ranked entries, at most {MAX_RANKED}")
            problems += 1
        seen = set()
        for i, entry in enumerate(chain):
            name = f"{tier}/{variant}" + (f" fallback {i}" if i else "")
            why = floor_problems(entry, args.harness, never)
            ident = (entry.get("model"), entry.get("effort"))
            if ident in seen:
                why.append("repeats an earlier entry in the same slot")
            seen.add(ident)
            if why:
                print(f"FAIL {name}: {'; '.join(why)}")
                problems += 1
            rows.append((name, entry, not why))
    if not problems:
        print(f"PASS floor: {len(rows)} ranked entries, none below mid or in never")
    if args.harness == "cursor":
        if not shutil.which("cursor-agent"):
            print("SKIP: cursor-agent not on PATH; slugs not verified")
            return 1 if problems else 0
        text, code, err = run(["cursor-agent", "models"])
        slugs = parse_slugs(text or "")
        if text is None:
            reason = err
        elif code != 0:
            reason = f"exit {code}: {first_line(text)}"
        elif not slugs:
            reason = f"no slugs listed: {first_line(text)}"
        else:
            reason = None
        if reason:
            print(f"SKIP: cursor-agent models unavailable ({reason})")
            return 1 if problems else 0
        for name, entry, floor_ok in rows:
            listed = entry.get("model") in slugs
            ok = listed and floor_ok
            note = "" if listed else " (not in cursor-agent models)"
            print(f"{'PASS' if ok else 'FAIL'} {name}: {entry.get('model')}{note}")
            problems += not listed
    else:
        print("PASS claude-code: aliases sonnet/opus are fixed by the harness; nothing to list")
    return 1 if problems else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pick")
    a.add_argument("--harness", required=True, choices=["claude-code", "cursor"])
    a.add_argument("--tier", required=True, choices=["mid", "strong"])
    a.add_argument("--family", choices=["claude", "grok"])
    a.add_argument("--hardest", action="store_true")
    a.add_argument("--retry", action="store_true")
    a.add_argument("--available", metavar="SLUG,SLUG,...",
                   help="models the harness has enabled; pick the first of the ranked 3 in this set")
    a.add_argument("--json", action="store_true", help="print the pick as JSON")
    c = sub.add_parser("check")
    c.add_argument("--harness", required=True, choices=["claude-code", "cursor"])
    args = p.parse_args(argv)
    return pick(args) if args.cmd == "pick" else check(args)


if __name__ == "__main__":
    sys.exit(main())
