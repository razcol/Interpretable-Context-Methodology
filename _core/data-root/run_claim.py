#!/usr/bin/env python3
"""Claims for workflow runs, so runs on different keys never block each other.

The rules live in "Run claims" under "Data root" in _core/CONVENTIONS.md. Python 3
standard library only. Every command prints one JSON object.

  claim   --ws WS --key KEY [--base B [--label L]]
                                        claim a run key before the run's first stage (prints claimId, runId)
  port    --ws WS --key KEY --kind K    the run's own port (dev or cdp), the same one on every call
  target  --ws WS --key KEY --path P --root R --branch B
                                        claim the target-repo work tree (and branch) the run edits
  commit  --ws WS --key KEY [--stage S] commit only this run's folder in the data repo (serialized)
  end     --ws WS --key KEY --claim-id ID
                                        end the run: drop its claims, then commit its folder
  list    [--ws WS]                     every claim, live or stale (`status` shows the live ones)

Deprecated: `release` is `end`, `--token` is `--claim-id`, and `claim` still prints `token`
next to `claimId`, so callers written before `end` keep working.

Where claims live:
  key claim      <data checkout>/workspaces/<ws>/runs/<KEY>/claim.lock (the checkout `resolve` prints)
  port, target   <main data checkout>/claims/{ports,targets}/*.lock (machine-wide, shared by a
                 maintenance worktree's test runs and normal runs)
Every claim file ends in .lock, which the data repo ignores, so a claim is never committed.

A key claim is stale when its process is gone (or its PID now belongs to another process),
when the ai-system checkout it recorded is gone, or when it was not touched for STALE_AFTER
seconds. `claim` stops on a live claim (exit 3, naming it) and replaces a stale one,
reporting it, so the next run on that key can continue. A port or target claim is live only
while the key claim that made it is live and has the same owner.

Exit codes: 0 ok, 2 bad arguments or no data root, 3 a live run holds what was asked for.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import socket
import sys
import time
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data_root as dr  # noqa: E402

VERSION = 1
CLAIM = "claim.lock"
RUN_META = "run.json"
SHARED = "claims"
OPS_LOCK = ".ops.lock"
STALE_AFTER = 2 * 3600
RANGES = {"dev": (3000, 3049), "cdp": (9340, 9399)}
WS_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
JIRA_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
BASE_LINE_RE = re.compile(r"^\s*-\s*base:\s*`?([^\s`]+)`?")
BRANCH_ORIGIN_RE = re.compile(r"^\s*-\s*branch:.*\b(?:from|at)\s+`?origin/([^\s`),;:]+)`?")
HANDOFF_DIFF_RE = re.compile(r"\bDiff\s+(?:against|vs\.?)\s+`?origin/([^\s`),;:]+)`?")
# Processes between the agent and this script that do not outlive one command.
TRANSIENT = {"bash", "sh", "dash", "zsh", "fish", "env", "timeout", "nice", "nohup", "sudo",
             "script", "stdbuf", "xargs", "flock", "time"}


class Held(Exception):
    """A live run holds what was asked for (exit 3)."""

    def __init__(self, message, holder):
        super().__init__(message)
        self.holder = holder


class Bad(Exception):
    """Bad arguments or no data root (exit 2)."""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


# ---------- processes ----------

def proc_stat(pid):
    """(comm, ppid, start ticks, state) from /proc, or None when the process is gone."""
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    comm = text[text.index("(") + 1:text.rindex(")")]
    rest = text[text.rindex(")") + 2:].split()
    return comm, int(rest[1]), rest[19], rest[0]


def owner_pid(start=None):
    """The long-lived process that runs this workflow: the first ancestor that is not a shell
    or an interpreter running one command (in Claude Code, the session's own process)."""
    pid = start or os.getppid()
    while pid and pid > 1:
        st = proc_stat(pid)
        if st is None:
            break
        comm, ppid = st[0], st[1]
        if comm not in TRANSIENT and not comm.startswith("python"):
            return pid
        pid = ppid
    return os.getppid()


def alive(pid, start_ticks):
    st = proc_stat(pid)
    if st is None or st[3] in ("Z", "X"):
        return False
    return start_ticks is None or st[2] == start_ticks


# ---------- places ----------

def places(data=None, code=HERE):
    """(data checkout for key claims, folder for shared claims, ai-system checkout)."""
    try:
        top = dr.checkout_info(code)[0]
        if data:
            data = Path(data).expanduser()
            return data, data / SHARED, top
        return dr.resolve(code), dr.data_root(code) / SHARED, top
    except dr.Stop as e:
        raise Bad(str(e))


def check_names(ws, key):
    if not WS_RE.match(ws or ""):
        raise Bad(f"bad workspace name: {ws!r}")
    if not KEY_RE.match(key or "") or ".." in key:
        raise Bad(f"bad run key: {key!r}")


def run_dir(data, ws, key):
    return Path(data) / "workspaces" / ws / "runs" / key


def key_file(data, ws, key):
    return run_dir(data, ws, key) / CLAIM


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def write(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.lock")  # ignored like the claim itself
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, path)


@contextmanager
def ops_lock(shared):
    """Every claim change, on any key, happens under one short lock."""
    Path(shared).mkdir(parents=True, exist_ok=True)
    with open(Path(shared) / OPS_LOCK, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# ---------- liveness ----------

def key_state(record, at=None):
    """('live', '') or ('stale', reason) for a key claim record."""
    if not record:
        return "stale", "unreadable claim file"
    if not alive(record.get("pid"), record.get("pidStart")):
        return "stale", f"process {record.get('pid')} is gone"
    checkout = record.get("checkout")
    if checkout and not Path(checkout).exists():
        return "stale", f"checkout {checkout} is gone"
    touched = record.get("touchedEpoch", 0)
    if (at or time.time()) - touched > STALE_AFTER:
        return "stale", f"not touched for more than {STALE_AFTER // 3600} hours"
    return "live", ""


def shared_state(record):
    if not record:
        return "stale", "unreadable claim file"
    owner = read(record.get("keyClaim", ""))
    if not owner or owner.get("pid") != record.get("pid") or owner.get("pidStart") != record.get("pidStart"):
        return "stale", "the run that made it no longer holds its key"
    return key_state(owner)


def summary(record):
    keep = ("ws", "key", "jira", "base", "label", "pid", "startedAt", "touchedAt", "checkout", "ports", "targets")
    return {k: record.get(k) for k in keep if k in record}


def public(record):
    return {k: v for k, v in record.items() if k not in ("pidStart", "keyClaim", "token", "touchedEpoch", "version")}


def live_owner(data, ws, key):
    record = read(key_file(data, ws, key))
    if record is None:
        raise Bad(f"no claim for {ws} {key}: run `claim` first")
    state, reason = key_state(record)
    if state != "live":
        raise Bad(f"the claim for {ws} {key} is stale ({reason}): run `claim` again")
    return record


def touch(path, record):
    record["touchedAt"], record["touchedEpoch"] = now(), time.time()
    write(path, record)


# ---------- multi-base / labeled slots ----------

def strip_origin(branch):
    s = (branch or "").strip()
    if s.startswith("origin/"):
        s = s[len("origin/"):]
    return s.rstrip("`),;:")


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


def validate_run_id(run_id):
    if not KEY_RE.match(run_id or "") or ".." in run_id:
        raise Bad(f"run id {run_id!r} exceeds run-key rules (^[A-Za-z0-9][A-Za-z0-9._-]{{0,63}}$)")
    if not PROFILE_RE.match(run_id.lower()):
        raise Bad(f"run id {run_id!r} fails browser profile limit (^[a-z0-9][a-z0-9-]{{0,40}}$, max 41 chars)")


def read_run_meta(folder):
    path = Path(folder) / RUN_META
    if not path.exists():
        return None, False
    data = read(path)
    if not isinstance(data, dict):
        raise Bad(f"unreadable {RUN_META} in {folder}")
    return data, True


def read_base_line(path):
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        m = BASE_LINE_RE.match(line)
        if m:
            b = strip_origin(m.group(1))
            if b:
                return b
    return None


def mixed_bases(folder):
    """Collect distinct base slugs across the five authoritative run record files."""
    folder = Path(folder)
    seen = {}

    def add(raw):
        b = strip_origin(raw)
        s = slugify(b)
        if s and s not in seen:
            seen[s] = b

    for rel in ("01-intake/intake.md", "03-plan/plan.md"):
        b = read_base_line(folder / rel)
        if b:
            add(b)

    for rel in ("04-implement/implement-record.md", "03b-baseline/baseline-record.md"):
        p = folder / rel
        if p.is_file():
            for line in p.read_text(errors="replace").splitlines():
                m = BRANCH_ORIGIN_RE.match(line)
                if m:
                    add(m.group(1))

    handoff = folder / "06-handoff" / "handoff.md"
    if handoff.is_file():
        for line in handoff.read_text(errors="replace").splitlines():
            m = HANDOFF_DIFF_RE.search(line)
            if m:
                add(m.group(1))

    return list(seen.values())


def resolve_slot(data, ws, key, base, label):
    """Resolve (run_id, jira, stored_base, label_slug) inside ops_lock."""
    if base is None:
        if label is not None:
            raise Bad("--label requires --base")
        return key, None, None, None

    if "--" in key or not JIRA_RE.match(key):
        raise Bad(f"--base requires a Jira key ([A-Z][A-Z0-9]+-\\d+, no '--'), got {key!r}")

    base_clean = strip_origin(base)
    base_slug = slugify(base_clean)
    if not base_slug:
        raise Bad(f"empty base slug for {base!r}")

    if label is not None:
        label_slug = slugify(label)
        if not label_slug:
            raise Bad(f"empty label slug for {label!r}")
        run_id = f"{key}--{base_slug}--{label_slug}"
        validate_run_id(run_id)
        folder = run_dir(data, ws, run_id)
        if folder.exists():
            meta, exists = read_run_meta(folder)
            if (not exists or meta.get("jira") != key
                    or slugify(strip_origin(meta.get("base", ""))) != base_slug
                    or meta.get("label") != label_slug
                    or (meta.get("runId") and meta.get("runId") != run_id)):
                raise Bad(f"existing folder runs/{run_id} has missing or mismatched {RUN_META}")
            base_clean = meta["base"]
        return run_id, key, base_clean, label_slug

    suf = f"{key}--{base_slug}"
    suf_dir = run_dir(data, ws, suf)
    if suf_dir.exists():
        meta, exists = read_run_meta(suf_dir)
        if (not exists or meta.get("jira") != key
                or slugify(strip_origin(meta.get("base", ""))) != base_slug
                or meta.get("label") is not None
                or (meta.get("runId") and meta.get("runId") != suf)):
            raise Bad(f"existing folder runs/{suf} has missing or mismatched {RUN_META}")
        validate_run_id(suf)
        return suf, key, meta["base"], None

    pri_dir = run_dir(data, ws, key)
    pri_meta, _ = read_run_meta(pri_dir)
    if pri_meta:
        if pri_meta.get("label") is not None:
            raise Bad(f"runs/{key} has a label ({pri_meta.get('label')}) and is not an unlabeled slot")
        if pri_meta.get("jira") and pri_meta.get("jira") != key:
            raise Bad(f"runs/{key}/{RUN_META} belongs to {pri_meta.get('jira')}, not {key}")

    intake_base = read_base_line(pri_dir / "01-intake" / "intake.md")
    meta_base = strip_origin(pri_meta.get("base", "")) if pri_meta and pri_meta.get("base") else None
    if meta_base and intake_base and slugify(meta_base) != slugify(intake_base):
        raise Bad(f"runs/{key}/{RUN_META} base ({meta_base}) differs from intake.md base ({intake_base})")

    found = mixed_bases(pri_dir) if pri_dir.is_dir() else []
    if len(found) > 1:
        raise Bad(f"mixed bases in runs/{key} ({', '.join(found)}); split the folder before claim")

    recorded_base = meta_base or intake_base
    if recorded_base is None or slugify(recorded_base) == base_slug:
        stored_base = pri_meta["base"] if (pri_meta and pri_meta.get("base")) else (recorded_base or base_clean)
        validate_run_id(key)
        return key, key, stored_base, None

    validate_run_id(suf)
    return suf, key, base_clean, None


# ---------- commands ----------

def claim(ws, key, data=None, pid=None, checkout=None, note=None, takeover=False, base=None, label=None):
    check_names(ws, key)
    data, shared, top = places(data)
    pid = pid or owner_pid()
    st = proc_stat(pid)
    if st is None:
        raise Bad(f"process {pid} does not exist")
    cleared = None
    with ops_lock(shared):
        run_id, jira, stored_base, label_slug = resolve_slot(data, ws, key, base, label)
        path = key_file(data, ws, run_id)
        old = read(path) if path.exists() else None
        if path.exists():
            state, reason = key_state(old)
            if state == "live" and not takeover:
                raise Held(f"{ws} {run_id} is already running (pid {old.get('pid')}, "
                           f"started {old.get('startedAt')}, checkout {old.get('checkout')})", summary(old))
            if state == "live":
                reason = "taken over: the user said that run is not running"
            cleared = {**summary(old or {}), "reason": reason}
            drop_shared(shared, ws, run_id)
        if base is not None:
            meta = {"jira": jira, "base": stored_base, "runId": run_id}
            if label_slug is not None:
                meta["label"] = label_slug
            write(run_dir(data, ws, run_id) / RUN_META, meta)
        record = {"version": VERSION, "ws": ws, "key": run_id, "pid": pid, "pidStart": st[2],
                  "token": secrets.token_hex(8), "host": socket.gethostname(),
                  "checkout": str(checkout or top), "dataRoot": str(data),
                  "startedAt": now(), "ports": {}, "targets": []}
        if base is not None:
            record["jira"] = jira
            record["base"] = stored_base
            if label_slug is not None:
                record["label"] = label_slug
        if note:
            record["note"] = note
        if cleared and old:
            record["continues"] = old.get("startedAt")
        touch(path, record)
    result = {"claimed": True, "claimId": record["token"], "token": record["token"],
              "runId": run_id, "claim": summary(record), "file": str(path)}
    if base is not None:
        result["jira"] = jira
        result["base"] = stored_base
        if label_slug is not None:
            result["label"] = label_slug
    if cleared:
        result["staleCleared"] = cleared
    return result


def port_free(port):
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return False
        except OSError:
            pass
    for family, host in ((socket.AF_INET, "0.0.0.0"), (socket.AF_INET6, "::")):
        with socket.socket(family, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
            except OSError as e:
                if family == socket.AF_INET6 and e.errno in (97, 99):  # no IPv6 here
                    continue
                return False
    return True


def port(ws, key, kind, data=None, lo_hi=None):
    check_names(ws, key)
    if kind not in RANGES:
        raise Bad(f"--kind is one of {', '.join(RANGES)}")
    lo, hi = lo_hi or RANGES[kind]
    data, shared, _ = places(data)
    path = key_file(data, ws, key)
    with ops_lock(shared):
        record = live_owner(data, ws, key)
        mine = record.get("ports", {}).get(kind)
        if mine:
            held = read(Path(shared) / "ports" / f"{mine}.lock")
            if held and held.get("ws") == ws and held.get("key") == key and shared_state(held)[0] == "live":
                touch(path, record)
                return {"port": mine, "kind": kind, "already": True}
        for p in range(lo, hi + 1):
            f = Path(shared) / "ports" / f"{p}.lock"
            held = read(f) if f.exists() else None
            if held and shared_state(held)[0] == "live":
                continue
            if not port_free(p):
                continue
            write(f, {"version": VERSION, "port": p, "kind": kind, "ws": ws, "key": key,
                      "keyClaim": str(path), "pid": record["pid"], "pidStart": record["pidStart"],
                      "claimedAt": now()})
            record.setdefault("ports", {})[kind] = p
            touch(path, record)
            return {"port": p, "kind": kind, "already": False}
    raise Bad(f"no free {kind} port between {lo} and {hi}")


def norm(path):
    return os.path.realpath(os.path.expanduser(str(path)))


def target(ws, key, work_tree, root, branch, data=None):
    check_names(ws, key)
    data, shared, _ = places(data)
    path = key_file(data, ws, key)
    wt, rt = norm(work_tree), norm(root)
    f = Path(shared) / "targets" / (hashlib.sha256(wt.encode()).hexdigest()[:20] + ".lock")
    with ops_lock(shared):
        record = live_owner(data, ws, key)
        folder = Path(shared) / "targets"
        for other in sorted(folder.glob("*.lock")) if folder.is_dir() else []:
            held = read(other)
            if not held or (held.get("ws"), held.get("key")) == (ws, key):
                continue
            if shared_state(held)[0] != "live":
                continue
            if held.get("path") == wt:
                raise Held(f"{wt} is being edited by {held['ws']} {held['key']}", public(held))
            if held.get("root") == rt and branch and held.get("branch") == branch:
                raise Held(f"branch {branch} of {rt} is in use by {held['ws']} {held['key']}", public(held))
        write(f, {"version": VERSION, "path": wt, "root": rt, "branch": branch, "ws": ws, "key": key,
                  "keyClaim": str(path), "pid": record["pid"], "pidStart": record["pidStart"],
                  "claimedAt": now()})
        targets = [t for t in record.get("targets", []) if t.get("path") != wt]
        record["targets"] = targets + [{"path": wt, "root": rt, "branch": branch}]
        touch(path, record)
    return {"target": wt, "root": rt, "branch": branch}


def drop_shared(shared, ws, key):
    dropped = []
    for sub in ("ports", "targets"):
        folder = Path(shared) / sub
        for f in sorted(folder.glob("*.lock")) if folder.is_dir() else []:
            held = read(f)
            if held and (held.get("ws"), held.get("key")) == (ws, key):
                f.unlink(missing_ok=True)
                dropped.append(f.name)
    return dropped


def commit_run(ws, key, data=None, stage=None, message=None):
    check_names(ws, key)
    data, _, _ = places(data)
    folder = run_dir(data, ws, key)
    record = read(folder / CLAIM)
    if record and key_state(record)[0] == "live":
        touch(folder / CLAIM, record)
    if not folder.is_dir():
        return {"commit": None, "reason": f"no run folder {folder}"}
    rel = folder.relative_to(data)
    msg = message or f"{key} {stage or 'run'} ({ws})"
    try:
        sha = dr.commit(data, msg, [str(rel)])
    except dr.Stop as e:
        raise Bad(str(e))
    return {"commit": sha, "paths": [str(rel)], "message": msg}


def end_run(ws, key, data=None, claim_id=None, pid=None, force=False, no_commit=False):
    check_names(ws, key)
    data, shared, _ = places(data)
    path = key_file(data, ws, key)
    with ops_lock(shared):
        record = read(path) if path.exists() else None
        if path.exists() and not force and key_state(record)[0] == "live":
            me = pid or owner_pid()
            st = proc_stat(me)
            same_owner = record.get("pid") == me and st is not None and record.get("pidStart") == st[2]
            if not same_owner and (not claim_id or claim_id != record.get("token")):
                raise Held(f"{ws} {key} is held by a live run (pid {record.get('pid')}, started "
                           f"{record.get('startedAt')}); only that run ends it", summary(record))
        dropped = drop_shared(shared, ws, key)
        ended = path.exists()
        path.unlink(missing_ok=True)
    result = {"ended": ended, "released": ended, "dropped": dropped}
    if not no_commit:
        result.update(commit_run(ws, key, data, message=f"{key} end of run ({ws})"))
    return result


release = end_run


def list_claims(ws=None, data=None):
    data, shared, _ = places(data)
    runs = []
    pattern = f"workspaces/{ws or '*'}/runs/*/{CLAIM}"
    for f in sorted(Path(data).glob(pattern)):
        record = read(f) or {}
        state, reason = key_state(record)
        runs.append({**summary(record), "state": state, "reason": reason or None, "file": str(f)})
    shared_list = []
    for sub in ("ports", "targets"):
        folder = Path(shared) / sub
        for f in sorted(folder.glob("*.lock")) if folder.is_dir() else []:
            record = read(f) or {}
            if ws and record.get("ws") != ws:
                continue
            state, reason = shared_state(record)
            item = {k: record.get(k) for k in ("ws", "key", "kind", "port", "path", "branch") if record.get(k)}
            shared_list.append({"type": sub[:-1], **item, "state": state})
    live = [r for r in runs if r["state"] == "live"]
    return {"dataRoot": str(data), "running": len(live), "runs": runs, "shared": shared_list}


# ---------- command line ----------

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(s, key=True):
        s.add_argument("--ws", required=key, help="workspace folder name, e.g. ticket-execution")
        if key:
            s.add_argument("--key", required=True, help="the run key")
        s.add_argument("--data-root", help="use this data checkout for every claim (tests)")

    c = sub.add_parser("claim", help="claim a run key")
    common(c)
    c.add_argument("--base", help="base git branch for this run (optional)")
    c.add_argument("--label", help="approach label for parallel runs on the same base (requires --base)")
    c.add_argument("--pid", type=int, help="owner process (default: the agent session that runs this)")
    c.add_argument("--checkout", help="ai-system checkout the run uses (default: this one)")
    c.add_argument("--note", help="what started the run, e.g. 'start'")
    c.add_argument("--takeover", action="store_true", help="replace a claim that still looks live "
                   "(only when the user says that run is not running)")
    po = sub.add_parser("port", help="the run's port of one kind")
    common(po)
    po.add_argument("--kind", required=True, choices=sorted(RANGES))
    po.add_argument("--range", help="LO-HI instead of the default range (tests)")
    t = sub.add_parser("target", help="claim the target work tree and branch the run edits")
    common(t)
    t.add_argument("--path", required=True, help="the work tree the run edits (main root or worktree)")
    t.add_argument("--root", required=True, help="the repo's main checkout (its row's Root)")
    t.add_argument("--branch", required=True)
    cm = sub.add_parser("commit", help="commit only this run's folder")
    common(cm)
    cm.add_argument("--stage", help="the stage that just wrote its record, e.g. 04-implement")
    for name, extra in (("end", {"help": "end the run"}), ("release", {})):
        e = sub.add_parser(name, **extra)
        common(e)
        e.add_argument("--claim-id", "--token", dest="claim_id", help="the claimId `claim` returned "
                       "(--token is the deprecated name)")
        e.add_argument("--pid", type=int, help="the caller's owner process (tests)")
        e.add_argument("--force", action="store_true", help="end a claim held by another live process "
                       "(only when the user says that run is not running)")
        e.add_argument("--no-commit", action="store_true")
    ls = sub.add_parser("list", help="every claim, live or stale")
    common(ls, key=False)
    args = p.parse_args(argv)
    try:
        if args.cmd == "claim":
            res = claim(args.ws, args.key, args.data_root, args.pid, args.checkout, args.note, args.takeover,
                        args.base, args.label)
        elif args.cmd == "port":
            lo_hi = None
            if args.range:
                m = re.match(r"^(\d+)-(\d+)$", args.range)
                if not m:
                    raise Bad("--range is LO-HI")
                lo_hi = (int(m.group(1)), int(m.group(2)))
            res = port(args.ws, args.key, args.kind, args.data_root, lo_hi)
        elif args.cmd == "target":
            res = target(args.ws, args.key, args.path, args.root, args.branch, args.data_root)
        elif args.cmd == "commit":
            res = commit_run(args.ws, args.key, args.data_root, args.stage)
        elif args.cmd in ("end", "release"):
            res = end_run(args.ws, args.key, args.data_root, args.claim_id, args.pid, args.force, args.no_commit)
        else:
            res = list_claims(args.ws, args.data_root)
    except Held as e:
        print(json.dumps({"ok": False, "error": str(e), "heldBy": e.holder}, ensure_ascii=False))
        return 3
    except Bad as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, **res}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
