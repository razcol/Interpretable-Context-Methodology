#!/usr/bin/env python3
"""Print the exact subagent call fields for a harness and tier, or check the mapping.

  models.py pick  --harness {claude-code,cursor} --tier {light,mid,strong}
                  [--hardest] [--retry] [--readonly]
                  [--available SLUG,SLUG,...] [--json]
  models.py table --harness {claude-code,cursor}
                  [--readonly] [--available SLUG,SLUG,...] [--json]
  models.py check --harness {claude-code,cursor}

Every slot in tiers.json is a ranked list of at most 3: the primary call fields plus
"fallbacks", best fit first. Walk the list in order for availability fallback.
--retry steps up one quality tier: light -> mid -> strong -> strong/hardest.
Retrying past strong/hardest exits 2 (escalation ceiling reached; stop and report).
table resolves all slots (light, mid, strong, strong/hardest) in one call at run start.
check verifies every primary and fallback: valid effort for tier, never in "never",
distinct retry primaries, and for cursor listed by `cursor-agent models`. When that
command fails or lists nothing (offline, sandboxed) it prints SKIP and does not fail
the slugs.
Exit codes: 0 ok, 1 check found a problem, 2 bad request (unknown tier, ceiling
reached, banned value, none of the top 3 available).
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
TIER_ORDER = ("light", "mid", "strong")
ALWAYS_BANNED = re.compile(r"(^fast$|-fast$|^auto$|^inherit$|-(none|minimal)$)")
EFFORTS_BY_TIER = {
    "light": ("low", "medium", "high"),
    "mid": ("medium", "high", "xhigh", "max"),
    "strong": ("medium", "high", "xhigh", "max"),
}
MAX_RANKED = 3
ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
SLUG_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s+-\s+\S")


def load():
    with open(TIERS, encoding="utf-8") as fh:
        return json.load(fh)["harnesses"]


def banned(value, never):
    if ALWAYS_BANNED.search(value):
        return True
    return any(fnmatch.fnmatch(value, pat) for pat in never if "*" in pat or pat == value)


def entries(h):
    for tier in TIER_ORDER:
        if tier in h:
            for variant, fields in h[tier].items():
                yield tier, variant, fields


def ranked(fields, readonly_type=None):
    primary = {k: v for k, v in fields.items() if k != "fallbacks"}
    chain = [primary] + [dict(f) for f in fields.get("fallbacks", [])]
    if readonly_type:
        for entry in chain:
            entry["subagent_type"] = readonly_type
    return chain


def floor_problems(entry, tier, harness, never):
    model = entry.get("model")
    if not model:
        return ["no model"]
    why = []
    if banned(model, never):
        why.append(f"{model} is banned")
    effort = entry.get("effort")
    if harness == "claude-code" and effort is None:
        why.append("no effort")
    allowed_efforts = EFFORTS_BY_TIER.get(tier, ("medium", "high", "xhigh", "max"))
    if effort is not None and effort not in allowed_efforts:
        why.append(f"effort {effort} is not allowed for {tier}")
    if not entry.get("subagent_type"):
        why.append("no subagent_type")
    return why


def slot_for(h, tier, hardest=False, retry=False):
    if hardest and tier != "strong":
        return None, f"--hardest only applies to --tier strong (got {tier})"
    if retry:
        if tier == "light":
            tier = "mid"
        elif tier == "mid":
            tier = "strong"
        elif tier == "strong" and not hardest:
            hardest = True
        else:
            return None, "already at escalation ceiling (strong/hardest); stop and report instead of retrying"
    key = "hardest" if hardest else "default"
    variants = h.get(tier, {})
    if key not in variants:
        return None, f"no {tier}/{key} slot in tiers.json"
    return (tier, hardest, key), None


def resolve_slot(h, harness, tier, hardest=False, readonly=False, available_set=None):
    key = "hardest" if hardest else "default"
    never = h.get("never", [])
    ro_type = h.get("readonly_subagent_type") if readonly else None
    chain = ranked(h[tier][key], readonly_type=ro_type)
    for entry in chain:
        why = floor_problems(entry, tier, harness, never)
        if why:
            return None, f"refusing {tier}/{key} in tiers.json: {'; '.join(why)} (run check)"
    skipped = []
    if available_set is not None:
        skipped = [e["model"] for e in chain if e["model"] not in available_set]
        chain = [e for e in chain if e["model"] in available_set]
        if not chain:
            return None, (f"none of the top {len(skipped)} for {harness} {tier}/{key} is available "
                          f"({', '.join(skipped)}); do not pick outside the slot, report it")
    return {"slot": f"{tier}/{key}", "call": chain[0], "fallbacks": chain[1:], "skipped": skipped}, None


def parse_available(raw):
    if raw is None:
        return None
    return {s.strip() for s in raw.split(",") if s.strip()}


def pick(args):
    h = load()[args.harness]
    slot, err = slot_for(h, args.tier, hardest=args.hardest, retry=args.retry)
    if err:
        sys.stderr.write(err + "\n")
        return 2
    tier, hardest, _ = slot
    resolved, err = resolve_slot(h, args.harness, tier, hardest=hardest,
                                 readonly=args.readonly,
                                 available_set=parse_available(args.available))
    if err:
        sys.stderr.write(err + "\n")
        return 2
    if args.json:
        print(json.dumps({"harness": args.harness, "tool": h["tool"], **resolved}, indent=2))
        return 0
    print(f"# {args.harness} {tier}{' hardest' if hardest else ''} via {h['tool']}")
    if resolved["skipped"]:
        print(f"# not available, skipped: {', '.join(resolved['skipped'])}")
    for k, v in resolved["call"].items():
        print(f"{k}: {v}")
    print(f"fallbacks: {json.dumps(resolved['fallbacks'])}")
    return 0


def table(args):
    h = load()[args.harness]
    avail = parse_available(args.available)
    slots = [("light", False), ("mid", False), ("strong", False), ("strong", True)]
    out = {}
    errors = []
    for tier, hardest in slots:
        res, err = resolve_slot(h, args.harness, tier, hardest=hardest,
                                readonly=args.readonly, available_set=avail)
        label = f"{tier}/{'hardest' if hardest else 'default'}"
        if err:
            errors.append(err)
        else:
            out[label] = res
    if errors:
        for e in errors:
            sys.stderr.write(e + "\n")
        return 2
    if args.json:
        print(json.dumps({"harness": args.harness, "tool": h["tool"], "slots": out}, indent=2))
        return 0
    print(f"# {args.harness} tiers via {h['tool']}")
    for label, res in out.items():
        call = res["call"]
        eff = f" ({call['effort']})" if "effort" in call else ""
        fbs = ", ".join(f["model"] + (f"/{f['effort']}" if "effort" in f else "") for f in res["fallbacks"]) or "none"
        print(f"{label:15s} -> {call['model']}{eff} [{call['subagent_type']}]  fallbacks: {fbs}")
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
    primaries = {}
    for tier, variant, fields in entries(h):
        chain = ranked(fields)
        if len(chain) > MAX_RANKED:
            print(f"FAIL {tier}/{variant}: {len(chain)} ranked entries, at most {MAX_RANKED}")
            problems += 1
        seen = set()
        for i, entry in enumerate(chain):
            name = f"{tier}/{variant}" + (f" fallback {i}" if i else "")
            why = floor_problems(entry, tier, args.harness, never)
            ident = (entry.get("model"), entry.get("effort"))
            if ident in seen:
                why.append("repeats an earlier entry in the same slot")
            seen.add(ident)
            if i == 0:
                primaries[(tier, variant)] = ident
            if why:
                print(f"FAIL {name}: {'; '.join(why)}")
                problems += 1
            rows.append((name, entry, not why))
    # Verify retry steps strictly change primary
    escalation_pairs = [
        (("light", "default"), ("mid", "default")),
        (("mid", "default"), ("strong", "default")),
        (("strong", "default"), ("strong", "hardest")),
    ]
    for src, dst in escalation_pairs:
        if src in primaries and dst in primaries and primaries[src] == primaries[dst]:
            print(f"FAIL escalation {src[0]}/{src[1]} -> {dst[0]}/{dst[1]}: identical primary {primaries[src]}")
            problems += 1
    if not problems:
        print(f"PASS floor: {len(rows)} ranked entries, none banned, escalation primaries distinct")
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
        print("PASS claude-code: aliases haiku/sonnet/opus are fixed by the harness; nothing to list")
    return 1 if problems else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pick")
    a.add_argument("--harness", required=True, choices=["claude-code", "cursor"])
    a.add_argument("--tier", required=True, choices=list(TIER_ORDER))
    a.add_argument("--hardest", action="store_true")
    a.add_argument("--retry", action="store_true")
    a.add_argument("--readonly", action="store_true",
                   help="use the harness read-only subagent type (explore / Explore)")
    a.add_argument("--available", metavar="SLUG,SLUG,...",
                   help="models the harness has enabled; pick the first of the ranked 3 in this set")
    a.add_argument("--json", action="store_true", help="print the pick as JSON")

    t = sub.add_parser("table")
    t.add_argument("--harness", required=True, choices=["claude-code", "cursor"])
    t.add_argument("--readonly", action="store_true")
    t.add_argument("--available", metavar="SLUG,SLUG,...")
    t.add_argument("--json", action="store_true")

    c = sub.add_parser("check")
    c.add_argument("--harness", required=True, choices=["claude-code", "cursor"])
    args = p.parse_args(argv)
    if args.cmd == "pick":
        return pick(args)
    if args.cmd == "table":
        return table(args)
    return check(args)


if __name__ == "__main__":
    sys.exit(main())
