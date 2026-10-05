#!/usr/bin/env python3
"""Print verified facts needed to write a session handoff document.

Usage: python3 gather_state.py "<topic words>" [--dir PATH]

Prints key: value lines:
  cwd, timestamp, slug, target_file, git_* (only inside a git repository).

target_file is collision-safe: if the name exists, a time suffix is added,
then seconds, then a counter. Nothing is written to disk.
Stdlib only. Works without git.
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50].strip("-") or "work"


def git(args, cwd):
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    # rstrip only: leading spaces are meaningful in `git status --short` columns
    return out.stdout.rstrip("\n") if out.returncode == 0 else None


def unique_name(directory: str, base: str, now: datetime) -> str:
    candidates = [
        f"{base}.md",
        f"{base}-{now:%H%M}.md",
        f"{base}-{now:%H%M%S}.md",
    ]
    for name in candidates:
        if not os.path.exists(os.path.join(directory, name)):
            return name
    n = 2
    while os.path.exists(os.path.join(directory, f"{base}-{now:%H%M%S}-{n}.md")):
        n += 1
    return f"{base}-{now:%H%M%S}-{n}.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", nargs="?", default="work")
    parser.add_argument("--dir", default=os.getcwd())
    args = parser.parse_args()

    directory = os.path.abspath(args.dir)
    now = datetime.now().astimezone()
    slug = slugify(args.topic)
    base = f"session-handoff-{now:%Y-%m-%d}-{slug}"

    print(f"cwd: {directory}")
    print(f"timestamp: {now.isoformat(timespec='seconds')}")
    print(f"slug: {slug}")
    print(f"target_file: {os.path.join(directory, unique_name(directory, base, now))}")

    if git(["rev-parse", "--is-inside-work-tree"], directory) == "true":
        branch = (git(["rev-parse", "--abbrev-ref", "HEAD"], directory) or "unknown").strip()
        head = (git(["rev-parse", "--short", "HEAD"], directory) or "no commits yet").strip()
        status = git(["status", "--short"], directory) or ""
        lines = [l for l in status.splitlines() if l.strip()]
        print(f"git_branch: {branch}")
        print(f"git_head: {head}")
        print(f"git_state: {'dirty' if lines else 'clean'} ({len(lines)} changed paths)")
        for line in lines[:40]:
            print(f"git_change: {line}")
        if len(lines) > 40:
            print(f"git_change: ... {len(lines) - 40} more")
    else:
        print("git: not a git repository")
    return 0


if __name__ == "__main__":
    sys.exit(main())
