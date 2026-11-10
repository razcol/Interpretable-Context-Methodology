#!/usr/bin/env python3
"""Find, start or stop the Next dev server for one app root.

Usage:
  dev_server.py status --app-root <dir>
  dev_server.py up --app-root <dir> --state <file> [--port N] [--path /route] [--timeout 300] [--keep-schema]
  dev_server.py down --state <file>

status  lists listening ports. "matches" are servers whose working directory is the
        app root, "others" are servers from other folders.
up      reuses a matching server (and writes the state file for it), or installs packages when node_modules is missing,
        starts `npm run dev` on a free port and waits until --path answers below 500.
        A reused server is probed on --path the same way as a new one, and exit 7 applies to both.
        The state file records listenerPid (the process on the port) next to pid (the npm
        process group `down` stops).
        It restores prisma/schema.prisma when the file was clean before the start and
        `prisma db pull` rewrote it, unless --keep-schema is given. Files the start
        created (Next 16 writes AGENTS.md) are listed as devArtifacts.
down    stops a server only when the state file says `up` started it.

Prints one JSON object. Exit codes: 0 ok, 2 bad arguments, 5 install failed,
6 the server exited, 7 timed out waiting.
"""

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PORTS = range(3000, 3021)


def out(code=0, **data):
    print(json.dumps({"ok": code == 0, **data}, ensure_ascii=False))
    sys.exit(code)


def listeners():
    try:
        text = subprocess.run(["ss", "-ltnpH"], capture_output=True, text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    found = []
    for line in text.splitlines():
        cols = line.split()
        if len(cols) < 4:
            continue
        port = cols[3].rsplit(":", 1)[-1]
        for pid in re.findall(r"pid=(\d+)", line):
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
                cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            except OSError:
                continue
            found.append({"port": int(port), "pid": int(pid), "cwd": cwd, "cmd": cmd[:160]})
    return found


def split(app_root):
    root = os.path.realpath(app_root)
    matches, others = [], []
    for entry in listeners():
        cwd = os.path.realpath(entry["cwd"])
        if cwd == root or cwd.startswith(root + os.sep):
            matches.append(entry)
        elif re.search(r"\b(node|next|npm)\b", entry["cmd"]):
            others.append(entry)
    return matches, others


def listening_ports():
    try:
        text = subprocess.run(["ss", "-ltnH"], capture_output=True, text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()
    return {int(cols[3].rsplit(":", 1)[-1]) for cols in (l.split() for l in text.splitlines()) if len(cols) >= 4}


def port_free(port):
    if port in listening_ports():
        return False
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
        try:
            s.bind(("::", port))
        except OSError:
            return False
    return True


def http_status(port, path):
    if not re.match(r"^/(?!/)", path):
        raise ValueError("path must start with /")
    try:
        with urllib.request.urlopen(f"http://localhost:{port}{path}", timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code
    except (urllib.error.URLError, socket.timeout, ConnectionError):
        return None


def tail(log, lines=25):
    try:
        text = Path(log).read_text(errors="replace").splitlines()[-lines:]
    except OSError:
        return []
    return [re.sub(r"[A-Za-z0-9+/_=-]{32,}", "<redacted>", t) for t in text]


def porcelain(app_root):
    res = subprocess.run(["git", "-C", app_root, "status", "--porcelain", "--untracked-files=all", "--", "."],
                         capture_output=True, text=True)
    return set(res.stdout.splitlines())


def schema_dirty(app_root):
    schema = Path(app_root, "prisma", "schema.prisma")
    if not schema.exists():
        return None
    res = subprocess.run(["git", "-C", app_root, "status", "--porcelain", "--", "prisma/schema.prisma"],
                         capture_output=True, text=True)
    return bool(res.stdout.strip())


def install(app_root, log):
    cmd = ["npm", "ci"] if Path(app_root, "package-lock.json").exists() else ["npm", "install"]
    with open(log, "a") as fh:
        fh.write(f"\n$ {' '.join(cmd)}\n")
        fh.flush()
        res = subprocess.run(cmd, cwd=app_root, stdout=fh, stderr=subprocess.STDOUT, timeout=1800)
    return cmd, res.returncode


def listener_pid(app_root, port):
    return next((m["pid"] for m in split(app_root)[0] if m["port"] == port), None)


def wait_reused(port, path, timeout):
    deadline = time.time() + timeout
    while True:
        status = http_status(port, path)
        if status is not None and status < 500:
            return True, status
        if time.time() >= deadline:
            return False, status
        time.sleep(3)


def same_group(pid, leader):
    try:
        return os.getpgid(pid) == leader
    except (OSError, TypeError):
        return False


def reuse_record(state, match, app_root, log):
    """The state file for a reused server. A server this key's earlier `up` started keeps its record
    (the pid there is the process group `down` stops); any other server is recorded as not ours."""
    try:
        prior = json.loads(state.read_text())
    except (OSError, ValueError):
        prior = None
    if prior and prior.get("startedBy") == "ticket-execution" and prior.get("startedByUs", True) \
            and same_group(match["pid"], prior.get("pid")):
        return {**prior, "port": match["port"], "listenerPid": match["pid"], "startedByUs": True}
    return {"startedBy": "ticket-execution", "startedByUs": False, "pid": match["pid"], "listenerPid": match["pid"],
            "port": match["port"], "appRoot": app_root, "log": log, "reusedAt": time.strftime("%Y-%m-%dT%H:%M:%S")}


def cmd_status(args):
    matches, others = split(args.app_root)
    out(0, appRoot=os.path.realpath(args.app_root), matches=matches, others=others)


def cmd_up(args):
    app_root = os.path.realpath(args.app_root)
    if not Path(app_root, "package.json").exists():
        out(2, error=f"no package.json in {app_root}")
    if not re.match(r"^/(?!/)", args.path):
        out(2, error="--path must start with /")
    state = Path(args.state)
    state.parent.mkdir(parents=True, exist_ok=True)
    log = str(state.with_suffix(".log"))

    matches, others = split(app_root)
    if matches:
        match = sorted(matches, key=lambda m: m["port"])[0]
        port = match["port"]
        record = reuse_record(state, match, app_root, log)
        state.write_text(json.dumps(record, indent=1))
        ok, status = wait_reused(port, args.path, args.timeout)
        if not ok:
            out(7, error=f"reused server: no answer below 500 on {args.path} after {args.timeout}s", reused=True,
                port=port, pid=record["pid"], listenerPid=record["listenerPid"], httpStatus=status,
                state=str(state), log=record["log"])
        out(0, reused=True, port=port, pid=record["pid"], listenerPid=record["listenerPid"],
            url=f"http://localhost:{port}{args.path}", httpStatus=status, others=others,
            startedByUs=record["startedByUs"], state=str(state))

    installed = None
    if not Path(app_root, "node_modules").is_dir():
        cmd, code = install(app_root, log)
        installed = " ".join(cmd)
        if code != 0:
            out(5, error=f"{installed} failed", log=log, tail=tail(log))

    taken = listening_ports()
    if args.port:
        if not port_free(args.port):
            out(2, error=f"port {args.port} is in use", others=others)
        port = args.port
    else:
        port = next((p for p in PORTS if p not in taken and port_free(p)), None)
        if port is None:
            out(2, error="no free port between 3000 and 3020", others=others)

    schema_before = schema_dirty(app_root)
    tree_before = porcelain(app_root)
    with open(log, "a") as fh:
        fh.write(f"\n$ PORT={port} npm run dev\n")
        fh.flush()
        proc = subprocess.Popen(["npm", "run", "dev"], cwd=app_root, env={**os.environ, "PORT": str(port)},
                                stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True)
    record = {"startedBy": "ticket-execution", "startedByUs": True, "pid": proc.pid, "port": port, "appRoot": app_root,
              "log": log, "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S")}
    state.write_text(json.dumps(record, indent=1))

    deadline = time.time() + args.timeout
    status = None
    while time.time() < deadline:
        if proc.poll() is not None:
            state.unlink(missing_ok=True)
            out(6, error=f"npm run dev exited with {proc.returncode}", log=log, tail=tail(log))
        status = http_status(port, args.path)
        if status is not None and status < 500:
            break
        time.sleep(3)
    else:
        out(7, error=f"no answer below 500 on {args.path} after {args.timeout}s", port=port, pid=proc.pid,
            httpStatus=status, log=log, tail=tail(log), state=str(state))

    schema = "untouched"
    if schema_before is False and schema_dirty(app_root):
        if args.keep_schema:
            schema = "changed by prisma db pull, kept"
        else:
            subprocess.run(["git", "-C", app_root, "checkout", "--", "prisma/schema.prisma"], check=False)
            schema = "changed by prisma db pull, restored"
    elif schema_before:
        schema = "was already modified before the start, left as is"
    dev_artifacts = sorted(line[3:] for line in porcelain(app_root) - tree_before)
    record["devArtifacts"] = dev_artifacts
    record["listenerPid"] = listener_pid(app_root, port)
    state.write_text(json.dumps(record, indent=1))

    out(0, reused=False, port=port, pid=proc.pid, listenerPid=record["listenerPid"], url=f"http://localhost:{port}{args.path}", httpStatus=status,
        log=log, state=str(state), installed=installed, schema=schema, devArtifacts=dev_artifacts,
        others=others, startedByUs=True)


def cmd_down(args):
    state = Path(args.state)
    if not state.exists():
        out(0, stopped=False, reason="no state file, nothing this workspace started")
    record = json.loads(state.read_text())
    if record.get("startedBy") != "ticket-execution":
        out(2, error="state file was not written by dev_server.py up")
    if record.get("startedByUs") is False:
        state.unlink(missing_ok=True)
        out(0, stopped=False, reason="reused server, not started by this run; left running",
            port=record.get("port"), pid=record.get("pid"))
    try:
        os.killpg(record["pid"], signal.SIGTERM)
        stopped = True
    except ProcessLookupError:
        stopped = False
    state.unlink(missing_ok=True)
    out(0, stopped=stopped, port=record.get("port"), pid=record.get("pid"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("status")
    s.add_argument("--app-root", required=True)
    u = sub.add_parser("up")
    u.add_argument("--app-root", required=True)
    u.add_argument("--state", required=True, help="state file, for example <run>/dev-server.json")
    u.add_argument("--port", type=int)
    u.add_argument("--path", default="/")
    u.add_argument("--timeout", type=int, default=300)
    u.add_argument("--keep-schema", action="store_true")
    d = sub.add_parser("down")
    d.add_argument("--state", required=True)
    args = ap.parse_args()
    {"status": cmd_status, "up": cmd_up, "down": cmd_down}[args.command](args)


if __name__ == "__main__":
    main()
