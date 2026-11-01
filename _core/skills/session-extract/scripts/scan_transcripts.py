#!/usr/bin/env python3
"""Index Cursor agent transcripts under ~/.cursor/projects for marker matches.

Prints JSON lines to stdout. The first line is a coverage object. Each later
line is one matching transcript. Excerpts are redacted and truncated.

Stdlib only. Does not read state.vscdb, chat sqlite, or agent-store databases.
A zero-match run exits 0. A bad regex or a missing projects root exits 2.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
USER_QUERY = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)
TIMESTAMP = re.compile(r"<timestamp>\s*(.*?)\s*</timestamp>", re.DOTALL)
TOOL_NAME = re.compile(
    r'"type"\s*:\s*"tool_use"\s*,\s*"name"\s*:\s*"([^"\\]+)"'
)
ROLE = re.compile(r'"role"\s*:\s*"(user|assistant)"')

# A single jsonl line above this size is counted and skipped, not parsed.
MAX_LINE = 20_000_000
MAX_EXCERPTS = 3

REDACTIONS = [
    (re.compile(r"figd_[A-Za-z0-9_\-]+"), "[REDACTED_FIGMA_TOKEN]"),
    (re.compile(r"Bearer\s+\S+", re.IGNORECASE), "Bearer [REDACTED]"),
    (
        re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),
        "[REDACTED_JWT]",
    ),
    (re.compile(r"(?i)(password\s*[=:]\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"data:[^\s;]{0,64};base64,[A-Za-z0-9+/=\s]{20,}"), "[REDACTED_DATA_URL]"),
    (re.compile(r"[A-Za-z0-9+/]{100,}={0,2}"), "[REDACTED_BASE64]"),
]


def projects_root() -> Path:
    return Path.home() / ".cursor" / "projects"


def redact(text: str) -> str:
    if "store.json" in text and len(text) > 400:
        return "[store.json body omitted]"
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def one_excerpt(text: str, limit: int) -> str:
    cleaned = redact(" ".join(text.split()))
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def compile_patterns(raw):
    compiled = []
    for item in raw:
        try:
            compiled.append(re.compile(item))
        except re.error as exc:
            print(f"bad regex {item!r}: {exc}", file=sys.stderr)
            sys.exit(2)
    return compiled


def iter_transcripts(root: Path, slugs, include_subagents):
    """Yield (project, uuid, path, kind, parent_uuid)."""
    if not root.is_dir():
        print(f"projects root not found: {root}", file=sys.stderr)
        sys.exit(2)

    names = sorted(p.name for p in root.iterdir() if p.is_dir())
    if slugs:
        wanted = set(slugs)
        missing = sorted(wanted - set(names))
        names = [name for name in names if name in wanted]
    else:
        missing = []

    for name in names:
        transcripts = root / name / "agent-transcripts"
        if not transcripts.is_dir():
            continue
        for folder in sorted(p for p in transcripts.iterdir() if p.is_dir()):
            if not UUID.match(folder.name):
                continue
            parent = folder / f"{folder.name}.jsonl"
            if parent.is_file():
                yield name, folder.name, parent, "parent", None
            else:
                yield name, folder.name, None, "orphan", None
            if include_subagents:
                sub = folder / "subagents"
                if sub.is_dir():
                    for child in sorted(sub.glob("*.jsonl")):
                        yield name, child.stem, child, "subagent", folder.name


def text_from_record(line: str):
    """Return (role or None, plain text, tool names) from one jsonl line."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None, line, TOOL_NAME.findall(line)
    role = obj.get("role") if isinstance(obj, dict) else None
    message = obj.get("message") if isinstance(obj, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    texts = []
    tools = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                texts.append(block["text"])
            elif block.get("type") == "tool_use" and isinstance(block.get("name"), str):
                tools.append(block["name"])
    if not tools:
        tools = TOOL_NAME.findall(line)
    return role, "\n".join(texts), tools


def scan_file(path: Path, patterns, max_excerpt: int):
    matched = []
    excerpts = []
    tools = []
    seen_tools = set()
    roles = {"user": 0, "assistant": 0}
    timestamp = None
    lines_skipped = 0
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"error": str(exc)}

    with handle:
        for line in handle:
            if len(line) > MAX_LINE:
                lines_skipped += 1
                continue
            role, text, line_tools = text_from_record(line)
            if role in roles:
                roles[role] += 1
            elif role is None:
                for found in ROLE.findall(line):
                    roles[found] += 1
            if timestamp is None and text:
                found = TIMESTAMP.search(text)
                if found:
                    timestamp = " ".join(found.group(1).split())[:120]
            for name in line_tools:
                if name not in seen_tools:
                    seen_tools.add(name)
                    tools.append(name)
            if role == "user" and len(excerpts) < MAX_EXCERPTS:
                queries = USER_QUERY.findall(text) or ([text] if text.strip() else [])
                for query in queries:
                    if len(excerpts) >= MAX_EXCERPTS:
                        break
                    excerpts.append(one_excerpt(query, max_excerpt))
            # Match the raw line, same as a file search: tool arguments count.
            # Excerpts stay limited to decoded user text.
            hits = [item.pattern for item in patterns if item.search(line)]
            for hit in hits:
                if hit not in matched:
                    matched.append(hit)

    stat = path.stat()
    return {
        "matched": matched,
        "excerpts": excerpts,
        "tools": tools[:40],
        "roles": roles,
        "timestamp": timestamp,
        "lines_skipped": lines_skipped,
        "bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pattern",
        action="append",
        required=True,
        help="Regex matched against transcript text. Repeat for more markers.",
    )
    parser.add_argument(
        "--project",
        action="append",
        default=[],
        help="Limit to one project slug (directory name under ~/.cursor/projects). Repeatable.",
    )
    parser.add_argument(
        "--include-subagents",
        action="store_true",
        help="Also scan agent-transcripts/<uuid>/subagents/*.jsonl.",
    )
    parser.add_argument(
        "--max-excerpt",
        type=int,
        default=500,
        help="Max characters per user excerpt after redaction (default 500).",
    )
    args = parser.parse_args()
    if args.max_excerpt < 40:
        print("--max-excerpt must be at least 40", file=sys.stderr)
        sys.exit(2)

    patterns = compile_patterns(args.pattern)
    root = projects_root()

    coverage = {
        "type": "coverage",
        "projects_root": str(root),
        "slug_count": 0,
        "parent_count": 0,
        "orphan_count": 0,
        "files_scanned": 0,
        "files_matched": 0,
        "files_skipped_error": 0,
        "lines_skipped_size": 0,
        "include_subagents": args.include_subagents,
        "missing_projects": [],
        "orphans": [],
        "stores_not_read": [
            "state.vscdb",
            "~/.cursor/chats/*/store.db",
            "agent-store sqlite",
            "conversation-search.db",
        ],
    }

    slugs_seen = set()
    matches = []
    requested = args.project
    if root.is_dir() and requested:
        existing = {p.name for p in root.iterdir() if p.is_dir()}
        coverage["missing_projects"] = sorted(set(requested) - existing)

    for project, uuid, path, kind, parent_uuid in iter_transcripts(
        root, requested, args.include_subagents
    ):
        slugs_seen.add(project)
        if kind == "orphan":
            coverage["orphan_count"] += 1
            if len(coverage["orphans"]) < 30:
                coverage["orphans"].append({"project": project, "uuid": uuid})
            continue
        if kind == "parent":
            coverage["parent_count"] += 1
        coverage["files_scanned"] += 1
        result = scan_file(path, patterns, args.max_excerpt)
        if "error" in result:
            coverage["files_skipped_error"] += 1
            continue
        coverage["lines_skipped_size"] += result["lines_skipped"]
        if not result["matched"]:
            continue
        coverage["files_matched"] += 1
        row = {
            "type": "match",
            "project": project,
            "uuid": uuid,
            "kind": kind,
            "path": str(path),
            "bytes": result["bytes"],
            "mtime": result["mtime"],
            "timestamp": result["timestamp"],
            "roles": result["roles"],
            "patterns": result["matched"],
            "tools": result["tools"],
            "excerpts": result["excerpts"],
        }
        if parent_uuid:
            row["parent_uuid"] = parent_uuid
        matches.append(row)

    coverage["slug_count"] = len(slugs_seen)
    print(json.dumps(coverage, ensure_ascii=False))
    for row in matches:
        print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
