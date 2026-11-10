#!/usr/bin/env python3
"""Check a written session debrief for structure, length and sensitive content.

Usage: python3 check_debrief.py <file.md>

Prints `ERROR <line>: <rule>` and `WARN <line>: <rule>` lines, then `OK` or
`FAIL (n errors)`. Exit codes: 0 = no errors (warnings allowed), 1 = errors found,
2 = usage or file error.

Required H2 sections, in this order: Bottom line, How it works, Decisions you own,
Left undone on purpose, Questions you would ask next, Dig deeper. Optional, in any order
after "Left undone on purpose" and before "Dig deeper": What changed, Status board,
Say it to your lead, Words used here. Optional `## Your answers` (only after "Dig deeper").
Optional sections do not break the required order. Any other H2 is a WARN.

Errors: missing/out-of-order required section; misplaced optional section; secret-like
pattern; Bottom line over 70 words or over 3 sentences; How it works without a mermaid
block; a decision card lacking a line that STARTS with **Recommendation:**, **If you do
nothing:**, **Do it if:** or **Skip it if:** (the message names the card); no cards and no
"No decisions"; Left undone on purpose with neither a table whose header has Item, Status
now and Agent's reason (case-insensitive) nor the text "Nothing was left undone".
Warnings: Bottom line with a commit-hash-like token or a `backticked` term that is neither
in "Words used here" nor glossed inline later in the file (term followed within 80 chars by
"(", " — " or ": "); mermaid block over 12 nodes; How it works prose over 140 words; more
than 4 decision cards; Left undone table with more than 4 columns, or with a Status now
cell containing "open" while the section lacks "Do it if" or "Skip it if"; any table with
more than 5 columns; What changed (only if present) without a table or without introduced /
pre-existing / extra / required; fewer than 3 or more than 8 bold question lines; file over
900 words + 140 per decision card (max 1600, mermaid blocks not counted; the message states
the limit); more than 110 non-empty lines; table cell over 30 words; more than 12 glossary
entries. A debrief whose opening looks like a review (the words review, Rovo, or pull request)
also warns when the bottom line has no Yes or No, when the file never says introduced /
pre-existing / already there / already on, or when it cites no source file.
Coverage statistics lines; status board (if present) with none of "verified",
"reported", "checked" / "not checked", or with no status mark (✅ ⚠️ ❌ ❓).
Matched secret values are never printed, only the line number and rule name.
Pattern matching is a safety net, not a guarantee. Stdlib only.
"""
import re
import sys

REQUIRED = [
    "Bottom line",
    "How it works",
    "Decisions you own",
    "Left undone on purpose",
    "Questions you would ask next",
    "Dig deeper",
]
# after "Left undone on purpose", before "Dig deeper", in any order
OPTIONAL_MIDDLE = ["What changed", "Status board", "Say it to your lead", "Words used here"]
OPTIONAL_LAST = "Your answers"  # allowed only after "Dig deeper"
MAX_BOTTOM_WORDS = 70
MAX_BOTTOM_SENTENCES = 3
BASE_FILE_WORDS = 900
WORDS_PER_CARD = 140
MAX_FILE_WORDS = 1600
MAX_LINES = 110
MAX_COLUMNS = 5
MAX_UNDONE_COLUMNS = 4
MAX_CELL_WORDS = 30
MAX_GLOSSARY = 12
MAX_NODES = 12
MAX_FLOW_WORDS = 140
MAX_CARDS = 4
MIN_QUESTIONS, MAX_QUESTIONS = 3, 8
GLOSS_WINDOW = 80
UNDONE_COLUMNS = ("item", "status now", "agent's reason")
CARD_LABELS = ("Recommendation", "If you do nothing", "Do it if", "Skip it if")


def _path_like_b64(text):
    return text.count("/") * 12 > len(text)


SECRET_RULES = [
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("figma token", re.compile(r"figd_[A-Za-z0-9_\-]{8,}")),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("password assignment", re.compile(r"(?i)\bpassword\s*[=:]\s*[\"']?(?![$<{\[(])[^\s\"'`]{4,}")),
    (
        "secret assignment",
        re.compile(
            r"(?i)\b(passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)"
            r"\b[\"']?\s*[:=]\s*[\"']?(?![$<{\[(])([^\s\"'`]{8,})"
        ),
    ),
    ("data URL", re.compile(r"data:[A-Za-z0-9.+/\-]{0,64}(?:;[A-Za-z0-9=.+\-]+)*,[^\s)\"']{20,}")),
    ("AWS access key id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Atlassian token", re.compile(r"\bATATT[A-Za-z0-9_=-]{20,}")),
    ("credentials in URL", re.compile(r"://[^/\s:@]+:[^/\s@]{3,}@")),
]
STATUS_WORDS = re.compile(r"verified|reported|\bchecked\b")
STATUS_MARKS = ("✅", "⚠", "❌", "❓")
BACKTICKED = re.compile(r"`([^`\n]+)`")
B64 = re.compile(r"[A-Za-z0-9+/]{60,}={0,2}")
COVERAGE = re.compile(
    r"(?i)\b(?:transcripts?|sessions?|files?)\s+(?:scanned|matched)\b"
    r"|\b(?:scanned|matched)\s+\d+\s+(?:transcripts?|sessions?|files?)\b"
)
NODE = re.compile(r"(?<![\w\"'])([A-Za-z_][\w-]*)\s*(?:\[\[|\[\(|\(\(|\[|\(|\{)")
NODE_SKIP = {"subgraph", "style", "classDef", "class", "click", "linkStyle", "direction"}
HASH_LIKE = re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{7,40}(?![0-9A-Za-z])")
SENTENCE_END = re.compile(r"[.?!](?=\s|$)")
CHANGE_WORDS = re.compile(r"(?i)\b(introduced|pre-existing|extra|required)\b")
SCOPE_WORDS = re.compile(r"(?i)\b(introduced|pre-existing|already there|already on)\b")
REVIEW_HINT = re.compile(r"(?i)\b(review|rovo|pull request)\b")
YES_NO = re.compile(r"(?i)\b(yes|no)\b")
SOURCE_FILE = re.compile(r"\b[\w./-]+\.(?:js|jsx|ts|tsx|py|php|vue)\b")
QUESTION_LINE = re.compile(r"^\s*(?:>\s*)?(?:[-*+]\s+|\d+\.\s+)?\*\*[^*\n]*\?\s*\*\*")
MERMAID_OPEN = re.compile(r"^\s*```mermaid\b")
SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def words(text):
    return len(text.split())


def split_row(stripped):
    return [c.strip() for c in stripped.replace("\\|", "\x00").strip("|").split("|")]


def table_headers(blines):
    """Header cells (lowercased, markup and curly quotes removed) of each markdown table in blines."""
    out = []
    for k in range(len(blines) - 1):
        cur, nxt = blines[k].strip(), blines[k + 1].strip()
        if cur.startswith("|") and SEPARATOR.match(nxt) and "|" in nxt:
            cells = [re.sub(r"[*_`]", "", c).replace("\u2019", "'").strip().lower() for c in split_row(cur)]
            out.append(cells)
    return out


def sentence_count(text):
    plain = text.replace("*", "").replace("_", " ")
    plain = re.sub(r"`[^`]*`", " ", plain)
    return len(SENTENCE_END.findall(plain.strip()))


def split_mermaid(blines):
    """Return (prose_lines, blocks); blocks are (offset_of_opening_line, [content lines])."""
    prose, blocks, cur = [], [], None
    for k, l in enumerate(blines):
        if cur is None:
            if MERMAID_OPEN.match(l):
                cur = (k, [])
            else:
                prose.append(l)
        elif l.strip().startswith("```"):
            blocks.append(cur)
            cur = None
        else:
            cur[1].append(l)
    if cur is not None:
        blocks.append(cur)
    return prose, blocks


def check(text):
    """Return a list of (line, level, message), level is 'ERROR' or 'WARN'."""
    lines = text.splitlines()
    found = []

    def add(line, level, msg):
        found.append((line, level, msg))

    # --- locate H2 headings outside code fences
    fenced = [False] * len(lines)
    in_fence = False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            fenced[i] = True
        else:
            fenced[i] = in_fence
    h2 = [(i, m.group(1)) for i, line in enumerate(lines)
          if not fenced[i] and (m := re.match(r"^##\s+(.+?)\s*$", line)) and not line.startswith("###")]

    first = {}
    for i, title in h2:
        first.setdefault(title, i)
    bodies = {}
    for idx, (i, title) in enumerate(h2):
        end = h2[idx + 1][0] if idx + 1 < len(h2) else len(lines)
        if title not in bodies:
            bodies[title] = (i, end)

    # required sections: present and in order (optional sections are ignored here)
    last = -1
    for name in REQUIRED:
        pos = first.get(name)
        if pos is None:
            add(1, "ERROR", f"missing required section '## {name}'")
            continue
        if pos < last:
            add(pos + 1, "ERROR", f"section out of order: '## {name}'")
        last = max(last, pos)

    # optional sections: placement
    lo, hi = first.get("Left undone on purpose"), first.get("Dig deeper")
    for name in OPTIONAL_MIDDLE:
        pos = first.get(name)
        if pos is None:
            continue
        if lo is not None and pos < lo:
            add(pos + 1, "ERROR", f"section out of order: '## {name}' must come after '## Left undone on purpose'")
        elif hi is not None and pos > hi:
            add(pos + 1, "ERROR", f"section out of order: '## {name}' must come before '## Dig deeper'")
    if OPTIONAL_LAST in first and hi is not None and first[OPTIONAL_LAST] < hi:
        add(first[OPTIONAL_LAST] + 1, "ERROR", f"section out of order: '## {OPTIONAL_LAST}' must come after '## Dig deeper'")
    known = set(REQUIRED) | set(OPTIONAL_MIDDLE) | {OPTIONAL_LAST}
    for i, title in h2:
        if title not in known:
            add(i + 1, "WARN", f"unexpected section '## {title}' (not part of the debrief structure)")

    def body(name):
        if name not in bodies:
            return None
        start, end = bodies[name]
        return start, lines[start + 1:end]

    # --- secrets (whole file)
    for i, line in enumerate(lines, 1):
        for rule, rx in SECRET_RULES:
            if rx.search(line):
                add(i, "ERROR", f"secret pattern: {rule} (value not shown)")
        for m in B64.finditer(line):
            if not _path_like_b64(m.group(0)):
                add(i, "ERROR", "secret pattern: long base64 (value not shown)")
                break

    # --- Bottom line
    bl = body("Bottom line")
    if bl:
        start, blines = bl
        content = [(start + 2 + k, l) for k, l in enumerate(blines) if l.strip() and not l.strip().startswith("<!--")]
        if not content:
            add(start + 1, "ERROR", "Bottom line is empty")
        else:
            joined = " ".join(l for _, l in content)
            n = words(joined)
            if n > MAX_BOTTOM_WORDS:
                add(content[0][0], "ERROR", f"Bottom line has {n} words (max {MAX_BOTTOM_WORDS})")
            sentences = sentence_count(joined)
            if sentences > MAX_BOTTOM_SENTENCES:
                add(content[0][0], "ERROR", f"Bottom line has {sentences} sentences (max {MAX_BOTTOM_SENTENCES})")
            for ln, l in content:
                if any(re.search(r"[0-9]", t) and re.search(r"[a-fA-F]", t) for t in HASH_LIKE.findall(l)):
                    add(ln, "WARN", "Bottom line contains a commit-hash-like token (leave hashes for 'Dig deeper')")

    # --- How it works
    hw = body("How it works")
    if hw:
        start, blines = hw
        prose, blocks = split_mermaid(blines)
        if not blocks:
            add(start + 1, "ERROR", "How it works has no ```mermaid block")
        for off, content in blocks:
            nodes = set()
            for l in content:
                nodes.update(n for n in NODE.findall(l) if n not in NODE_SKIP)
            if len(nodes) > MAX_NODES:
                add(start + 2 + off, "WARN", f"mermaid block has about {len(nodes)} nodes (max {MAX_NODES})")
        n = words(" ".join(prose))
        if n > MAX_FLOW_WORDS:
            add(start + 1, "WARN", f"How it works has {n} words of prose outside the diagram (max {MAX_FLOW_WORDS})")

    # --- Decisions you own
    n_cards = 0
    got = body("Decisions you own")
    if got:
        start, blines = got
        cards = [k for k, l in enumerate(blines) if not fenced[start + 1 + k] and l.startswith("### ")]
        if not cards:
            if not re.search(r"(?i)no decisions", "\n".join(blines)):
                add(start + 1, "ERROR", "Decisions section has no '### ' cards and no 'No decisions' text")
        n_cards = len(cards)
        if n_cards > MAX_CARDS:
            add(start + 1, "WARN", f"Decisions section has {n_cards} cards (max {MAX_CARDS})")
        for j, k in enumerate(cards):
            end = cards[j + 1] if j + 1 < len(cards) else len(blines)
            card = blines[k:end]
            title = blines[k][4:].strip()[:60] or "(untitled)"
            for label in CARD_LABELS:
                rx = re.compile(rf"^\s*(?:[-*]\s+)?\*\*{re.escape(label)}:\*\*")
                if not any(rx.match(l) for l in card):
                    inline = any(f"**{label}:**" in l for l in card)
                    where = "found inside a line, not at its start" if inline else "not found"
                    add(start + 2 + k, "ERROR",
                        f"decision card '{title}': **{label}:** must start a line ({where})")

    # --- Left undone on purpose
    got = body("Left undone on purpose")
    if got:
        start, blines = got
        tables = [hdr for hdr in table_headers(blines) if all(col in hdr for col in UNDONE_COLUMNS)]
        section = "\n".join(blines)
        if not tables and not re.search(r"(?i)nothing was left undone", section):
            add(start + 1, "ERROR", "Left undone on purpose needs a table with columns Item, Status now, "
                                    "Agent's reason, or the text 'Nothing was left undone'")
        for hdr in tables:
            if len(hdr) > MAX_UNDONE_COLUMNS:
                add(start + 1, "WARN", f"Left undone table has {len(hdr)} columns (max {MAX_UNDONE_COLUMNS})")
        if tables:
            idx = tables[0].index("status now")
            has_open = False
            for k, l in enumerate(blines):
                st = l.strip()
                if st.startswith("|") and not SEPARATOR.match(st) and not fenced[start + 1 + k]:
                    cells = split_row(st)
                    if idx < len(cells) and "open" in cells[idx].lower():
                        has_open = True
            low = section.lower()
            if has_open and not ("do it if" in low and "skip it if" in low):
                add(start + 1, "WARN", "Left undone has an open item but no 'Do it if' and 'Skip it if' lines")

    # --- What changed
    got = body("What changed")
    if got:
        start, blines = got
        if not table_headers(blines):
            add(start + 1, "WARN", "What changed has no table")
        if not CHANGE_WORDS.search("\n".join(blines)):
            add(start + 1, "WARN", "What changed uses none of 'introduced', 'pre-existing', 'extra', 'required'")

    # --- Questions you would ask next
    got = body("Questions you would ask next")
    if got:
        start, blines = got
        n = sum(1 for k, l in enumerate(blines) if not fenced[start + 1 + k] and QUESTION_LINE.match(l))
        if n < MIN_QUESTIONS or n > MAX_QUESTIONS:
            add(start + 1, "WARN", f"Questions section has {n} bold question lines (expected {MIN_QUESTIONS} to {MAX_QUESTIONS})")

    # --- review debriefs must answer and scope each claim
    head = "\n".join(lines[:25])
    if REVIEW_HINT.search(head):
        bl = body("Bottom line")
        bl_text = "\n".join(bl[1]) if bl else ""
        if not YES_NO.search(bl_text):
            add(1, "WARN", "review bottom line has no Yes or No per claim")
        if not SCOPE_WORDS.search("\n".join(lines)):
            add(1, "WARN", "review debrief never says introduced, pre-existing, already there, or already on")
        if not SOURCE_FILE.search("\n".join(lines)):
            add(1, "WARN", "review debrief cites no source file as the existing pattern")

    # --- word budget (mermaid blocks not counted)
    prose_all, _blocks = split_mermaid(lines)
    total_words = words("\n".join(prose_all))
    limit = min(BASE_FILE_WORDS + WORDS_PER_CARD * n_cards, MAX_FILE_WORDS)
    if total_words > limit:
        add(1, "WARN", f"file has {total_words} words (target max {limit} = {BASE_FILE_WORDS} + "
                       f"{WORDS_PER_CARD} x {n_cards} decision cards, cap {MAX_FILE_WORDS})")
    non_empty = sum(1 for l in lines if l.strip())
    if non_empty > MAX_LINES:
        add(1, "WARN", f"file has {non_empty} non-empty lines (max {MAX_LINES})")

    for i, line in enumerate(lines, 1):
        if fenced[i - 1]:
            continue
        stripped = line.strip()
        if stripped.startswith("|") and SEPARATOR.match(stripped) and i >= 2 and lines[i - 2].strip().startswith("|"):
            cols = len(split_row(lines[i - 2].strip()))
            if cols > MAX_COLUMNS:
                add(i - 1, "WARN", f"table has {cols} columns (max {MAX_COLUMNS})")
        if stripped.startswith("|") and not SEPARATOR.match(stripped):
            for cell in split_row(stripped):
                if words(cell) > MAX_CELL_WORDS:
                    add(i, "WARN", f"table cell has {words(cell)} words (max {MAX_CELL_WORDS})")
        if COVERAGE.search(line):
            add(i, "WARN", "coverage statistics (scanned/matched counts) do not belong in a debrief")

    got = body("Words used here")
    if got:
        start, blines = got
        entries = 0
        for k, l in enumerate(blines):
            s = l.strip()
            if re.match(r"^([-*+]|\d+\.)\s+", s) or s.startswith("### "):
                entries += 1
            elif s.startswith("|") and not SEPARATOR.match(s):
                is_header = k + 1 < len(blines) and SEPARATOR.match(blines[k + 1].strip() or "x") is not None
                if not is_header:
                    entries += 1
        if entries > MAX_GLOSSARY:
            add(start + 1, "WARN", f"Words used here has {entries} entries (max {MAX_GLOSSARY})")

    got = body("Status board")
    if got:
        start, blines = got
        board = "\n".join(blines)
        if not STATUS_WORDS.search(board.lower()):
            add(start + 1, "WARN", "Status board uses none of 'verified', 'reported', 'checked' / 'not checked'")
        if not any(mark in board for mark in STATUS_MARKS):
            add(start + 1, "WARN", "Status board has no status marks (✅ ⚠️ ❌ ❓)")

    # --- backticked terms in the Bottom line should be explained: glossary entry or inline gloss later on
    if bl:
        gl = body("Words used here")
        glossary = "\n".join(gl[1]).lower() if gl else ""
        later = "\n".join(lines[bodies["Bottom line"][1]:])
        reported = set()
        for k, l in enumerate(bl[1]):
            for term in BACKTICKED.findall(l):
                term = term.strip()
                if (not term or "/" in term or "." in term or len(term) > 40 or term.lower() in reported
                        or term.lower() in glossary or any(rx.search(term) for _n, rx in SECRET_RULES)
                        or B64.search(term)):
                    continue
                gloss = re.compile(re.escape(term) + r"[^\n]{0," + str(GLOSS_WINDOW) + r"}?(?:\(| — |: )", re.I)
                if gloss.search(later):
                    continue
                reported.add(term.lower())
                add(bl[0] + 2 + k, "WARN", f"Bottom line term `{term}` is not explained in '## Words used here' or inline")

    return sorted(found, key=lambda x: (x[0], x[1] != "ERROR"))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    try:
        with open(argv[0], encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"cannot read file: {exc}", file=sys.stderr)
        return 2
    results = check(text)
    for line, level, msg in results:
        print(f"{level} {line}: {msg}")
    errors = sum(1 for _, level, _ in results if level == "ERROR")
    if errors:
        print(f"FAIL ({errors} errors)")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
