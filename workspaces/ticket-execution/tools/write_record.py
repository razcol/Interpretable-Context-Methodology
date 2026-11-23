#!/usr/bin/env python3
"""Write one stage's record when the Write tool cannot reach the data root (a chat rooted in the app repo).

Usage:
  write_record.py --stage <01..07 or 03b> --key <KEY> [--data-root DIR] < record

The record text comes from stdin. There is no record path argument: the target is
<data root>/workspaces/ticket-execution/runs/<KEY>/<NN-name>/<record>, with the record
name fixed per stage (the table in shared/run-records.md; stage 03b writes
<KEY>/03b-baseline/baseline-record.md). The data root is what
_core/data-root/data_root.py resolve prints for this ai-system checkout (--data-root
overrides it, for tests). The folder is created when missing, and the whole file is
replaced atomically.

Prints one JSON object. Exit codes: 0 written, 2 refused (unknown stage, bad key, no
data root, or a target that resolves outside the run's <KEY>/<NN-name>/ folder, a
symlink included), 3 empty content or no `version: N` line in the first five lines.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
HELPER = WS.parent.parent / "_core" / "data-root" / "data_root.py"
RECORDS = {
    "01": ("01-intake", "intake.md"),
    "02": ("02-research", "research.md"),
    "03": ("03-plan", "plan.md"),
    "03b": ("03b-baseline", "baseline-record.md"),
    "04": ("04-implement", "implement-record.md"),
    "05": ("05-verify", "verify-report.md"),
    "06": ("06-handoff", "handoff.md"),
    "07": ("07-release", "release-record.md"),
}
KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-\d+")
VERSION_RE = re.compile(r"^version: \d+")


def out(code=0, **data):
    print(json.dumps({"ok": code == 0, **data}, ensure_ascii=False))
    sys.exit(code)


def data_root(given):
    """The data checkout, with symlinks resolved, so the containment check below is exact."""
    if given:
        root = Path(os.path.expanduser(given))
    else:
        if not HELPER.is_file():
            out(2, error=f"no data-root helper at {HELPER}; pass --data-root")
        r = subprocess.run([sys.executable, str(HELPER), "resolve"], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            out(2, error="no data root: " + (r.stderr.strip() or "resolve printed nothing") + " (run setup)")
        root = Path(r.stdout.strip())
    if not root.is_dir():
        out(2, error=f"data root {root} is not a folder (run setup)")
    return Path(os.path.realpath(root))


def contained(folder, target):
    return os.path.realpath(folder) == str(folder) and os.path.realpath(target) == str(target)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True, help="stage id: two digits, 01 to 07, or 03b (baseline)")
    ap.add_argument("--key", required=True, help="Jira key, for example NSS-8")
    ap.add_argument("--data-root", help="data checkout to write into (default: data_root.py resolve)")
    args = ap.parse_args()

    if args.stage not in RECORDS:
        out(2, error=f"unknown stage {args.stage!r}; expected one of {', '.join(RECORDS)}")
    if not KEY_RE.fullmatch(args.key):
        out(2, error="key must look like ABC-123")
    stage_dir, record = RECORDS[args.stage]
    if not (WS / "stages" / stage_dir).is_dir():
        out(2, error=f"no stage folder stages/{stage_dir}")
    runs = data_root(args.data_root) / "workspaces" / WS.name / "runs"
    folder = runs / args.key / stage_dir
    target = folder / record
    if not contained(folder, target):
        out(2, error=f"target resolves outside runs/{args.key}/{stage_dir}/")

    text = sys.stdin.read()
    if not text.strip():
        out(3, error="empty record on stdin")
    if not any(VERSION_RE.match(line) for line in text.splitlines()[:5]):
        out(3, error="no `version: N` line in the first five lines")

    folder.mkdir(parents=True, exist_ok=True)
    if not contained(folder, target):
        out(2, error=f"target resolves outside runs/{args.key}/{stage_dir}/")
    replaced = target.exists()
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=f".{record}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    out(0, path=str(target), bytes=len(text.encode("utf-8")), replaced=replaced)


if __name__ == "__main__":
    main()
