#!/usr/bin/env python3
"""Print a compact, redacted digest of ONE agent session (Cursor or Kiro CLI).

Usage:
  session_digest.py <id>                     full uuid or unique prefix (>= 6 chars)
  session_digest.py --latest [--cwd PATH] [--source cursor|kiro]
  session_digest.py --path FILE              digest an explicit .jsonl file
  session_digest.py <id> --turn N [--turn M] 3-line header plus only the given turn(s), in full
  session_digest.py <id> --turn N --final-only  just the user text and final assistant text of turn N
  session_digest.py <id> --subagent N|all    3-line header plus the full final text of subagent child N
                                             (index as listed in Meta) or of every child (each <= 3000 chars)
  session_digest.py <id> --full              no per-item truncation (warns on stderr > 150k chars)
Options: --max-chars N (default 40000), --json (machine output instead of markdown),
--no-related (skip the scan for later sessions that mention this one).
Every "### Turn k" header shows the jsonl line range of that turn, and the final message
section shows its line number, so the raw file never has to be searched.

After Meta, "## Later sessions that mention this one" lists up to 10 Cursor parent
transcripts (all project slugs) and Kiro CLI sessions whose file contains this session's
full uuid (plain byte search per line, no JSON parsing of non-matching lines; the session
itself and its own Kiro subagents are skipped). Each entry has uuid, source, project or cwd,
date (first <timestamp> / Kiro prompt time, else file mtime) and the first user text
(<= 160 chars, redacted), sorted by date, earliest first.
Each subagent child in Meta also shows its final assistant text (500 chars, head+tail) and
its jsonl path. --turn and --subagent are drill-down modes: they print a 3-line header
(session id, source, turn count) instead of Meta and skip the related-session scan.

Search roots (override for tests with environment variables):
  CURSOR_PROJECTS_DIR  default ~/.cursor/projects
                       <root>/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl (parent)
                       <root>/<slug>/agent-transcripts/<uuid>/subagents/*.jsonl
  KIRO_SESSIONS_DIR    default ~/.kiro/sessions/cli   (directory holding <uuid>.jsonl/.json)

Exit codes: 0 ok, 2 not found / bad arguments / roots missing, 3 ambiguous prefix
(matches are printed as JSON with path, source, mtime).

Read-only and stdlib only. Session files are read line by line; a line over 5 MB is
skipped and counted. SQLite databases (state.vscdb etc.) and store.json are never
opened. Every emitted string is redacted (tokens, JWTs, passwords, long base64, data
URLs, cloud keys, private keys).

Auto-injected "user" messages (not real user turns): a user message whose text starts
with a notification-like tag (<system_notification>, <task_notification>, ...) or with
the stock "Perform any necessary follow-up actions in response to the subagent
completion" / "Briefly inform the user about the task result" prompts. Each becomes a
one-line "Turn k: auto notification" entry (stock boilerplate removed, then 120 chars; the
first 300 chars of the assistant reply follow as "result") and is not counted as a user turn. User lines that are empty after stripping
context tags are skipped. Kiro "[LIVE STEERING ...]" text is a real user message sent
mid-turn and is shown inside the current turn. Kiro Compaction and Clear rows are shown
at their real position between turns.
Open-signal lines skip sentences where the agent narrates its own reasoning ("I'll", "Let
me", "I need to", "I should", "I'm weighing") unless they also say "not fixed", "deferred",
"out of scope", "follow-up", "still open" or "left". For Kiro, tool output that matched a
redaction rule is reported in Meta as "Secret-like values seen in tool output: turn k
(rule name)"; the value is never printed.
Kiro subagent status comes only from the session's own .json (session_created_reason
== "subagent", or a parent_session_id when no reason is recorded). A "rewind" session
that has a parent_session_id is NOT a subagent.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_LINE = 5_000_000  # a single jsonl line above this is skipped and counted
STORE_CAP = 100_000  # per stored string, after redaction

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ID_ARG = re.compile(r"^[0-9a-fA-F][0-9a-fA-F-]{5,35}$")
USER_QUERY = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)
TIMESTAMP = re.compile(r"<timestamp>\s*(.*?)\s*</timestamp>", re.DOTALL)
CTX_TAGS = re.compile(
    r"<(available_subagent_types|available_subagent_models|dynamic_tool_catalog|"
    r"dynamic_tool_namespaces|side_chat_boundary|open_and_recently_viewed_files|"
    r"user_info|git_status|agent_skills|system_reminder|hooks_context)\b[^>]*>.*?</\1>",
    re.DOTALL,
)
IMAGE_FILES = re.compile(r"<image_files>.*?</image_files>", re.DOTALL)
ATTACHED = re.compile(r"<attached_file\b[^>]*?path=\"([^\"]*)\"[^>]*>.*?</attached_file>", re.DOTALL)
AUTO_NOTICE = re.compile(
    r"^\s*<(?:system|task|subagent|agent|background)[-_]?"
    r"(?:notification|completion|complete|result|status)\w*",
    re.IGNORECASE,
)
AUTO_PROMPT = re.compile(
    r"^\s*(?:Perform any necessary follow-up actions in response to the subagent completion"
    r"|Briefly inform the user about the task result)",
    re.IGNORECASE,
)
CD_RE = re.compile(r"(?:^|[;&|(]\s*)cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|()<>]+)")
GIT_C_RE = re.compile(r"\bgit\s+-C\s+(\"[^\"]+\"|'[^']+'|[^\s;&|()<>]+)")
STEER_MSG = re.compile(r"<user_message\b[^>]*>(.*?)</user_message>", re.DOTALL)
PATCH_FILE = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+?)\s*$", re.MULTILINE)

SIGNAL_RE = re.compile(  # open-signal markers, also used to protect a turn's final text from omission
    r"\b(not implemented|deferred|out of scope|follow[- ]?up|todo|still open|could not|"
    r"couldn't|unable|failed|not verified|didn't verify|did not verify|assumption|assume[sd]?|"
    r"pending|needs your|your call|decide|approve|risk|workaround|skipped|pre-existing|"
    r"unrelated|not fixed|not changed|\bleft\b|\blater\b|\bseparate|\bneeds an?\b|open question|unknown)",
    re.IGNORECASE,
)
NARRATION = re.compile(  # the agent narrating its own reasoning, not reporting an open item
    r"\b(?:I['\u2019]m weighing|I['\u2019]ll|Let me|I need to|I should)\b", re.IGNORECASE)
NARRATION_KEEP = re.compile(  # ...unless the sentence also says something is open
    r"not fixed|deferred|out of scope|follow[- ]?up|still open|\bleft\b", re.IGNORECASE)
BOILERPLATE = [  # stock text of auto-injected "subagent finished" prompts
    re.compile(r"If you mention an agent or subagent in your response.*?(?:Don['\u2019]t repeat the same confirmation every time\.?|\Z)",
               re.IGNORECASE | re.DOTALL),
    re.compile(r"Perform any necessary follow-up actions in response to the subagent completion[^.]*\.?", re.IGNORECASE),
    re.compile(r"If no follow-up work is needed[^.]*\.?", re.IGNORECASE),
    re.compile(r"Briefly inform the user about the task result[^.]*\.?", re.IGNORECASE),
    re.compile(r"Don['\u2019]t repeat the same confirmation every time\.?", re.IGNORECASE),
]
FENCE = re.compile(r"```.*?```", re.DOTALL)
ASK_TOOLS = {"askquestion", "ask_question", "askuserquestion", "userinput", "user_input"}


# --------------------------------------------------------------------------- redaction
def _b64(match):
    text = match.group(0)
    if text.count("/") * 12 > len(text):  # path-like, not base64
        return text
    return "[REDACTED_BASE64]"


REDACTIONS = [  # (rule name, pattern, replacement); names are reported, values never are
    ("private key block",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.DOTALL),
     "[REDACTED_PRIVATE_KEY]"),
    ("figma token", re.compile(r"figd_[A-Za-z0-9_\-]+"), "[REDACTED_FIGMA_TOKEN]"),
    ("authorization header", re.compile(r"Bearer\s+\S+", re.IGNORECASE), "Bearer [REDACTED]"),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"), "[REDACTED_JWT]"),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_\-]{16,}"), "[REDACTED_JWT]"),
    ("password assignment", re.compile(r"(?i)(password\s*[=:]\s*)\S+"), r"\1[REDACTED]"),
    ("secret assignment", re.compile(
        r"(?i)\b((?:passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)"
        r"\b[\"']?\s*[:=]\s*[\"']?)(?![$<{\[(])[^\s\"'`]{8,}"), r"\1[REDACTED]"),
    ("data URL", re.compile(r"data:[A-Za-z0-9.+/\-]{0,64}(?:;[A-Za-z0-9=.+\-]+)*,[^\s)\"']{20,}"), "[REDACTED_DATA_URL]"),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    ("GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "[REDACTED_GITHUB_TOKEN]"),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), "[REDACTED_SLACK_TOKEN]"),
    ("Atlassian token", re.compile(r"\bATATT[A-Za-z0-9_=\-]{20,}"), "[REDACTED_ATLASSIAN_TOKEN]"),
    ("credentials in URL", re.compile(r"(://[^/\s:@]+:)[^/\s@]{3,}@"), r"\1[REDACTED]@"),
    ("long base64", re.compile(r"[A-Za-z0-9+/]{60,}={0,2}"), _b64),
]


def redact(text):
    """Redact secrets. Unlike scan_transcripts.py there is no store.json clause: this
    script never opens store.json files, and dropping any text that merely mentions
    the name would hide real content."""
    if not isinstance(text, str):
        return text
    for _name, pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def secret_rules(text):
    """Names of the redaction rules that would change this text (never the values), in rule order."""
    if not isinstance(text, str) or len(text) < 8:
        return []
    hits = []
    for name, pattern, repl in REDACTIONS:
        if name in hits:
            continue
        for match in pattern.finditer(text):
            new = repl(match) if callable(repl) else match.expand(repl)
            if new != match.group(0):
                hits.append(name)
                break
    return hits


def redact_obj(obj):
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    return obj


# --------------------------------------------------------------------------- helpers
def collapse(text):
    return " ".join(str(text).split())


def trunc(text, limit):
    """Keep the head and the tail when text is longer than limit (None = never truncate)."""
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if limit is None or len(text) <= limit:
        return text
    if limit < 40:
        return text[: max(limit, 0)].rstrip() + ("…" if limit > 0 else "")
    head = int(limit * 0.65)
    tail = limit - head - 7
    return text[:head].rstrip() + " […] " + text[-tail:].lstrip()


def store(text):
    """Redact, then cap what is kept in memory."""
    return trunc(redact(text), STORE_CAP)


def iso_mtime(path):
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cursor_slug(cwd):
    return re.sub(r"[^A-Za-z0-9]+", "-", cwd).strip("-")


def iter_lines(path, stats):
    """Yield (lineno, parsed json) line by line. Oversized or invalid lines are counted."""
    with open(path, "rb") as handle:
        lineno = 0
        while True:
            raw = handle.readline(MAX_LINE + 1)
            if not raw:
                break
            lineno += 1
            if len(raw) > MAX_LINE:
                if not raw.endswith(b"\n"):
                    while True:  # drain the rest of the oversized line in chunks
                        chunk = handle.readline(1 << 20)
                        if not chunk or chunk.endswith(b"\n"):
                            break
                stats["skipped_big"] += 1
                continue
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield lineno, json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                stats["bad_json"] += 1


def load_json_file(path):
    try:
        if path.stat().st_size > 50_000_000:
            return {}
        with open(path, encoding="utf-8", errors="replace") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


# --------------------------------------------------------------------------- session model
def new_session(source, path):
    return {
        "source": source, "path": path, "uuid": path.stem, "turns": [], "files": {},
        "signals": [], "tasks": [], "pending": {}, "pre_steer": [], "last_text": "",
        "last_text_line": None, "auto_skipped": 0, "compactions": 0, "markers": [], "dirs": Counter(),
        "steer_seen": set(), "tool_secrets": [], "tool_secret_keys": set(),
        "stats": {"skipped_big": 0, "bad_json": 0},
    }


def new_turn(sess, ts, user, lineno, auto=False):
    turn = {
        "n": len(sess["turns"]) + 1, "ts": ts, "user": user, "tools": Counter(), "files": {},
        "cmds": [], "subagents": [], "questions": [],
        "steer": list(sess["pre_steer"]), "final": "", "final_line": None, "lead": "",
        "tool_errors": 0, "auto": auto, "l0": lineno, "l1": lineno,
    }
    sess["pre_steer"] = []
    sess["turns"].append(turn)
    return turn


def steer(sess, turn, text, sid=None):
    """A user message sent while the agent was working: real user input, shown in the turn."""
    if sid:
        if sid in sess["steer_seen"]:
            return
        sess["steer_seen"].add(sid)
    text = store(text)
    if not text:
        return
    (sess["pre_steer"] if turn is None else turn["steer"]).append(text)


def add_marker(sess, kind, text, lineno):
    sess["markers"].append({"after": len(sess["turns"]), "kind": kind, "text": text, "line": lineno})


def record_edit(sess, turn, path, action):
    path = redact(str(path).strip())[:300]
    if not path:
        return
    turn["files"].setdefault(path, action)
    entry = sess["files"].setdefault(path, {"edits": 0, "first": turn["n"], "last": turn["n"]})
    entry["edits"] += 1
    entry["last"] = turn["n"]


def sentences(text):
    text = FENCE.sub(" ", text)
    for part in re.split(r"(?<=[.!?])\s+|\n+", text):
        part = re.sub(r"^[\s>#|*\-\d.)]+", "", part).replace("**", "").strip()
        if len(part) >= 12:
            yield part


def add_text(sess, turn, text, lineno=None):
    """Record an assistant text block: keep the last one per turn, harvest open signals.
    Every text block is scanned, including the session's final message."""
    cleaned = text.replace("[REDACTED]", "").strip()  # Cursor's stand-in for hidden thinking
    if not cleaned:
        return
    turn["final"] = store(cleaned)
    turn["final_line"] = lineno
    sess["last_text"] = turn["final"]
    sess["last_text_line"] = lineno
    if len(turn["lead"]) < 300:
        turn["lead"] = (turn["lead"] + " " + collapse(redact(cleaned))).strip()[:300]
    seen = {s["text"].lower() for s in sess["signals"]}
    for sent in sentences(cleaned):
        if SIGNAL_RE.search(sent) and not (NARRATION.search(sent) and not NARRATION_KEEP.search(sent)):
            sent = trunc(redact(sent), 220)
            if sent.lower() not in seen:
                seen.add(sent.lower())
                sess["signals"].append({"turn": turn["n"], "text": sent})
    if len(sess["signals"]) > 400:
        del sess["signals"][: len(sess["signals"]) - 400]


def strip_boilerplate(text):
    for rx in BOILERPLATE:
        text = rx.sub(" ", text)
    return collapse(text)


def clean_cmd(command):
    text = redact(collapse(command)).replace("`", "'")
    return text if len(text) <= 160 else text[:159].rstrip() + "…"


def full_cmd(command):
    return trunc(redact(collapse(command)).replace("`", "'"), 1500)


def add_dir(sess, raw):
    """Count an absolute directory seen in a shell call (working dir, cd, git -C)."""
    if not isinstance(raw, str):
        return
    raw = raw.strip().strip("\"'")
    if raw.startswith("~"):
        raw = os.path.expanduser(raw)
    if not raw.startswith("/") or re.search(r"[$*`(){}<>]", raw):
        return
    path = os.path.normpath(raw)
    if len(path) <= 300:
        sess["dirs"][redact(path)] += 1


def handle_tool(sess, turn, name, inp, tid=None):
    """Update the turn and the session from one tool call (Cursor or Kiro, normalised)."""
    turn["tools"][name] += 1
    low = name.lower()
    if isinstance(inp, str):
        inp = {"input": inp}
    elif not isinstance(inp, dict):
        inp = {}
    if low == "write":  # Cursor Write, Kiro write (command create/strReplace/insert)
        if isinstance(inp.get("path"), str):
            record_edit(sess, turn, inp["path"], inp.get("command") or "write")
    elif low == "strreplace":
        if isinstance(inp.get("path"), str):
            record_edit(sess, turn, inp["path"], "edit")
    elif low == "delete":
        if isinstance(inp.get("path"), str):
            record_edit(sess, turn, inp["path"], "delete")
    elif low == "applypatch":
        patch = inp.get("input") if isinstance(inp.get("input"), str) else ""
        for verb, path in PATCH_FILE.findall(patch):
            record_edit(sess, turn, path, verb.lower())
    elif low in ("shell", "bash"):
        if isinstance(inp.get("command"), str):
            command = inp["command"]
            rec = {"cmd": clean_cmd(command), "full": full_cmd(command), "exit": None, "err": ""}
            turn["cmds"].append(rec)
            if tid:
                sess["pending"][tid] = rec
            for rx in (CD_RE, GIT_C_RE):
                for target in rx.findall(command):
                    add_dir(sess, target)
        for key in ("working_directory", "working_dir"):
            add_dir(sess, inp.get(key))
    elif low == "task":  # Cursor subagent launch
        desc = collapse(inp.get("description") or "")
        prompt = collapse(inp.get("prompt") or "")
        label = redact(desc or prompt[:100] or "(no description)")
        turn["subagents"].append(trunc(label, 160))
        sess["tasks"].append({"desc": trunc(label, 160), "prefix": prompt[:60], "used": False})
    elif low == "subagent":  # Kiro subagent launch
        label = collapse(inp.get("task") or "")
        stages = inp.get("stages")
        if isinstance(stages, list):
            names = [str(s.get("name")) for s in stages if isinstance(s, dict) and s.get("name")]
            if names:
                label = f"{label[:120]} [stages: {', '.join(names[:6])}]"
        turn["subagents"].append(trunc(redact(label or "(no task)"), 200))
    elif low in ASK_TOOLS:
        items = inp.get("questions")
        found = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    for key in ("prompt", "question", "text", "title"):
                        if isinstance(item.get(key), str):
                            found.append(item[key])
                            break
                elif isinstance(item, str):
                    found.append(item)
        elif isinstance(inp.get("question"), str):
            found.append(inp["question"])
        if not found and isinstance(inp.get("title"), str):
            found.append(inp["title"])
        for q in found[:5]:
            turn["questions"].append(trunc(redact(collapse(q)), 200))


def strip_user(text):
    """Return (timestamp, query, has_query_tag) from raw user text."""
    found = TIMESTAMP.search(text)
    ts = collapse(found.group(1))[:120] if found else None
    queries = USER_QUERY.findall(text)
    body = "\n\n".join(queries) if queries else TIMESTAMP.sub("", text)
    body = CTX_TAGS.sub("", body)
    body = ATTACHED.sub(lambda m: f"[attached file: {m.group(1)}]", body)
    body = IMAGE_FILES.sub("[images attached]", body)
    return ts, body.strip(), bool(queries)


def start_user_turn(sess, cur, ts, query, tagged, lineno):
    """Open a turn for a user message. Auto notifications become collapsed turns.
    Returns the new turn, or the old one when the message is empty."""
    if not query:
        sess["auto_skipped"] += 1  # only context tags / timestamp: nothing to show
        if cur is not None:
            cur["l1"] = lineno
        return cur
    auto = bool(AUTO_PROMPT.match(query)) or (not tagged and bool(AUTO_NOTICE.match(query)))
    return new_turn(sess, ts, store(query), lineno, auto=auto)


# --------------------------------------------------------------------------- parsers
def parse_cursor(path):
    sess = new_session("cursor", path)
    cur = None
    for lineno, obj in iter_lines(path, sess["stats"]):
        if not isinstance(obj, dict):
            continue
        if cur is not None and obj.get("role") != "user":  # a user line opens (or skips into) its own turn
            cur["l1"] = lineno
        content = (obj.get("message") or {}).get("content") if isinstance(obj.get("message"), dict) else None
        if not isinstance(content, list):
            content = []
        role = obj.get("role")
        if role == "user":
            raw = "\n".join(b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str))
            ts, query, tagged = strip_user(raw)
            cur = start_user_turn(sess, cur, ts, query, tagged, lineno)
        elif role == "assistant":
            if cur is None:
                cur = new_turn(sess, None, "", lineno)
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    add_text(sess, cur, block["text"], lineno)
                elif block.get("type") == "tool_use":
                    name = str(block.get("name") or "?")
                    inp = block.get("input")
                    if name == "CallDynamicTool" and isinstance(inp, dict):
                        name = str(inp.get("toolName") or name)
                        inp = inp.get("arguments")
                        if isinstance(inp, str):
                            try:
                                inp = json.loads(inp)
                            except ValueError:
                                inp = {"input": inp}
                    handle_tool(sess, cur, name, inp, None)
    return sess


def kiro_text(content):
    out = []
    for block in content or []:
        if isinstance(block, dict) and block.get("kind") == "text" and isinstance(block.get("data"), str):
            out.append(block["data"])
    return "\n".join(out)


def kiro_result(data, tid):
    """(exit status, stderr/error text) for a shell tool call from a ToolResults line."""
    res = (data.get("results") or {}).get(tid) if isinstance(data.get("results"), dict) else None
    if res == "Cancelled":
        return "cancelled", ""
    if isinstance(res, dict):
        result = res.get("result")
        if isinstance(result, dict):
            if "Error" in result:
                return "error", str(result["Error"])
            succ = result.get("Success")
            items = succ.get("items") if isinstance(succ, dict) else None
            for item in items or []:
                js = item.get("Json") if isinstance(item, dict) else None
                if isinstance(js, dict) and "exit_status" in js:
                    return norm_exit(js["exit_status"]), str(js.get("stderr") or "")
    for block in data.get("content") or []:
        if isinstance(block, dict) and block.get("kind") == "toolResult":
            tr = block.get("data") or {}
            if tr.get("toolUseId") == tid:
                first = ""
                for part in tr.get("content") or []:
                    text = part.get("data") if isinstance(part, dict) else None
                    if isinstance(text, str):
                        first = first or text
                        m = re.search(r"exit status:\s*(-?\d+)", text[:2000])
                        if m:
                            return m.group(1), text if m.group(1) != "0" else ""
                if tr.get("status") == "error":
                    return "error", first
    return None, ""


def iter_strings(obj, depth=0):
    """Every string inside nested dict/list data (tool output is text or JSON such as stdout/stderr)."""
    if isinstance(obj, str):
        yield obj
    elif depth < 6 and isinstance(obj, dict):
        for value in obj.values():
            yield from iter_strings(value, depth + 1)
    elif depth < 6 and isinstance(obj, list):
        for value in obj:
            yield from iter_strings(value, depth + 1)


def note_tool_secrets(sess, turn, parts):
    """Record (turn, rule name) for tool output that matches a redaction rule. Never the value.
    Image parts are skipped: their payload is base64 by nature."""
    names = []
    for part in parts or []:
        if not isinstance(part, dict) or part.get("kind") == "image":
            continue
        for text in iter_strings(part.get("data")):
            names += [n for n in secret_rules(text) if n not in names]
    n = turn["n"] if turn is not None else 0
    for name in names:
        if (n, name) not in sess["tool_secret_keys"]:
            sess["tool_secret_keys"].add((n, name))
            sess["tool_secrets"].append({"turn": n, "rule": name})


def norm_exit(value):
    m = re.search(r"-?\d+", str(value))
    return m.group(0) if m else str(value)[:20]


def steer_parts(text):
    """(id, user text) pairs from a Kiro '[LIVE STEERING ...]' block."""
    out = []
    for m in re.finditer(r"<user_message\b([^>]*)>(.*?)</user_message>", text, re.DOTALL):
        sid = re.search(r'id="([^"]+)"', m.group(1))
        out.append((sid.group(1) if sid else None, m.group(2).strip()))
    if not out:  # no <user_message> wrapper: drop the banner, boilerplate and trailing instructions
        body = re.sub(r"^\[LIVE STEERING[^\]]*\]\s*", "", text.strip())
        body = re.sub(r"^The user sent a new message while you are working\.[^\n]*\n*", "", body)
        body = re.split(r"\n\s*IMPORTANT: After completing your work", body)[0]
        out.append((None, body.strip()))
    return out


def parse_kiro(path):
    sess = new_session("kiro", path)
    cur = None
    for lineno, obj in iter_lines(path, sess["stats"]):
        if not isinstance(obj, dict):
            continue
        kind = obj.get("kind")
        data = obj.get("data") if isinstance(obj.get("data"), dict) else {}
        if kind == "Clear":
            add_marker(sess, "clear", "", lineno)
            continue
        if kind == "Compaction":
            sess["compactions"] += 1
            summary = data.get("summary")
            if not isinstance(summary, str):
                summary = json.dumps(summary, ensure_ascii=False) if summary is not None else ""
            add_marker(sess, "compaction", store(summary), lineno)
            continue
        if cur is not None and kind != "Prompt":
            cur["l1"] = lineno
        if kind == "Prompt":
            ts, query, tagged = strip_user(kiro_text(data.get("content")))
            epoch = (data.get("meta") or {}).get("timestamp") if isinstance(data.get("meta"), dict) else None
            if isinstance(epoch, (int, float)):
                ts = datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            cur = start_user_turn(sess, cur, ts, query, tagged, lineno)
        elif kind == "AssistantMessage":
            if cur is None:
                cur = new_turn(sess, None, "", lineno)
            for block in data.get("content") or []:
                if not isinstance(block, dict):
                    continue
                bdata = block.get("data")
                if block.get("kind") == "text" and isinstance(bdata, str):
                    add_text(sess, cur, bdata, lineno)
                elif block.get("kind") == "toolUse" and isinstance(bdata, dict):
                    handle_tool(sess, cur, str(bdata.get("name") or "?"), bdata.get("input"), bdata.get("toolUseId"))
        elif kind == "ToolResults":
            for block in data.get("content") or []:
                if not isinstance(block, dict):
                    continue
                bdata = block.get("data")
                if block.get("kind") == "toolResult" and isinstance(bdata, dict):
                    tid = bdata.get("toolUseId")
                    if bdata.get("status") == "error" and cur is not None:
                        cur["tool_errors"] += 1
                    note_tool_secrets(sess, cur, bdata.get("content"))
                    rec = sess["pending"].pop(tid, None)
                    if rec is not None:
                        rec["exit"], err = kiro_result(data, tid)
                        rec["err"] = collapse(redact(err))[:200] if rec["exit"] not in (None, "0") else ""
                    for part in bdata.get("content") or []:  # steering appended to a tool output
                        ptext = part.get("data") if isinstance(part, dict) else None
                        if isinstance(ptext, str) and "[LIVE STEERING" in ptext:
                            for sid, msg in steer_parts(ptext[ptext.index("[LIVE STEERING"):]):
                                steer(sess, cur, msg, sid)
                elif block.get("kind") == "text" and isinstance(bdata, str) and "[LIVE STEERING" in bdata[:80]:
                    for sid, msg in steer_parts(bdata):
                        steer(sess, cur, msg, sid)
    return sess


# --------------------------------------------------------------------------- source discovery
def cursor_root():
    return Path(os.environ.get("CURSOR_PROJECTS_DIR") or Path.home() / ".cursor" / "projects")


def kiro_dir():
    return Path(os.environ.get("KIRO_SESSIONS_DIR") or Path.home() / ".kiro" / "sessions" / "cli")


def find_by_id(ident, croot, kdir):
    ident = ident.lower()
    found = {}
    if croot.is_dir():
        for proj in sorted(p for p in croot.iterdir() if p.is_dir()):
            base = proj / "agent-transcripts"
            if not base.is_dir():
                continue
            for folder in sorted(p for p in base.iterdir() if p.is_dir()):
                parent = folder / f"{folder.name}.jsonl"
                if folder.name.lower().startswith(ident) and parent.is_file():
                    found[str(parent)] = (parent, "cursor", "parent")
                sub = folder / "subagents"
                if sub.is_dir():
                    for child in sorted(sub.glob("*.jsonl")):
                        if child.stem.lower().startswith(ident):
                            found[str(child)] = (child, "cursor", "subagent")
    if kdir.is_dir():
        for path in sorted(kdir.glob("*.jsonl")):
            if path.stem.lower().startswith(ident):
                found[str(path)] = (path, "kiro", "session")
    return list(found.values())


def cursor_latest(croot, cwd):
    """Newest parent jsonl for the cwd slug; walk up parent directories if needed."""
    cand = os.path.abspath(cwd)
    while True:
        slug = cursor_slug(cand)
        base = croot / slug / "agent-transcripts"
        if slug and base.is_dir():
            files = [f / f"{f.name}.jsonl" for f in base.iterdir() if f.is_dir()]
            files = [f for f in files if f.is_file()]
            if files:
                best = max(files, key=lambda f: f.stat().st_mtime)
                return best, best.stat().st_mtime
        up = os.path.dirname(cand)
        if up == cand:
            return None
        cand = up


def kiro_is_subagent(info):
    """From the session's OWN .json only: reason "subagent", or a parent_session_id when no
    reason is recorded. A "rewind" session also has a parent_session_id but is a main session."""
    reason = info.get("session_created_reason")
    if reason == "subagent":
        return True
    return not reason and bool(info.get("parent_session_id"))


def kiro_latest(kdir, cwd):
    """Newest non-subagent, non-empty CLI session whose cwd equals (preferred) or contains cwd."""
    cwd = os.path.abspath(cwd)
    exact, ancestor = [], []
    for meta_path in kdir.glob("*.json"):
        if not UUID.match(meta_path.stem):
            continue
        jsonl = meta_path.with_suffix(".jsonl")
        try:
            if not jsonl.is_file() or jsonl.stat().st_size == 0:
                continue
            mtime = jsonl.stat().st_mtime
        except OSError:
            continue
        meta = load_json_file(meta_path)
        scwd = meta.get("cwd")
        if not isinstance(scwd, str) or kiro_is_subagent(meta):
            continue
        scwd = os.path.abspath(scwd)
        if scwd == cwd:
            exact.append((mtime, jsonl))
        elif cwd.startswith(scwd.rstrip("/") + "/"):
            ancestor.append((mtime, jsonl))
    pool = exact or ancestor
    if not pool:
        return None
    mtime, jsonl = max(pool)
    return jsonl, mtime


def sniff_source(path):
    if "agent-transcripts" in path.parts:
        return "cursor"
    if ".kiro" in path.parts or path.parent.name == "cli":
        return "kiro"
    try:
        for _n, obj in iter_lines(path, {"skipped_big": 0, "bad_json": 0}):
            if isinstance(obj, dict) and "kind" in obj and "version" in obj:
                return "kiro"
            break
    except OSError:
        pass
    return "cursor"


# --------------------------------------------------------------------------- meta
def first_user_prefix(path):
    stats = {"skipped_big": 0, "bad_json": 0}
    try:
        for i, (_n, obj) in enumerate(iter_lines(path, stats)):
            if i > 4:
                break
            if isinstance(obj, dict) and obj.get("role") == "user":
                content = (obj.get("message") or {}).get("content") or []
                raw = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and isinstance(b.get("text"), str))
                return collapse(strip_user(raw)[1])[:60]
    except OSError:
        pass
    return ""


def cursor_children(folder, tasks):
    sub = folder / "subagents"
    if not sub.is_dir():
        return []
    out, loose = [], []
    for child in sorted(sub.glob("*.jsonl")):
        prefix = first_user_prefix(child)
        rec = {"id": child.stem, "size": child.stat().st_size, "description": None, "match": "none",
               "path": str(child), "source": "cursor"}
        for task in tasks:
            k = min(len(prefix), len(task["prefix"]), 60)
            if not task["used"] and k >= 10 and prefix[:k] == task["prefix"][:k]:
                task["used"] = True
                rec["description"], rec["match"] = task["desc"], "prompt"
                break
        if rec["description"] is None:
            loose.append(rec)
        out.append(rec)
    remaining = [t for t in tasks if not t["used"]]
    for rec, task in zip(loose, remaining):  # fallback: listing order (heuristic)
        rec["description"], rec["match"] = task["desc"], "order-guess"
    return out


def kiro_children(kdir, sid):
    out = []
    for meta_path in sorted(kdir.glob("*.json")):
        if meta_path.stem == sid or not UUID.match(meta_path.stem):
            continue
        meta = load_json_file(meta_path)
        if meta.get("parent_session_id") == sid and kiro_is_subagent(meta):
            jsonl = meta_path.with_suffix(".jsonl")
            out.append({"id": meta_path.stem, "size": None, "match": "parent_session_id", "source": "kiro",
                        "path": str(jsonl) if jsonl.is_file() else None,
                        "description": trunc(redact(collapse(meta.get("title") or "")), 160) or None})
    return out


def git_toplevel(path, cache):
    """Nearest ancestor of an (edited) file path holding a .git dir or file. Never runs git."""
    if not path.startswith("/"):
        return None
    d = os.path.dirname(path)
    chain, found = [], None
    while d and d != "/":
        if d in cache:
            found = cache[d]
            break
        if os.path.exists(os.path.join(d, ".git")):
            found = d
            break
        chain.append(d)
        d = os.path.dirname(d)
    for c in chain:
        cache[c] = found
    if found:
        cache[found] = found
    return found


def working_dirs(sess, info_cwd=None, limit=5):
    """Most frequent directories the session worked in, as [{path, count, exists}]."""
    counts = Counter(sess["dirs"])
    if sess["source"] == "kiro" and isinstance(info_cwd, str) and info_cwd.startswith("/"):
        counts[redact(os.path.normpath(info_cwd))] += 1
    if sess["source"] == "cursor":
        cache = {}
        for fpath, entry in sess["files"].items():
            top = git_toplevel(fpath, cache)
            if top:
                counts[redact(top)] += entry["edits"]
    rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"path": p, "count": c, "exists": os.path.isdir(p)} for p, c in rows]


def build_meta(sess, selection):
    path = sess["path"]
    st = path.stat()
    turns = sess["turns"]
    real = [t for t in turns if not t["auto"]]
    meta = {
        "source": sess["source"], "uuid": sess["uuid"], "file": str(path), "bytes": st.st_size,
        "file_mtime": iso_mtime(path), "user_turns": len(real),
        "turns_total": len(turns), "auto_notifications": len(turns) - len(real),
        "empty_user_lines_skipped": sess["auto_skipped"], "compactions": sess["compactions"],
        "first_timestamp": next((t["ts"] for t in real if t["ts"]), None),
        "last_timestamp": next((t["ts"] for t in reversed(real) if t["ts"]), None),
        "is_subagent": False, "parent_id": None, "title": None, "project": None, "cwd": None,
        "children": [], "selection": selection,
        "lines_skipped_oversize": sess["stats"]["skipped_big"], "lines_skipped_bad_json": sess["stats"]["bad_json"],
    }
    if sess["source"] == "cursor":
        parts = path.parts
        if "agent-transcripts" in parts:
            meta["project"] = parts[parts.index("agent-transcripts") - 1]
        if path.parent.name == "subagents":
            meta["is_subagent"] = True
            meta["parent_id"] = path.parent.parent.name
        else:
            meta["children"] = cursor_children(path.parent, sess["tasks"])
        meta["working_dirs"] = working_dirs(sess)
    else:
        info = load_json_file(path.with_suffix(".json"))
        meta["cwd"] = info.get("cwd")
        meta["title"] = trunc(redact(collapse(info.get("title") or "")), 160) or None
        meta["created_at"] = info.get("created_at")
        meta["updated_at"] = info.get("updated_at")
        if info.get("session_created_reason"):
            meta["created_reason"] = info["session_created_reason"]
        meta["is_subagent"] = kiro_is_subagent(info)
        meta["parent_id"] = info.get("parent_session_id")
        meta["children"] = kiro_children(path.parent, sess["uuid"])
        meta["working_dirs"] = working_dirs(sess, info.get("cwd"))
        by_turn = {}
        for item in sess["tool_secrets"]:
            by_turn.setdefault(item["turn"], []).append(item["rule"])
        meta["tool_secrets"] = [{"turn": k, "rules": v} for k, v in by_turn.items()]
    return meta


def child_final(kid):
    """Final assistant text (redacted, up to STORE_CAP chars) of a subagent child's own jsonl."""
    if not kid.get("path"):
        return ""
    path = Path(kid["path"])
    try:
        sess = parse_cursor(path) if kid.get("source") == "cursor" else parse_kiro(path)
    except OSError:
        return ""
    return sess["last_text"]


def attach_reports(kids, wanted=None, limit=40):
    """Add kid["final_text"] for the listed children (all of the first `limit`, or the 1-based indexes in wanted)."""
    for idx, kid in enumerate(kids, 1):
        if (wanted is None and idx <= limit) or (wanted is not None and idx in wanted):
            kid["final_text"] = child_final(kid)


# --------------------------------------------------------------------------- related sessions
RELATED_MAX = 10
CURSOR_TS_ZONE = re.compile(r"\s*\(UTC([+-])(\d{1,2})(?::?(\d{2}))?\)\s*$")


def parse_cursor_ts(text):
    """'Thursday, Nov 5, 2026, 11:11 AM (UTC+2)' -> aware datetime, or None."""
    if not text:
        return None
    zone = CURSOR_TS_ZONE.search(text)
    offset = timezone.utc
    if zone:
        minutes = int(zone.group(2)) * 60 + int(zone.group(3) or 0)
        offset = timezone(timedelta(minutes=-minutes if zone.group(1) == "-" else minutes))
        text = text[: zone.start()]
    try:
        return datetime.strptime(text.strip(), "%A, %b %d, %Y, %I:%M %p").replace(tzinfo=offset)
    except ValueError:
        return None


def mentions(path, needle):
    """True when any line of the file contains the bytes (plain `in`, no decoding or JSON)."""
    try:
        with open(path, "rb") as handle:
            for line in handle:
                if needle in line:
                    return True
    except OSError:
        pass
    return False


def describe_hit(path, source, where):
    """Date, project/cwd and first user text of a session file that mentions the uuid."""
    when, ts_text, first = None, None, ""
    stats = {"skipped_big": 0, "bad_json": 0}
    try:
        for i, (_n, obj) in enumerate(iter_lines(path, stats)):
            if i > 40:
                break
            if not isinstance(obj, dict):
                continue
            if source == "cursor" and obj.get("role") == "user":
                content = (obj.get("message") or {}).get("content") if isinstance(obj.get("message"), dict) else None
                raw = "\n".join(b.get("text", "") for b in content or []
                                if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str))
                ts_text, first, _tagged = strip_user(raw)
                when = parse_cursor_ts(ts_text)
            elif source == "kiro" and obj.get("kind") == "Prompt":
                data = obj.get("data") if isinstance(obj.get("data"), dict) else {}
                _ts, first, _tagged = strip_user(kiro_text(data.get("content")))
                epoch = (data.get("meta") or {}).get("timestamp") if isinstance(data.get("meta"), dict) else None
                if isinstance(epoch, (int, float)):
                    when = datetime.fromtimestamp(epoch, timezone.utc)
            else:
                continue
            if first:
                break
    except OSError:
        pass
    date_from = "timestamp"
    if when is None:
        when, date_from = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc), "mtime"
    if source == "kiro":
        where = load_json_file(path.with_suffix(".json")).get("cwd") or "(cwd unknown)"
    utc = when.astimezone(timezone.utc)
    return {"uuid": path.stem, "source": source, "where": redact(str(where)), "when": utc,
            "date": utc.strftime("%Y-%m-%d %H:%M UTC") + ("" if date_from == "timestamp" else " (mtime)"),
            "first_user": trunc(redact(collapse(first)), 160)}


def related_sessions(uuid, croot, kdir, skip_ids=()):
    """Sessions (Cursor parents of every slug, Kiro CLI) whose file contains the full uuid.
    Returns (hits sorted by date, total hit count). Skips the session itself and `skip_ids`."""
    needle = uuid.encode("ascii")
    cands = []
    if croot.is_dir():
        for proj in sorted(p for p in croot.iterdir() if p.is_dir()):
            base = proj / "agent-transcripts"
            if not base.is_dir():
                continue
            for folder in base.iterdir():
                parent = folder / f"{folder.name}.jsonl"
                if folder.name.lower() != uuid.lower() and parent.is_file():
                    cands.append((parent, "cursor", proj.name))
    if kdir.is_dir():
        for path in kdir.glob("*.jsonl"):
            if path.stem.lower() != uuid.lower() and path.stem not in skip_ids:
                cands.append((path, "kiro", None))
    hits = []
    for path, source, where in cands:
        try:
            if path.stat().st_size >= len(needle) and mentions(path, needle):
                hits.append(describe_hit(path, source, where))
        except OSError:
            continue
    hits.sort(key=lambda h: (h["when"], h["uuid"]))
    return hits[:RELATED_MAX], len(hits)


# --------------------------------------------------------------------------- view + render
BASE = {"edge_final": 3000, "mid_final": 1500, "cmds_edge": 12, "cmds_mid": 8, "signals": 30,
        "user": 1500, "last": 12000, "files": 50, "collapse": False, "cuser": 100, "compaction": 2000, "steer": 600,
        "fullcmd": False, "kid": 500}
FULL = {"edge_final": None, "mid_final": None, "cmds_edge": None, "cmds_mid": None, "signals": 400,
        "user": None, "last": None, "files": 10 ** 6, "collapse": False, "cuser": None, "compaction": None, "steer": None,
        "fullcmd": True, "kid": 3000}
MIN_SIGNALS = 6  # the open-signal section is never dropped entirely
PROTECTED_FINAL = 600  # a final text with a question or open-signal marker keeps at least this much
LEVEL_STEPS = [  # applied cumulatively; order follows the budget rules in the brief
    {},
    {"kid": 250},
    {"mid_final": 800}, {"mid_final": 300}, {"mid_final": 0},
    {"cmds_mid": 3}, {"cmds_mid": 0},
    {"cmds_edge": 5}, {"cmds_edge": 0},
    {"compaction": 800, "steer": 300},
    {"user": 800, "edge_final": 1500, "last": 8000, "files": 30},
    {"signals": 15}, {"signals": 8},
    {"user": 400, "edge_final": 800, "last": 4000, "files": 15, "compaction": 300, "kid": 120},
    {"collapse": True},
    {"user": 160, "edge_final": 250, "last": 1500, "files": 10, "signals": MIN_SIGNALS},
    {"cuser": 50, "last": 800, "files": 5, "compaction": 150, "steer": 150, "kid": 0},
]


def levels():
    params = dict(BASE)
    for step in LEVEL_STEPS:
        params.update(step)
        yield dict(params)


def asks_or_open(turn):
    """True when the turn's final text asks the user something or carries an open-signal marker."""
    text = turn["final"]
    if not text:
        return False
    if turn["questions"] or SIGNAL_RE.search(FENCE.sub(" ", text)):
        return True
    return any(s.endswith("?") and not s.endswith("??") for s in sentences(text))


def view_kid(kid, P):
    """Child record for display: the final text cut to P["kid"] chars (0 hides final text and path)."""
    out = {k: v for k, v in kid.items() if k != "final_text"}
    if not P["kid"]:
        out["path"] = None
    elif "final_text" in kid:
        out["final"] = trunc(collapse(kid["final_text"]), P["kid"])
    return out


HEADER_KEYS = ("source", "uuid", "user_turns", "turns_total", "auto_notifications")


def build_view(sess, meta, P, only=None, final_only=False):
    turns = sess["turns"]
    real_idx = {t["n"]: i for i, t in enumerate(t for t in turns if not t["auto"])}
    n_real = len(real_idx)
    vturns = []
    for t in turns:
        if only is not None and t["n"] not in only:
            continue
        base = {"n": t["n"], "ts": t["ts"], "lines": [t["l0"], t["l1"]]}
        if final_only:
            vturns.append({**base, "auto": t["auto"], "collapsed": False, "final_only": True, "user": t["user"],
                           "final": t["final"] or None, "final_line": t["final_line"]})
            continue
        if t["auto"] and only is None:
            vturns.append({**base, "auto": True, "collapsed": False,
                           "text": trunc(strip_boilerplate(re.sub(r"</?[A-Za-z_][^>]*>", " ", t["user"])), 120) or "subagent completion",
                           "lead": t["lead"],
                           "tools": dict(t["tools"].most_common()), "questions": t["questions"][:3]})
            continue
        i = real_idx.get(t["n"], 0)
        edge = only is not None or i < 2 or i >= n_real - 3
        protected = only is None and asks_or_open(t)
        limit = P["edge_final"] if edge else P["mid_final"]
        if limit is not None and protected:
            limit = max(limit, PROTECTED_FINAL)
        is_last = (only is None and t["final"] and t["final"] == sess["last_text"]
                   and t["final_line"] == sess["last_text_line"])
        if P["collapse"] and not edge:
            vturns.append({**base, "auto": False, "collapsed": True, "user": trunc(collapse(t["user"]), P["cuser"]),
                           "final": None if is_last or not protected else trunc(t["final"], PROTECTED_FINAL),
                           "final_line": t["final_line"], "final_is_last": bool(is_last),
                           "steering": [trunc(x, P["steer"]) for x in t["steer"]]})
            continue
        ncmd = P["cmds_edge"] if edge else P["cmds_mid"]
        cmds = [{"cmd": rec["full"] if P["fullcmd"] else rec["cmd"], "exit": rec["exit"], "err": rec["err"]}
                for rec in t["cmds"][:ncmd]]
        final = None
        if t["final"] and not is_last and (limit is None or limit > 0):
            final = trunc(t["final"], limit)
        questions = list(t["questions"])
        if final != trunc(t["final"], None) and not is_last:  # text is cut or omitted: keep its questions
            for sent in sentences(t["final"]):
                if sent.endswith("?") and not sent.endswith("??") and len(questions) < 3:
                    questions.append(trunc(sent, 160))
        vturns.append({
            **base, "auto": t["auto"], "collapsed": False, "user": trunc(t["user"], P["user"]),
            "tools": dict(t["tools"].most_common()),
            "files": [{"path": p, "action": a} for p, a in t["files"].items()],
            "commands": cmds, "commands_more": max(len(t["cmds"]) - len(cmds), 0),
            "subagents": t["subagents"] if only is not None else t["subagents"][:8],
            "questions": questions if only is not None else questions[:3],
            "steering": [trunc(x, P["steer"]) for x in t["steer"]],
            "tool_errors": t["tool_errors"],
            "final": final, "final_line": t["final_line"], "final_is_last": bool(is_last),
            "final_omitted": bool(t["final"]) and not is_last and final is None,
        })
    shown = {v["n"] for v in vturns}
    markers = []
    for mk in ([] if final_only else sess["markers"]):
        if only is not None and not (mk["after"] in shown or (mk["kind"] == "clear" and mk["after"] + 1 in shown)):
            continue
        markers.append({"after": mk["after"], "kind": mk["kind"], "line": mk["line"],
                        "text": trunc(mk["text"], P["compaction"]) if mk["kind"] == "compaction" else ""})
    if only is not None:  # drill-down: compact header instead of Meta
        return {"meta": {k: meta[k] for k in HEADER_KEYS}, "turns": vturns, "markers": markers}
    meta = dict(meta, children=[view_kid(k, P) for k in meta["children"]])
    view = {"meta": meta, "turns": vturns, "markers": markers}
    rows = sorted(sess["files"].items(), key=lambda kv: (-kv[1]["edits"], kv[1]["first"], kv[0]))
    signals = sess["signals"][-P["signals"]:] if P["signals"] > 0 else []
    view.update({
        "files_touched": {
            "total": len(rows),
            "rows": [{"path": p, "edits": e["edits"], "first_turn": e["first"], "last_turn": e["last"]}
                     for p, e in rows[: P["files"]]],
            "more": max(len(rows) - P["files"], 0),
        },
        "open_signals": [dict(s) for s in signals],
        "open_signals_total": len(sess["signals"]),
        "final_message": trunc(sess["last_text"], P["last"]) if sess["last_text"] else "",
        "final_message_line": sess["last_text_line"],
    })
    return view


def quote(text):
    return "\n".join(("> " + line).rstrip() for line in text.splitlines())


def lines_label(lines):
    a, b = lines
    return f"jsonl line {a}" if a == b else f"jsonl lines {a}-{b}"


def render_meta(m):
    out = [f"# Session digest {m['uuid'][:8]}", "", "## Meta"]
    out.append(f"- Source: {m['source']}")
    out.append(f"- Session id: {m['uuid']}")
    if m.get("project"):
        out.append(f"- Project slug: {m['project']}")
    if m.get("cwd"):
        out.append(f"- Cwd: {m['cwd']}")
    dirs = m.get("working_dirs") or []
    if dirs:
        out.append("- Working dirs: " + ", ".join(
            f"{d['path']} ×{d['count']}" + ("" if d["exists"] else " (missing now)") for d in dirs))
    else:
        out.append("- Working dirs: none found")
    if m.get("title"):
        out.append(f"- Title: {m['title']}")
    out.append(f"- First / last timestamp: {m['first_timestamp'] or 'n/a'} / {m['last_timestamp'] or 'n/a'}")
    out.append(f"- File: {m['file']} ({m['bytes']:,} bytes, modified {m['file_mtime']})")
    extra = [f"auto notifications collapsed: {m['auto_notifications']}"]
    if m["compactions"]:
        extra.append(f"compactions: {m['compactions']}")
    if m["empty_user_lines_skipped"]:
        extra.append(f"empty user lines skipped: {m['empty_user_lines_skipped']}")
    out.append(f"- User turns: {m['user_turns']} ({', '.join(extra)}); turn numbers count auto notifications too")
    out.append(f"- Subagent session: {'yes' if m['is_subagent'] else 'no'}"
               + (f" (parent {m['parent_id']})" if m["is_subagent"] and m["parent_id"] else ""))
    if m.get("created_reason") and not m["is_subagent"]:
        out.append(f"- Created reason: {m['created_reason']}"
                   + (f" (parent_session_id {m['parent_id']})" if m["parent_id"] else ""))
    if m.get("selection"):
        out.append(f"- Selection: {m['selection']}")
    if m["lines_skipped_oversize"] or m["lines_skipped_bad_json"]:
        out.append(f"- Parse notes: {m['lines_skipped_oversize']} line(s) over 5 MB skipped, "
                   f"{m['lines_skipped_bad_json']} unparseable line(s) skipped")
    secrets = m.get("tool_secrets") or []
    if secrets:
        shown = [f"turn {x['turn']} ({', '.join(x['rules'])})" for x in secrets[:12]]
        more = f", +{len(secrets) - 12} more turns" if len(secrets) > 12 else ""
        out.append("- Secret-like values seen in tool output: " + ", ".join(shown) + more + " (values not shown)")
    kids = m["children"]
    out.append(f"- Subagent children: {len(kids)}" if kids else "- Subagent children: none")
    for idx, kid in enumerate(kids[:40], 1):
        size = f", {kid['size']:,} bytes" if kid.get("size") else ""
        out.append(f"  - [{idx}] {kid['id'][:8]}: {kid['description'] or '(no matching description)'} [{kid['match']}{size}]")
        if kid.get("final") is not None:
            out.append(f"    - Final: {kid['final'] or '(no final assistant text)'}")
        if kid.get("path"):
            out.append(f"    - File: {kid['path']}")
    if len(kids) > 40:
        out.append(f"  - +{len(kids) - 40} more")
    return out


def render_header(m):
    return [f"Session id: {m['uuid']}",
            f"Source: {m['source']}",
            f"Turns: {m['user_turns']} user turns ({m['turns_total']} numbered, "
            f"{m['auto_notifications']} of them auto notifications)"]


def render_related(m):
    hits = m["related"]
    out = ["", "## Later sessions that mention this one"]
    if not hits:
        return out + ["(none found)"]
    for h in hits:
        out.append(f"- {h['uuid']} — {h['source']} — {h['where']} — {h['date']}: "
                   + (h["first_user"] or "(no user text)"))
    if m.get("related_total", 0) > len(hits):
        out.append(f"- +{m['related_total'] - len(hits)} later matches not shown (earliest {len(hits)} listed)")
    return out


def render_subagent_reports(reports):
    out = []
    for r in reports:
        out += ["", f"## Subagent {r['index']} of {r['of']} — {r['id'][:8]}"
                    + (f": {r['description']}" if r.get("description") else ""),
                f"- File: {r['path']}" if r.get("path") else "- File: (not found)",
                quote(r["final"]) if r["final"] else "> (no final assistant text)"]
    return out


def render_turn(t, out):
    head = f"### Turn {t['n']} — {t['ts'] or 'no timestamp'} — {lines_label(t['lines'])}"
    out += ["", head]
    if t.get("final_only"):
        out.append(quote(t["user"]) if t["user"] else "> (no user text)")
        where = f", jsonl line {t['final_line']}" if t.get("final_line") else ""
        out += [f"**Assistant (final text{where}):**", quote(t["final"])] if t.get("final") else [
            "**Assistant (final text):** none"]
        return
    if t["collapsed"]:
        out.append(f"{t['user']} _(collapsed for budget)_")
        for msg in t.get("steering", []):
            out.append(quote(f"(mid-turn user message) {msg}"))
        if t.get("final"):
            out += ["**Assistant (final text):**", quote(t["final"])]
        return
    out.append(quote(t["user"]) if t["user"] else "> (no user text)")
    if t.get("auto"):
        out.append("_(auto notification, shown in full because it was requested)_")
    if t["tools"]:
        out.append("- Tools: " + ", ".join(f"{k} x{v}" for k, v in t["tools"].items()))
    if t["files"]:
        shown = [f"{f['path']} ({f['action']})" for f in t["files"][:12]]
        more = f", +{len(t['files']) - 12} more" if len(t["files"]) > 12 else ""
        out.append("- Files written: " + ", ".join(shown) + more)
    if t["commands"] or t["commands_more"]:
        out.append("- Commands:" if t["commands"] else f"- Commands: {t['commands_more']} (list omitted for budget)")
        for c in t["commands"]:
            status = ""
            if c["exit"] is not None:
                status = f" (exit {c['exit']}" + (f"; stderr: {c['err']}" if c.get("err") else "") + ")"
            out.append(f"  - `{c['cmd']}`{status}")
        if t["commands_more"] and t["commands"]:
            out.append(f"  - +{t['commands_more']} more")
    if t["subagents"]:
        out.append("- Subagents launched: " + "; ".join(t["subagents"]))
    if t["questions"]:
        out.append("- Questions to user: " + " | ".join(t["questions"]))
    if t["tool_errors"]:
        out.append(f"- Tool errors: {t['tool_errors']}")
    for msg in t["steering"]:
        out.append(quote(f"(mid-turn user message) {msg}"))
    where = f", jsonl line {t['final_line']}" if t.get("final_line") else ""
    if t.get("final"):
        out += [f"**Assistant (final text{where}):**", quote(t["final"])]
    elif t.get("final_is_last"):
        out.append("**Assistant (final text):** same as the Final assistant message below")
    elif t.get("final_omitted"):
        out.append("**Assistant (final text):** omitted for budget")


def render_markers(markers, out):
    for mk in markers:
        if mk["kind"] == "clear":
            out += ["", "— /clear —"]
        else:
            out += ["", f"#### Compaction summary (jsonl line {mk['line']})",
                    quote(mk["text"]) if mk["text"] else "> (empty)"]


def render_md(view, turn_mode=False):
    m = view["meta"]
    if turn_mode:  # drill-down: 3-line header, no Meta
        out = render_header(m)
    else:
        out = render_meta(m)
        if "related" in m:
            out += render_related(m)
        out += ["", "## Turns"]
    by_after = {}
    for mk in view["markers"]:
        by_after.setdefault(mk["after"], []).append(mk)
    if not view["turns"] and not turn_mode:
        out.append("(no user turns found)")
    if not turn_mode:
        render_markers(by_after.get(0, []), out)
    for t in view["turns"]:
        if turn_mode:  # a /clear right before the requested turn is part of its context
            render_markers([mk for mk in by_after.get(t["n"] - 1, []) if mk["kind"] == "clear"], out)
        if t.get("auto") and not t["collapsed"] and "text" in t:
            if out and not out[-1].startswith("Turn "):
                out.append("")
            line = f"Turn {t['n']}: auto notification — {t['text']}"
            if t["lead"]:
                line += f" → result: {t['lead']}"
            if t["tools"]:
                line += " [tools: " + ", ".join(f"{k} x{v}" for k, v in t["tools"].items()) + "]"
            if t["questions"]:
                line += " [asks: " + " | ".join(t["questions"]) + "]"
            out.append(line + f" ({lines_label(t['lines'])})")
        else:
            render_turn(t, out)
        render_markers([mk for mk in by_after.get(t["n"], []) if not turn_mode or mk["kind"] == "compaction"], out)
    if turn_mode:
        out += render_subagent_reports(view.get("subagent_reports") or [])
        return "\n".join(out)

    ft = view["files_touched"]
    out += ["", "## Files touched (whole session)"]
    if ft["rows"]:
        out += ["| path | present | edits | first turn | last turn |", "|---|---|---|---|---|"]
        for r in ft["rows"]:
            path = r["path"]
            present = "yes" if os.path.isfile(path) else "no"
            out.append(
                f"| {path.replace('|', chr(92) + '|')} | {present} | {r['edits']} | {r['first_turn']} | {r['last_turn']} |"
            )
        if ft["more"]:
            out.append(f"| +{ft['more']} more files | | | |")
        if m["source"] == "kiro":
            out.append("_Kiro: edits made through shell commands (sed, redirects) are not listed._")
    else:
        out.append("(no file edits recorded)")

    out += ["", "## Open-signal lines"]
    if view["open_signals"]:
        out += [f"- Turn {s['turn']}: {s['text']}" for s in view["open_signals"]]
    elif view["open_signals_total"]:
        out.append("(omitted for budget)")
    else:
        out.append("(none found)")

    out += ["", "## Final assistant message"]
    if view["final_message"]:
        if view.get("final_message_line"):
            out.append(f"- jsonl line: {view['final_message_line']}")
        out.append(quote(view["final_message"]))
    else:
        out.append("(none)")
    return "\n".join(out)


def make_output(sess, meta, max_chars, as_json, full=False, only=None, final_only=False, reports=None):
    """Pick the least-shrunk level that fits max_chars; return (text, chars, truncated).
    With full or only (--turn / --subagent drill-down) there is no budget: nothing is truncated.
    reports: [{index, of, id, description, path, final}] printed after the turns in drill-down mode."""
    trailer_room = 80
    result = None
    if full or only is not None:
        steps = [dict(FULL)]
    else:
        steps = list(levels())
    for idx, params in enumerate(steps):
        view = build_view(sess, meta, params, only, final_only)
        if reports:
            view["subagent_reports"] = reports
        view = redact_obj(view)
        body = json.dumps(view, ensure_ascii=False) if as_json else render_md(view, turn_mode=only is not None)
        result = (view, body, idx)
        if full or only is not None or len(body) + trailer_room <= max_chars:
            break
    view, body, idx = result
    truncated = idx > 0
    if as_json:
        view["digest"] = {"chars": 0, "truncated": truncated, "shrink_level": idx}
        for _ in range(3):  # converge: the digits of the count are part of the text
            view["digest"]["chars"] = len(json.dumps(view, ensure_ascii=False))
        text = json.dumps(view, ensure_ascii=False)
        return text, len(text), truncated
    chars = len(body)
    for _ in range(3):
        trailer = f"\n<!-- digest: {chars} chars, truncated: {'yes' if truncated else 'no'} -->"
        chars = len(body) + len(trailer)
    return body + trailer, chars, truncated


# --------------------------------------------------------------------------- main
EPILOG = """\
common usages:
  session_digest.py 70677439                    digest by uuid prefix (>= 6 hex chars), default budget
  session_digest.py --latest --cwd "$PWD"       newest session for a directory (both tools)
  session_digest.py --latest --source kiro      newest Kiro CLI session only
  session_digest.py 70677439 --turn 3           3-line header + turn 3 in full (repeat --turn for more turns)
  session_digest.py 70677439 --turn 3 --final-only   only the user text and final assistant text of turn 3
  session_digest.py 70677439 --subagent 2       full final text of subagent child 2 (index as listed in Meta)
  session_digest.py 70677439 --subagent all     final text of every child (each cut at 3000 chars)
  session_digest.py 70677439 --no-related       skip the scan for later sessions that mention this one
  session_digest.py 70677439 --full             nothing truncated (stderr warning above 150k chars)
  session_digest.py 70677439 --max-chars 80000  raise the budget instead of using --full
  session_digest.py --path FILE.jsonl --json    explicit file, machine-readable output
  session_digest.py 70677439 | head -60         piping into head is safe

exit codes: 0 ok, 2 not found / bad arguments, 3 ambiguous prefix (JSON list on stdout)
"""


def fail(message, code=2):
    print(message, file=sys.stderr)
    return code


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Compact, redacted digest of one agent session (Cursor or Kiro CLI).",
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", nargs="?", help="session uuid or unique prefix (>= 6 chars)")
    ap.add_argument("--latest", action="store_true", help="newest parent session for --cwd")
    ap.add_argument("--cwd", default=None, help="working directory for --latest (default: current)")
    ap.add_argument("--source", choices=["cursor", "kiro"], default=None)
    ap.add_argument("--path", default=None, help="digest an explicit .jsonl file")
    ap.add_argument("--max-chars", type=int, default=40000, help="output budget (default 40000)")
    ap.add_argument("--turn", type=int, action="append", metavar="N", default=None,
                    help="print a 3-line header plus only turn N, in full (repeatable)")
    ap.add_argument("--final-only", action="store_true",
                    help="with --turn: only the user text and the final assistant text of the turn")
    ap.add_argument("--subagent", default=None, metavar="N|all",
                    help="print the full final text of subagent child N (index as listed in Meta) or of all "
                         "children (each up to 3000 chars)")
    ap.add_argument("--no-related", action="store_true",
                    help="skip the scan for later sessions that mention this one")
    ap.add_argument("--full", action="store_true", help="no per-item truncation (still redacted)")
    ap.add_argument("--json", action="store_true", dest="as_json", help="machine output instead of markdown")
    args = ap.parse_args(argv)

    modes = [bool(args.id), args.latest, bool(args.path)]
    if sum(modes) != 1:
        return fail("give exactly one of: <id>, --latest, --path FILE")
    if args.max_chars < 1000:
        return fail("--max-chars must be at least 1000")
    if args.turn and any(n < 1 for n in args.turn):
        return fail("--turn needs a positive turn number")
    if args.final_only and not args.turn:
        return fail("--final-only needs --turn N")
    if args.subagent is not None and args.subagent != "all" and not (args.subagent.isdigit() and int(args.subagent) >= 1):
        return fail("--subagent needs a positive child number or 'all'")

    croot, kdir = cursor_root(), kiro_dir()
    selection = None
    source = None
    if args.path:
        path = Path(args.path)
        if not path.is_file():
            return fail(f"file not found: {path}")
        source = sniff_source(path)
    elif args.latest:
        cwd = args.cwd or os.getcwd()
        want = [args.source] if args.source else ["cursor", "kiro"]
        roots_ok = {"cursor": croot.is_dir(), "kiro": kdir.is_dir()}
        if not any(roots_ok[s] for s in want):
            return fail(f"no session roots found (cursor: {croot}, kiro: {kdir})")
        cands = {}
        if "cursor" in want and roots_ok["cursor"]:
            hit = cursor_latest(croot, cwd)
            if hit:
                cands["cursor"] = hit
        if "kiro" in want and roots_ok["kiro"]:
            hit = kiro_latest(kdir, cwd)
            if hit:
                cands["kiro"] = hit
        if not cands:
            return fail(f"no session found for cwd {cwd} (sources: {', '.join(want)})")
        source = max(cands, key=lambda s: cands[s][1])
        path = cands[source][0]
        stamp = lambda s: datetime.fromtimestamp(cands[s][1], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if len(cands) == 2:
            selection = (f"latest for {cwd}: both sources have one (cursor {stamp('cursor')}, kiro {stamp('kiro')}); "
                         f"picked newest overall: {source}")
        else:
            selection = f"latest for {cwd}: {source} only ({stamp(source)})"
    else:
        if not ID_ARG.match(args.id):
            return fail("id must be 6-36 hex characters (uuid or unique prefix)")
        if not croot.is_dir() and not kdir.is_dir():
            return fail(f"no session roots found (cursor: {croot}, kiro: {kdir})")
        matches = find_by_id(args.id, croot, kdir)
        if not matches:
            return fail(f"no session matches id {args.id}")
        if len(matches) > 1:
            listing = [{"path": str(p), "source": s, "kind": k, "mtime": iso_mtime(p)} for p, s, k in matches]
            print(json.dumps({"error": "ambiguous", "id": args.id, "matches": listing}, indent=2))
            sys.stdout.flush()
            return 3
        path, source, _kind = matches[0]

    try:
        sess = parse_cursor(path) if source == "cursor" else parse_kiro(path)
        meta = build_meta(sess, selection)
    except OSError as exc:
        return fail(f"cannot read {path}: {exc}")
    only = None
    reports = None
    if args.turn:
        total = len(sess["turns"])
        bad = [n for n in args.turn if n > total]
        if bad:
            return fail(f"turn {bad[0]} not found (session has {total} turns)")
        only = set(args.turn)
    if args.subagent is not None:
        kids = meta["children"]
        if not kids:
            return fail("session has no subagent children")
        if args.subagent == "all":
            wanted, cap = set(range(1, len(kids) + 1)), 3000
        else:
            wanted, cap = {int(args.subagent)}, None
            if int(args.subagent) > len(kids):
                return fail(f"subagent {args.subagent} not found (session has {len(kids)} children)")
        attach_reports(kids, wanted)
        reports = [{"index": i, "of": len(kids), "id": kid["id"], "description": kid.get("description"),
                    "path": kid.get("path"), "final": trunc(kid.get("final_text") or "", cap)}
                   for i, kid in enumerate(kids, 1) if i in wanted]
        only = only if only is not None else set()
    drill = only is not None
    if not drill:
        attach_reports(meta["children"])
        if not args.no_related and UUID.match(sess["uuid"]):
            hits, total = related_sessions(sess["uuid"], croot, kdir, {k["id"] for k in meta["children"]})
            meta["related"] = [{k: v for k, v in h.items() if k != "when"} for h in hits]
            meta["related_total"] = total
    text, chars, _trunc = make_output(sess, meta, args.max_chars, args.as_json, full=args.full, only=only,
                                      final_only=args.final_only, reports=reports)
    if (args.full or drill) and chars > 150_000:
        print(f"warning: output is {chars:,} chars (over 150,000); consider --turn N or a lower --max-chars",
              file=sys.stderr)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)
    sys.stdout.flush()
    return 0


def run():
    try:
        code = main()
        sys.stdout.flush()
        return code
    except BrokenPipeError:  # e.g. piped into `head`: stop quietly
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except OSError:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(run())
