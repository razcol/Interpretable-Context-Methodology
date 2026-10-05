#!/usr/bin/env python3
"""Check a handoff document for structure and sensitive content.

Usage: python3 check_handoff.py <handoff.md>

Exit codes: 0 = pass (warnings allowed), 1 = errors found, 2 = usage/file error.
Checks:
  - header fields present (Work status, Created, Working directory); Created must be
    a real ISO timestamp and not in the future
  - all 11 numbered sections present, in order, each non-empty
  - no unfilled template placeholders
  - secret-like patterns (errors) and personal-data-like patterns (warnings)
Pattern matching is a safety net, not a guarantee: still review by judgment.
Matched values are never printed, only the line number and rule name.
Stdlib only.
"""
import re
import sys
from datetime import datetime, timedelta, timezone

SECTIONS = [
    "Goal",
    "Status",
    "Work Breakdown",
    "Decisions",
    "Rejected Approaches",
    "Constraints and Preferences",
    "Files and Artifacts",
    "Commands and Results",
    "Open Questions and Blockers",
    "Next Steps",
    "Environment and Tooling",
]

HEADER_FIELDS = ["Work status", "Created", "Working directory"]
VALID_STATUS = re.compile(r"\*\*Work status:\*\*\s*(IN PROGRESS|BLOCKED|PAUSED)\b")

SECRET_RULES = [
    ("private-key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Atlassian/API token-like", re.compile(r"\bATATT[A-Za-z0-9_=-]{20,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("credentials in URL", re.compile(r"://[^/\s:@]+:[^/\s@]{3,}@")),
    (
        "secret assignment",
        re.compile(
            r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)"
            r"\b[\"']?\s*[:=]\s*[\"']?(?![$<{\[(])([^\s\"'`]{8,})"
        ),
    ),
]

WARN_RULES = [
    ("email address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone-like number", re.compile(r"(?<!\d)\+?\d[\d\s().-]{9,}\d(?!\d)")),
]

PLACEHOLDER = re.compile(r"<[^>\n]{2,80}>")
# Dates/timestamps look like phone numbers to a naive regex; remove them first.
DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?\s?(?:Z|[+-]\d{2}:?\d{2})?")


def strip_code_fences_for_placeholders(lines):
    """Yield (lineno, text) outside fenced code blocks and inline code."""
    in_fence = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        yield i, re.sub(r"`[^`]*`", "", line)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"ERROR cannot read file: {exc}")
        return 2

    lines = text.splitlines()
    errors, warnings = [], []

    for field in HEADER_FIELDS:
        if not re.search(rf"\*\*{re.escape(field)}:\*\*", text):
            errors.append(f"missing header field: {field}")
    if "**Work status:**" in text and not VALID_STATUS.search(text):
        errors.append("Work status must be exactly one of: IN PROGRESS, BLOCKED, PAUSED")

    created = re.search(r"\*\*Created:\*\*\s*(.+)", text)
    if created:
        raw = created.group(1).strip()
        try:
            stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                warnings.append("Created has no timezone; use the timestamp printed by gather_state.py")
            elif stamp > datetime.now(timezone.utc) + timedelta(minutes=2):
                errors.append("Created timestamp is in the future; use the system timestamp, do not type one from memory")
        except ValueError:
            warnings.append("Created is not an ISO-8601 timestamp; paste the value printed by gather_state.py")

    # sections: present, ordered, non-empty
    positions = {}
    for idx, line in enumerate(lines):
        m = re.match(r"^## (\d+)\.\s+(.*?)\s*$", line)
        if m:
            positions[(int(m.group(1)), m.group(2))] = idx
    last = -1
    for n, name in enumerate(SECTIONS, 1):
        pos = positions.get((n, name))
        if pos is None:
            errors.append(f"missing section: '## {n}. {name}'")
            continue
        if pos < last:
            errors.append(f"section out of order: '## {n}. {name}'")
        last = max(last, pos)
        nxt = [p for p in positions.values() if p > pos]
        end = min(nxt) if nxt else len(lines)
        body = [l for l in lines[pos + 1:end] if l.strip() and not l.strip().startswith("<!--")]
        if not body:
            errors.append(f"empty section (write 'None.' and why): '## {n}. {name}'")

    for lineno, line in strip_code_fences_for_placeholders(lines):
        if PLACEHOLDER.search(line):
            errors.append(f"line {lineno}: unfilled placeholder {PLACEHOLDER.search(line).group(0)[:40]!r}")

    for lineno, line in enumerate(lines, 1):
        for name, rx in SECRET_RULES:
            if rx.search(line):
                errors.append(f"line {lineno}: possible secret ({name}); value not shown")
        scrubbed = DATETIME.sub("", line)
        for name, rx in WARN_RULES:
            if rx.search(scrubbed):
                warnings.append(f"line {lineno}: possible personal data ({name}); keep only if essential")

    for e in errors:
        print(f"ERROR {e}")
    for w in warnings:
        print(f"WARN  {w}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: structure complete, no secret patterns found ({len(warnings)} warning(s))")
    print("Reminder: pattern checks are a safety net. Re-read the document for anything sensitive they cannot detect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
