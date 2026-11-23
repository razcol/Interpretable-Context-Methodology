#!/usr/bin/env python3
"""Tests for run_claim.py. Each test builds a throwaway ai-system checkout and data root
(the Sandbox from test_data_root.py). Run owners, dev servers and listeners are fake
processes (sleep, a bare listening socket); no real dev server or browser is started.
Run: python3 test_run_claim.py"""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_claim as rc  # noqa: E402
from test_data_root import Sandbox  # noqa: E402

WS = "ticket-execution"


class ClaimSandbox(Sandbox):
    def setUp(self):
        super().setUp()
        self.run_helper(self.code, "init")
        self.procs = []
        self.base_port = 47100 + (os.getpid() % 50) * 20

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
                p.wait()
            if p.stdout:
                p.stdout.close()
        super().tearDown()

    def fake_owner(self):
        """A process standing in for an agent session that runs a workflow."""
        p = subprocess.Popen(["sleep", "120"])
        self.procs.append(p)
        return p

    def listener(self, port):
        """A process listening on a port, standing in for a dev server or Chrome."""
        code = ("import socket,sys,time;s=socket.socket();s.bind(('127.0.0.1',int(sys.argv[1])));"
                "s.listen();print('up',flush=True);time.sleep(120)")
        p = subprocess.Popen([sys.executable, "-c", code, str(port)], stdout=subprocess.PIPE, text=True)
        self.assertEqual(p.stdout.readline().strip(), "up")
        self.procs.append(p)
        return p

    def rc(self, *args, checkout=None, code=0):
        r = subprocess.run([sys.executable, str((checkout or self.code) / "_core/data-root/run_claim.py"), *args],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def claim(self, key, owner, ws=WS, code=0, *extra):
        return self.rc("claim", "--ws", ws, "--key", key, "--pid", str(owner.pid), *extra, code=code)

    def port(self, key, kind, ws=WS, code=0, span=10):
        lo = self.base_port + (0 if kind == "dev" else 10)
        return self.rc("port", "--ws", ws, "--key", key, "--kind", kind, "--range", f"{lo}-{lo + span - 1}",
                       code=code)

    def claim_file(self, key, ws=WS, data=None):
        return (data or self.data) / "workspaces" / ws / "runs" / key / "claim.lock"


class KeyClaimTests(ClaimSandbox):
    def test_claim_records_start_checkout_and_pid_and_is_never_committed(self):
        owner = self.fake_owner()
        res = self.claim("ABC-1", owner)
        record = json.loads(self.claim_file("ABC-1").read_text())
        self.assertEqual(record["pid"], owner.pid)
        self.assertEqual(record["checkout"], str(self.code))
        self.assertTrue(record["startedAt"])
        self.assertEqual(res["claimId"], record["token"])
        self.assertEqual(res["token"], res["claimId"])
        self.git(self.data, "check-ignore", "-q", "workspaces/ticket-execution/runs/ABC-1/claim.lock")
        self.assertEqual(self.git(self.data, "status", "--porcelain", "--untracked-files=all"), "")

    def test_second_start_on_a_running_key_stops_and_names_the_claim(self):
        first, second = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", first)
        res = self.claim("ABC-1", second, WS, 3)
        self.assertFalse(res["ok"])
        self.assertIn("ABC-1 is already running", res["error"])
        self.assertEqual(res["heldBy"]["pid"], first.pid)
        self.assertIn("startedAt", res["heldBy"])
        self.assertNotIn("token", res["heldBy"])
        # the same session cannot start the key twice either
        self.claim("ABC-1", first, WS, 3)
        self.assertEqual(json.loads(self.claim_file("ABC-1").read_text())["pid"], first.pid)

    def test_killed_run_is_stale_and_the_next_start_continues(self):
        dead, nxt = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", dead)
        self.port("ABC-1", "dev")
        dead.kill()
        dead.wait()
        listed = self.rc("list", "--ws", WS)
        self.assertEqual(listed["running"], 0)
        self.assertEqual(listed["runs"][0]["state"], "stale")
        self.assertIn(f"process {dead.pid} is gone", listed["runs"][0]["reason"])
        res = self.claim("ABC-1", nxt)
        self.assertEqual(res["staleCleared"]["pid"], dead.pid)
        self.assertIn("is gone", res["staleCleared"]["reason"])
        record = json.loads(self.claim_file("ABC-1").read_text())
        self.assertEqual(record["pid"], nxt.pid)
        self.assertTrue(record["continues"])
        self.assertEqual(list((self.data / "claims" / "ports").glob("*.lock")), [])

    def test_reused_pid_gone_checkout_and_old_claim_are_stale(self):
        owner = self.fake_owner()
        self.claim("ABC-1", owner)
        f = self.claim_file("ABC-1")
        good = json.loads(f.read_text())
        self.assertEqual(rc.key_state(good), ("live", ""))
        self.assertEqual(rc.key_state({**good, "pidStart": "1"})[0], "stale")
        self.assertIn("checkout", rc.key_state({**good, "checkout": str(self.tmp / "gone")})[1])
        self.assertIn("not touched", rc.key_state({**good, "touchedEpoch": time.time() - rc.STALE_AFTER - 5})[1])
        self.assertEqual(rc.key_state({**good, "pid": 0x3FFFFF})[0], "stale")

    def test_a_removed_maintenance_checkout_makes_its_claim_stale(self):
        owner, nxt = self.fake_owner(), self.fake_owner()
        wt = self.tmp / "gone-checkout"
        wt.mkdir()
        self.claim("ABC-1", owner, WS, 0, "--checkout", str(wt))
        wt.rmdir()
        res = self.claim("ABC-1", nxt)
        self.assertIn("is gone", res["staleCleared"]["reason"])

    def test_takeover_replaces_a_live_looking_claim(self):
        first, second = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", first)
        res = self.claim("ABC-1", second, WS, 0, "--takeover")
        self.assertIn("taken over", res["staleCleared"]["reason"])

    def test_bad_names_are_refused(self):
        owner = self.fake_owner()
        for key in ("../x", "a/b", "", "A..B"):
            self.rc("claim", "--ws", WS, "--key", key, "--pid", str(owner.pid), code=2)
        self.rc("claim", "--ws", "../x", "--key", "ABC-1", "--pid", str(owner.pid), code=2)
        self.assertFalse((self.data / "workspaces" / WS).exists())

    def test_owner_is_the_first_long_lived_ancestor(self):
        chain = {300: ("python3", 200, "9", "S"), 200: ("bash", 150, "8", "S"),
                 150: ("zsh", 100, "7", "S"), 100: ("claude", 1, "5", "S")}
        with mock.patch.object(rc, "proc_stat", side_effect=lambda pid: chain.get(pid)):
            self.assertEqual(rc.owner_pid(300), 100)
            self.assertEqual(rc.owner_pid(200), 100)


class PortTests(ClaimSandbox):
    def test_each_run_gets_its_own_ports_and_keeps_them(self):
        a, b = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", a)
        self.claim("XYZ-2", b)
        dev_a, dev_b = self.port("ABC-1", "dev")["port"], self.port("XYZ-2", "dev")["port"]
        cdp_a, cdp_b = self.port("ABC-1", "cdp")["port"], self.port("XYZ-2", "cdp")["port"]
        self.assertNotEqual(dev_a, dev_b)
        self.assertNotEqual(cdp_a, cdp_b)
        again = self.port("ABC-1", "dev")
        self.assertEqual((again["port"], again["already"]), (dev_a, True))
        record = json.loads(self.claim_file("ABC-1").read_text())
        self.assertEqual(record["ports"], {"dev": dev_a, "cdp": cdp_a})

    def test_a_port_something_listens_on_is_skipped(self):
        owner = self.fake_owner()
        self.listener(self.base_port)
        self.claim("ABC-1", owner)
        self.assertEqual(self.port("ABC-1", "dev")["port"], self.base_port + 1)

    def test_a_dead_runs_port_is_given_out_again(self):
        dead, nxt = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", dead)
        first = self.port("ABC-1", "dev")["port"]
        dead.kill()
        dead.wait()
        self.claim("XYZ-2", nxt)
        self.assertEqual(self.port("XYZ-2", "dev")["port"], first)

    def test_port_needs_a_live_key_claim_and_a_free_port(self):
        self.port("ABC-1", "dev", code=2)
        owner = self.fake_owner()
        self.claim("ABC-1", owner)
        self.listener(self.base_port)
        res = self.port("ABC-1", "dev", span=1, code=2)
        self.assertIn("no free dev port", res["error"])

    def test_parallel_port_requests_never_share_a_port(self):
        owners = [self.fake_owner() for _ in range(6)]
        for i, o in enumerate(owners):
            self.claim(f"K-{i}", o)
        results = {}

        def ask(i):
            results[i] = self.port(f"K-{i}", "dev", span=10)["port"]

        threads = [threading.Thread(target=ask, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(set(results.values())), 6, results)


class TargetTests(ClaimSandbox):
    def test_work_tree_and_branch_are_claimed_once(self):
        a, b = self.fake_owner(), self.fake_owner()
        root = self.tmp / "app-repo"
        self.claim("ABC-1", a)
        self.claim("ABC-2", b)
        self.rc("target", "--ws", WS, "--key", "ABC-1", "--path", str(root), "--root", str(root),
                "--branch", "ABC-1-x")
        res = self.rc("target", "--ws", WS, "--key", "ABC-2", "--path", str(root), "--root", str(root),
                      "--branch", "ABC-2-y", code=3)
        self.assertIn("ABC-1", res["error"])
        self.assertEqual(res["heldBy"]["key"], "ABC-1")
        # the row says worktree: the second run gets its own work tree in the same repo
        self.rc("target", "--ws", WS, "--key", "ABC-2", "--path", str(root / ".worktrees/ABC-2"),
                "--root", str(root), "--branch", "ABC-2-y")
        # but never the branch another run has
        res = self.rc("target", "--ws", "figma-section-fields", "--key", "1-2", "--path",
                      str(self.tmp / "elsewhere"), "--root", str(root), "--branch", "ABC-1-x", code=2)
        self.assertIn("no claim", res["error"])
        c = self.fake_owner()
        self.claim("1-2", c, "figma-section-fields")
        res = self.rc("target", "--ws", "figma-section-fields", "--key", "1-2", "--path",
                      str(self.tmp / "elsewhere"), "--root", str(root), "--branch", "ABC-1-x", code=3)
        self.assertIn("branch ABC-1-x", res["error"])

    def test_a_dead_runs_work_tree_is_free(self):
        dead, nxt = self.fake_owner(), self.fake_owner()
        root = self.tmp / "app-repo"
        self.claim("ABC-1", dead)
        self.rc("target", "--ws", WS, "--key", "ABC-1", "--path", str(root), "--root", str(root), "--branch", "b1")
        dead.kill()
        dead.wait()
        self.claim("ABC-2", nxt)
        self.rc("target", "--ws", WS, "--key", "ABC-2", "--path", str(root), "--root", str(root), "--branch", "b2")


class CommitAndEndTests(ClaimSandbox):
    def committed(self, rev="HEAD"):
        return set(self.git(self.data, "show", "--name-only", "--format=", rev).splitlines())

    def test_commit_stages_only_this_runs_folder(self):
        a, b = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", a)
        self.claim("XYZ-2", b)
        self.write(self.data / "workspaces" / WS / "runs/ABC-1/01-intake/intake.md", "version: 1\n")
        self.write(self.data / "workspaces" / WS / "runs/XYZ-2/01-intake/intake.md", "version: 1\n")
        self.write(self.data / "log/browser-cdp/LOG.md", "a line\n")
        res = self.rc("commit", "--ws", WS, "--key", "ABC-1", "--stage", "01-intake")
        self.assertEqual(res["message"], "ABC-1 01-intake (ticket-execution)")
        self.assertEqual(self.committed(), {"workspaces/ticket-execution/runs/ABC-1/01-intake/intake.md"})
        left = self.git(self.data, "status", "--porcelain", "--untracked-files=all")
        self.assertIn("runs/XYZ-2/01-intake/intake.md", left)
        self.assertIn("log/browser-cdp/LOG.md", left)
        self.assertNotIn("claim.lock", left)
        self.assertIsNone(self.rc("commit", "--ws", WS, "--key", "ABC-1")["commit"])

    def test_claim_commit_then_end_needs_the_claim_id_and_drops_claims(self):
        owner, other = self.fake_owner(), self.fake_owner()
        claim_id = self.claim("ABC-1", owner)["claimId"]
        self.port("ABC-1", "dev")
        self.rc("target", "--ws", WS, "--key", "ABC-1", "--path", str(self.tmp / "r"), "--root",
                str(self.tmp / "r"), "--branch", "b")
        self.write(self.data / "workspaces" / WS / "runs/ABC-1/06-handoff/handoff.md", "version: 1\n")
        res = self.rc("commit", "--ws", WS, "--key", "ABC-1", "--stage", "06-handoff")
        self.assertEqual(res["message"], "ABC-1 06-handoff (ticket-execution)")
        self.assertEqual(self.committed(), {"workspaces/ticket-execution/runs/ABC-1/06-handoff/handoff.md"})
        self.assertTrue(self.claim_file("ABC-1").exists())
        res = self.rc("end", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), code=3)
        self.assertIn("only that run ends it", res["error"])
        self.rc("end", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), "--claim-id", "wrong", code=3)
        self.write(self.data / "workspaces" / WS / "runs/ABC-1/06-handoff/notes.md", "late\n")
        res = self.rc("end", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), "--claim-id", claim_id)
        self.assertTrue(res["ended"])
        self.assertTrue(res["released"])
        self.assertEqual(len(res["dropped"]), 2)
        self.assertEqual(res["message"], "ABC-1 end of run (ticket-execution)")
        self.assertEqual(self.committed(), {"workspaces/ticket-execution/runs/ABC-1/06-handoff/notes.md"})
        self.assertFalse(self.claim_file("ABC-1").exists())
        self.assertEqual(self.rc("list")["runs"], [])

    def test_the_owner_session_ends_its_claim_without_the_claim_id(self):
        owner = self.fake_owner()
        self.claim("ABC-1", owner)
        self.assertTrue(self.rc("end", "--ws", WS, "--key", "ABC-1", "--pid", str(owner.pid), "--no-commit")["ended"])
        self.assertFalse(self.claim_file("ABC-1").exists())

    def test_deprecated_release_and_token_still_work(self):
        owner, other = self.fake_owner(), self.fake_owner()
        token = self.claim("ABC-1", owner)["token"]
        res = self.rc("release", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), code=3)
        self.assertIn("only that run ends it", res["error"])
        self.rc("release", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), "--token", "wrong", code=3)
        res = self.rc("release", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), "--token", token, "--no-commit")
        self.assertTrue(res["released"])
        self.assertTrue(res["ended"])
        self.assertFalse(self.claim_file("ABC-1").exists())
        # the new command takes the old flag name too
        token = self.claim("ABC-2", owner)["token"]
        self.assertTrue(self.rc("end", "--ws", WS, "--key", "ABC-2", "--pid", str(other.pid), "--token", token,
                                "--no-commit")["ended"])
        self.assertIs(rc.release, rc.end_run)

    def test_end_of_a_stale_claim_needs_no_claim_id(self):
        dead = self.fake_owner()
        self.claim("ABC-1", dead)
        dead.kill()
        dead.wait()
        self.assertTrue(self.rc("end", "--ws", WS, "--key", "ABC-1", "--no-commit")["ended"])

    def test_approve_reclaims_commits_07_and_ends(self):
        start, approve = self.fake_owner(), self.fake_owner()
        run = self.data / "workspaces" / WS / "runs/ABC-1"
        first = self.claim("ABC-1", start, WS, 0, "--note", "start")["claimId"]
        self.write(run / "06-handoff/handoff.md", "version: 1\n")
        self.rc("commit", "--ws", WS, "--key", "ABC-1", "--stage", "06-handoff")
        self.rc("end", "--ws", WS, "--key", "ABC-1", "--claim-id", first)
        # approve <KEY>: a fresh claim with its own id, then 07, then end
        res = self.claim("ABC-1", approve, WS, 0, "--note", "approve")
        self.assertNotIn("staleCleared", res)
        second = res["claimId"]
        self.assertNotEqual(second, first)
        record = json.loads(self.claim_file("ABC-1").read_text())
        self.assertEqual((record["note"], record["pid"]), ("approve", approve.pid))
        self.write(run / "07-release/release-record.md", "version: 1\n")
        res = self.rc("commit", "--ws", WS, "--key", "ABC-1", "--stage", "07-release")
        self.assertEqual(res["message"], "ABC-1 07-release (ticket-execution)")
        self.assertEqual(self.committed(), {"workspaces/ticket-execution/runs/ABC-1/07-release/release-record.md"})
        self.assertTrue(self.claim_file("ABC-1").exists())
        self.rc("end", "--ws", WS, "--key", "ABC-1", "--claim-id", first, "--pid", str(start.pid), code=3)
        res = self.rc("end", "--ws", WS, "--key", "ABC-1", "--claim-id", second, "--pid", str(start.pid))
        self.assertTrue(res["ended"])
        self.assertIsNone(res["commit"])
        self.assertEqual(self.rc("list")["runs"], [])

    def test_approve_after_a_claim_never_ended_reports_it(self):
        held, approve = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", held, WS, 0, "--note", "start")
        # the session that held it is still live: approve stops and names it
        res = self.claim("ABC-1", approve, WS, 3, "--note", "approve")
        self.assertIn("ABC-1 is already running", res["error"])
        self.assertEqual(res["heldBy"]["pid"], held.pid)
        held.kill()
        held.wait()
        res = self.claim("ABC-1", approve, WS, 0, "--note", "approve")
        self.assertEqual(res["staleCleared"]["pid"], held.pid)
        self.assertEqual(json.loads(self.claim_file("ABC-1").read_text())["note"], "approve")


RUN = r'''
import json, subprocess, sys, time
from pathlib import Path
rc, data, ws, key, owner, root, lo, expect = sys.argv[1:9]
def call(*a):
    r = subprocess.run([sys.executable, rc, *a], capture_output=True, text=True)
    out = json.loads(r.stdout)
    if r.returncode:
        raise SystemExit(f"{a[0]} exit {r.returncode}: {out}")
    return out
claim_id = call("claim", "--ws", ws, "--key", key, "--pid", owner)["claimId"]
deadline = time.time() + 30
seen = call("list")["running"]
while seen < int(expect) and time.time() < deadline:  # wait until every run holds its claim
    time.sleep(0.05)
    seen = call("list")["running"]
call("target", "--ws", ws, "--key", key, "--path", root, "--root", root, "--branch", key + "-work")
dev = call("port", "--ws", ws, "--key", key, "--kind", "dev", "--range", f"{lo}-{int(lo) + 9}")["port"]
cdp = call("port", "--ws", ws, "--key", key, "--kind", "cdp", "--range", f"{int(lo) + 10}-{int(lo) + 19}")["port"]
run = Path(data, "workspaces", ws, "runs", key)
for stage in ("01-intake", "04-implement", "05-verify", "06-handoff"):
    folder = run / stage
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "record.md").write_text(f"version: 1\n{key} {stage} http://localhost:{dev}/ cdp {cdp}\n")
    if stage == "05-verify":
        (folder / "shots").mkdir(exist_ok=True)
        (folder / "shots" / "row1.png").write_bytes(b"png-" + key.encode())
    time.sleep(0.05)
    call("commit", "--ws", ws, "--key", key, "--stage", stage)
call("end", "--ws", ws, "--key", key, "--claim-id", claim_id, "--pid", owner)
print(json.dumps({"key": key, "dev": dev, "cdp": cdp, "runningSeen": seen}))
'''


class TwoRunsAtOnceTests(ClaimSandbox):
    def simulate(self, runs):
        script = self.tmp / "fake_run.py"
        script.write_text(RUN)
        procs = []
        for ws, key, root in runs:
            owner = self.fake_owner()
            procs.append(subprocess.Popen(
                [sys.executable, str(script), str(self.code / "_core/data-root/run_claim.py"), str(self.data),
                 ws, key, str(owner.pid), str(root), str(self.base_port), str(len(runs))],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env))
        results = []
        for p in procs:
            out, err = p.communicate(timeout=120)
            self.assertEqual(p.returncode, 0, err)
            results.append(json.loads(out))
        return results

    def check(self, results, keys):
        self.assertEqual(len({r["dev"] for r in results}), len(keys))
        self.assertEqual(len({r["cdp"] for r in results}), len(keys))
        log = self.git(self.data, "log", "--format=%s")
        for key in keys:
            for stage in ("01-intake", "04-implement", "05-verify", "06-handoff"):
                self.assertIn(f"{key} {stage}", log)
            files = self.git(self.data, "ls-files", f"workspaces/*/runs/{key}/*")
            self.assertIn("05-verify/shots/row1.png", files)
            self.assertNotIn("claim.lock", files)
        for line in self.git(self.data, "log", "--format=%H").splitlines()[:-1]:
            touched = {p.split("/runs/")[1].split("/")[0] for p in
                       self.git(self.data, "show", "--name-only", "--format=", line).splitlines() if "/runs/" in p}
            self.assertLessEqual(len(touched), 1, f"a commit mixed runs: {touched}")
        self.assertEqual(self.git(self.data, "status", "--porcelain", "--untracked-files=all"), "")
        self.assertEqual(self.rc("list")["runs"], [])
        self.assertEqual(list(self.tmp.rglob(".run-lock")), [])
        self.assertEqual([r["runningSeen"] for r in results], [len(keys)] * len(keys))

    def test_two_keys_in_different_repos(self):
        results = self.simulate([(WS, "ABC-1", self.tmp / "repo-a"), (WS, "XYZ-2", self.tmp / "repo-b")])
        self.check(results, ["ABC-1", "XYZ-2"])

    def test_two_keys_in_one_repo_on_worktrees_and_a_figma_run(self):
        root = self.tmp / "repo"
        results = self.simulate([(WS, "OND-1", root / ".worktrees/OND-1"), (WS, "OND-2", root / ".worktrees/OND-2"),
                                 ("figma-section-fields", "2556-14120", self.tmp / "repo-c")])
        self.check(results, ["OND-1", "OND-2", "2556-14120"])


class MaintenanceTests(ClaimSandbox):
    def test_worktree_runs_claim_keys_in_their_data_worktree_and_ports_machine_wide(self):
        self.write(self.code / "README.md", "second\n")
        self.git(self.code, "add", "README.md")
        self.git(self.code, "commit", "-q", "-m", "second")
        first = self.git(self.code, "rev-list", "--max-parents=0", "HEAD")
        wt = self.tmp / "wt" / "PER-1-x"
        self.run_helper(self.code, "add", "PER-1-x", "--code-path", str(wt), "--from", first)
        self.assertEqual(self.git(wt, "rev-parse", "HEAD"), first)
        data_wt = self.data / ".worktrees" / "PER-1-x"
        a, b = self.fake_owner(), self.fake_owner()
        self.rc("claim", "--ws", WS, "--key", "ABC-1", "--pid", str(a.pid), checkout=wt)
        self.rc("claim", "--ws", WS, "--key", "ABC-1", "--pid", str(b.pid))  # main data: its own key space
        self.assertTrue(self.claim_file("ABC-1", data=data_wt).exists())
        self.assertTrue(self.claim_file("ABC-1").exists())
        lo = self.base_port
        p1 = self.rc("port", "--ws", WS, "--key", "ABC-1", "--kind", "dev", "--range", f"{lo}-{lo + 5}",
                     checkout=wt)["port"]
        p2 = self.rc("port", "--ws", WS, "--key", "ABC-1", "--kind", "dev", "--range", f"{lo}-{lo + 5}")["port"]
        self.assertNotEqual(p1, p2)
        self.assertEqual(len(list((self.data / "claims" / "ports").glob("*.lock"))), 2)
        self.assertFalse((data_wt / "claims").exists())
        self.assertEqual(self.git(self.data, "status", "--porcelain", "--untracked-files=all"), "")


class MultiBaseAndLabelTests(ClaimSandbox):
    def run_meta(self, run_id, ws=WS, data=None):
        return (data or self.data) / "workspaces" / ws / "runs" / run_id / "run.json"

    def test_two_unlabeled_bases_live_with_own_folders_ports_and_targets(self):
        a, b = self.fake_owner(), self.fake_owner()
        root = self.tmp / "repo"
        r1 = self.claim("ABC-1", a, WS, 0, "--base", "master")
        r2 = self.claim("ABC-1", b, WS, 0, "--base", "dev")
        self.assertEqual((r1["runId"], r1["jira"], r1["base"]), ("ABC-1", "ABC-1", "master"))
        self.assertNotIn("label", r1)
        self.assertEqual((r2["runId"], r2["jira"], r2["base"]), ("ABC-1--dev", "ABC-1", "dev"))
        self.assertNotIn("label", r2)
        self.assertEqual(json.loads(self.run_meta("ABC-1").read_text()),
                         {"jira": "ABC-1", "base": "master", "runId": "ABC-1"})
        self.assertEqual(json.loads(self.run_meta("ABC-1--dev").read_text()),
                         {"jira": "ABC-1", "base": "dev", "runId": "ABC-1--dev"})
        p1, p2 = self.port("ABC-1", "dev")["port"], self.port("ABC-1--dev", "dev")["port"]
        self.assertNotEqual(p1, p2)
        self.rc("target", "--ws", WS, "--key", "ABC-1", "--path", str(root / ".worktrees/ABC-1"),
                "--root", str(root), "--branch", "ABC-1-work")
        self.rc("target", "--ws", WS, "--key", "ABC-1--dev", "--path", str(root / ".worktrees/ABC-1--dev"),
                "--root", str(root), "--branch", "ABC-1-work--dev")
        listed = self.rc("list", "--ws", WS)
        self.assertEqual(listed["running"], 2)
        by_key = {r["key"]: r for r in listed["runs"]}
        self.assertEqual(by_key["ABC-1"]["base"], "master")
        self.assertEqual(by_key["ABC-1--dev"]["base"], "dev")

    def test_origin_prefix_and_case_reuse_same_unlabeled_slot(self):
        a, b = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", a, WS, 0, "--base", "master")
        r = self.claim("ABC-1", b, WS, 0, "--base", "origin/dev")
        self.assertEqual((r["runId"], r["base"]), ("ABC-1--dev", "dev"))
        self.rc("end", "--ws", WS, "--key", "ABC-1--dev", "--claim-id", r["claimId"])
        r2 = self.claim("ABC-1", b, WS, 0, "--base", "Dev")
        self.assertEqual((r2["runId"], r2["base"]), ("ABC-1--dev", "dev"))
        self.assertEqual(json.loads(self.run_meta("ABC-1--dev").read_text())["base"], "dev")

    def test_two_labeled_runs_beside_unlabeled_same_base(self):
        o0, o1, o2, o3 = [self.fake_owner() for _ in range(4)]
        root = self.tmp / "repo"
        r0 = self.claim("ABC-1", o0, WS, 0, "--base", "dev")
        r1 = self.claim("ABC-1", o1, WS, 0, "--base", "dev", "--label", "shared-checkbox")
        r2 = self.claim("ABC-1", o2, WS, 0, "--base", "dev", "--label", "article-meta")
        self.assertEqual(r0["runId"], "ABC-1")
        self.assertEqual((r1["runId"], r1["label"]), ("ABC-1--dev--shared-checkbox", "shared-checkbox"))
        self.assertEqual((r2["runId"], r2["label"]), ("ABC-1--dev--article-meta", "article-meta"))
        ids = [r0["runId"], r1["runId"], r2["runId"]]
        devs = {self.port(rid, "dev")["port"] for rid in ids}
        cdps = {self.port(rid, "cdp")["port"] for rid in ids}
        self.assertEqual((len(devs), len(cdps)), (3, 3))
        for i, rid in enumerate(ids):
            self.rc("target", "--ws", WS, "--key", rid, "--path", str(root / f".worktrees/{rid}"),
                    "--root", str(root), "--branch", f"branch-{i}")
        # second target on the same branch exits 3
        dup_branch = self.rc("target", "--ws", WS, "--key", r2["runId"],
                             "--path", str(root / ".worktrees/other"), "--root", str(root),
                             "--branch", "branch-1", code=3)
        self.assertIn("branch-1", dup_branch["error"])
        # second live claim of the same base and label exits 3 and names that run id; other label stays
        dup = self.claim("ABC-1", o3, WS, 3, "--base", "Dev", "--label", "shared-checkbox")
        self.assertIn("ABC-1--dev--shared-checkbox", dup["error"])
        self.assertEqual(dup["heldBy"]["label"], "shared-checkbox")
        self.assertEqual(json.loads(self.run_meta(r1["runId"]).read_text())["base"], "dev")
        # end of one label drops only that id's port and target locks
        self.rc("end", "--ws", WS, "--key", r1["runId"], "--claim-id", r1["claimId"])
        listed = self.rc("list", "--ws", WS)
        self.assertEqual(listed["running"], 2)
        self.assertEqual({r["key"] for r in listed["runs"]}, {r0["runId"], r2["runId"]})
        self.assertTrue(all(s["key"] != r1["runId"] for s in listed["shared"]))
        self.assertEqual(len([s for s in listed["shared"] if s["type"] == "port"]), 4)
        self.assertEqual(len([s for s in listed["shared"] if s["type"] == "target"]), 2)

    def test_commit_stages_only_one_run_id_including_run_json(self):
        a, b = self.fake_owner(), self.fake_owner()
        r1 = self.claim("ABC-1", a, WS, 0, "--base", "dev", "--label", "try-a")["runId"]
        r2 = self.claim("ABC-1", b, WS, 0, "--base", "dev", "--label", "try-b")["runId"]
        self.write(self.data / "workspaces" / WS / "runs" / r1 / "01-intake/intake.md", "version: 1\n")
        self.write(self.data / "workspaces" / WS / "runs" / r2 / "01-intake/intake.md", "version: 1\n")
        self.rc("commit", "--ws", WS, "--key", r1, "--stage", "01-intake")
        committed = set(self.git(self.data, "show", "--name-only", "--format=", "HEAD").splitlines())
        self.assertEqual(committed, {
            f"workspaces/{WS}/runs/{r1}/run.json",
            f"workspaces/{WS}/runs/{r1}/01-intake/intake.md",
        })
        left = self.git(self.data, "status", "--porcelain", "--untracked-files=all")
        self.assertIn(f"runs/{r2}/run.json", left)
        self.assertNotIn("claim.lock", left)

    def test_labeled_claim_leaves_primary_untouched_even_when_mixed(self):
        pri = self.data / "workspaces" / WS / "runs" / "ABC-1"
        self.write(pri / "01-intake/intake.md", "version: 1\n- base: master\n")
        self.write(pri / "06-handoff/handoff.md", "version: 1\nDiff against origin/dev\n")
        owner = self.fake_owner()
        r = self.claim("ABC-1", owner, WS, 0, "--base", "dev", "--label", "shared-checkbox")
        self.assertEqual(r["runId"], "ABC-1--dev--shared-checkbox")
        self.assertFalse((pri / "run.json").exists())
        self.assertFalse((pri / "claim.lock").exists())

    def test_stale_primary_continued_and_unlabeled_primary_adopted(self):
        dead, nxt = self.fake_owner(), self.fake_owner()
        self.claim("ABC-1", dead, WS, 0, "--base", "master")
        dead.kill()
        dead.wait()
        r = self.claim("ABC-1", nxt, WS, 0, "--base", "master")
        self.assertEqual(r["runId"], "ABC-1")
        self.assertIn("staleCleared", r)
        # primary without run.json and healthy records adopts on matching base
        pri2 = self.data / "workspaces" / WS / "runs" / "XYZ-2"
        self.write(pri2 / "01-intake/intake.md", "version: 1\n- base: master\n")
        self.write(pri2 / "02-research/research.md", "version: 1\nmentions origin/dev in prose\n")
        self.write(pri2 / "04-implement/implement-record.md",
                   "version: 1\n- branch: hotfix/XYZ-2-x (created from origin/master abc123)\n")
        self.write(pri2 / "06-handoff/handoff.md", "version: 1\nDiff against origin/master\n")
        r2 = self.claim("XYZ-2", nxt, WS, 0, "--base", "master")
        self.assertEqual(r2["runId"], "XYZ-2")
        meta = json.loads(self.run_meta("XYZ-2").read_text())
        self.assertEqual(meta, {"jira": "XYZ-2", "base": "master", "runId": "XYZ-2"})
        self.assertNotIn("label", meta)

    def test_mixed_primary_blocks_every_unlabeled_claim(self):
        pri = self.data / "workspaces" / WS / "runs" / "ABC-1"
        self.write(pri / "01-intake/intake.md", "version: 1\n- base: master\n")
        self.write(pri / "06-handoff/handoff.md", "version: 1\nDiff against origin/dev\n")
        owner = self.fake_owner()
        for base in ("master", "dev"):
            res = self.claim("ABC-1", owner, WS, 2, "--base", base)
            self.assertIn("mixed bases in runs/ABC-1", res["error"])
            self.assertFalse((pri / "run.json").exists())
        # also catches backticked `Diff vs \`origin/dev\``
        self.write(pri / "06-handoff/handoff.md", "version: 1\nDiff vs `origin/dev`:\n")
        res = self.claim("ABC-1", owner, WS, 2, "--base", "master")
        self.assertIn("mixed bases in runs/ABC-1", res["error"])

    def test_mismatched_run_json_and_suffixed_without_run_json_exit_2(self):
        owner = self.fake_owner()
        pri = self.data / "workspaces" / WS / "runs" / "ABC-1"
        self.write(pri / "run.json", json.dumps({"jira": "ABC-1", "base": "master", "runId": "ABC-1"}) + "\n")
        self.write(pri / "01-intake/intake.md", "version: 1\n- base: dev\n")
        res = self.claim("ABC-1", owner, WS, 2, "--base", "master")
        self.assertIn("differs from intake.md", res["error"])
        suf = self.data / "workspaces" / WS / "runs" / "XYZ-2--dev"
        suf.mkdir(parents=True)
        res = self.claim("XYZ-2", owner, WS, 2, "--base", "dev")
        self.assertIn("run.json", res["error"])

    def test_concurrent_claims_on_empty_primary_and_parallel_labels(self):
        o1, o2 = self.fake_owner(), self.fake_owner()
        out = {}

        def go(name, base, label=None, key="ABC-1"):
            extra = ["--base", base] + (["--label", label] if label else [])
            out[name] = self.claim(key, o1 if name.endswith("1") else o2, WS, 0, *extra)["runId"]

        t1 = threading.Thread(target=go, args=("u1", "master"))
        t2 = threading.Thread(target=go, args=("u2", "dev"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertIn("ABC-1", (out["u1"], out["u2"]))
        self.assertEqual(len({out["u1"], out["u2"]}), 2)
        other = out["u2"] if out["u1"] == "ABC-1" else out["u1"]
        self.assertIn(other, ("ABC-1--dev", "ABC-1--master"))

        out2 = {}
        t3 = threading.Thread(target=lambda: out2.setdefault("a", self.claim("XYZ-9", o1, WS, 0, "--base", "dev", "--label", "try-a")["runId"]))
        t4 = threading.Thread(target=lambda: out2.setdefault("b", self.claim("XYZ-9", o2, WS, 0, "--base", "dev", "--label", "try-b")["runId"]))
        t3.start()
        t4.start()
        t3.join()
        t4.join()
        self.assertEqual(out2, {"a": "XYZ-9--dev--try-a", "b": "XYZ-9--dev--try-b"})
        self.assertFalse((self.data / "workspaces" / WS / "runs" / "XYZ-9").exists())

    def test_release_slash_base_validation_limits_and_reclaim_after_end(self):
        owner = self.fake_owner()
        r = self.claim("ABC-1", owner, WS, 0, "--base", "release/1.2", "--label", "try-a")
        self.assertEqual((r["runId"], r["base"], r["label"]), ("ABC-1--release-1-2--try-a", "release/1.2", "try-a"))
        self.assertEqual(json.loads(self.run_meta(r["runId"]).read_text()),
                         {"jira": "ABC-1", "base": "release/1.2", "label": "try-a", "runId": "ABC-1--release-1-2--try-a"})
        # profile > 41 chars exits 2
        self.claim("ABC-1", owner, WS, 2, "--base", "dev", "--label", "a" * 35)
        # --key already suffixed with --base exits 2
        self.claim("ABC-1--dev--try-a", owner, WS, 2, "--base", "dev", "--label", "try-a")
        # --label without --base exits 2
        self.claim("ABC-1", owner, WS, 2, "--label", "try-a")
        # after end, reclaim with --base --label OR directly with --key <runId> without --base
        self.rc("end", "--ws", WS, "--key", r["runId"], "--claim-id", r["claimId"])
        r2 = self.claim("ABC-1", owner, WS, 0, "--base", "release/1.2", "--label", "try-a")
        self.assertEqual(r2["runId"], "ABC-1--release-1-2--try-a")
        self.rc("end", "--ws", WS, "--key", r2["runId"], "--claim-id", r2["claimId"])
        r3 = self.claim("ABC-1--release-1-2--try-a", owner, WS, 0)
        self.assertEqual(r3["runId"], "ABC-1--release-1-2--try-a")
        self.assertNotIn("jira", r3)
        self.assertNotIn("base", r3)
        self.assertNotIn("label", r3)

    def test_claim_without_base_writes_no_run_json_or_extra_fields(self):
        owner = self.fake_owner()
        r = self.claim("ABC-1", owner)
        self.assertEqual(r["runId"], "ABC-1")
        for field in ("jira", "base", "label"):
            self.assertNotIn(field, r)
            self.assertNotIn(field, r["claim"])
        self.assertFalse(self.run_meta("ABC-1").exists())


class RepoTextTests(unittest.TestCase):
    def test_no_tracked_file_tells_a_run_to_write_a_run_lock(self):
        repo = HERE.parent.parent
        lock = "stages/" + ".run-lock"
        r = subprocess.run(["git", "-C", str(repo), "grep", "-n", "-F", lock], capture_output=True, text=True)
        hits = [h for h in r.stdout.splitlines() if not h.startswith("workspaces/ticket-execution/tools/test_tools.py")]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
