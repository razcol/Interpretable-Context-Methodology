#!/usr/bin/env python3
"""Print the exact subagent call fields for a harness and tier, or check the mapping.

  models.py pick  --harness {claude-code,cursor} --tier {mid,strong}
                  [--family {claude,grok}] [--hardest] [--retry]
  models.py check --harness {claude-code,cursor}

--retry raises the tier one step (mid -> strong, strong -> strong hardest).
For Grok in Cursor, strong hardest is claude-opus-5-5-high (no grok-4.7-xhigh).
Exit codes: 0 ok, 1 check found a problem, 2 bad request (unknown tier/family, banned value).
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


def load():
    with open(TIERS, encoding="utf-8") as fh:
        return json.load(fh)["harnesses"]


def banned(value, never):
    if FAST.search(value):
        return True
    return any(fnmatch.fnmatch(value, pat) for pat in never if "*" in pat or pat == value)


def entries(h):
    for tier in ("mid", "strong"):
        for variant, fields in h[tier].items():
            yield tier, variant, fields


def pick(args):
    h = load()[args.harness]
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
        sys.stderr.write(f"no {family} model for {args.harness} {tier}; "
                         f"available: {', '.join(variants)}\n")
        return 2
    fields = dict(variants[key])
    value = fields["model"]
    if banned(value, h.get("never", [])):
        sys.stderr.write(f"refusing banned value {value}\n")
        return 2
    print(f"# {args.harness} {tier}{' hardest' if hardest else ''} ({family}) via {h['tool']}")
    for k, v in fields.items():
        print(f"{k}: {v}")
    return 0


def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", out.stdout + out.stderr), None


def check(args):
    h = load()[args.harness]
    problems = 0
    for tier, variant, fields in entries(h):
        value = fields["model"]
        if banned(value, h.get("never", [])):
            print(f"FAIL {tier}/{variant}: {value} is banned")
            problems += 1
    if args.harness == "cursor":
        if not shutil.which("cursor-agent"):
            print("SKIP cursor-agent not on PATH; slugs not verified")
            return 1 if problems else 0
        text, err = run(["cursor-agent", "models"])
        if text is None:
            print(f"SKIP cursor-agent models failed: {err}")
            return 1 if problems else 0
        slugs = {line.split(" - ")[0].strip() for line in text.splitlines() if " - " in line}
        for tier, variant, fields in entries(h):
            ok = fields["model"] in slugs
            print(f"{'PASS' if ok else 'FAIL'} {tier}/{variant}: {fields['model']}")
            problems += not ok
    else:
        print("PASS claude-code: aliases sonnet/opus are fixed by the harness; nothing to list")
    return 1 if problems else 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pick")
    a.add_argument("--harness", required=True, choices=["claude-code", "cursor"])
    a.add_argument("--tier", required=True, choices=["mid", "strong"])
    a.add_argument("--family", choices=["claude", "grok"])
    a.add_argument("--hardest", action="store_true")
    a.add_argument("--retry", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--harness", required=True, choices=["claude-code", "cursor"])
    args = p.parse_args()
    return pick(args) if args.cmd == "pick" else check(args)


if __name__ == "__main__":
    sys.exit(main())
