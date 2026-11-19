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
        self.assertEqual(res["token"], record["token"])
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


class CommitAndReleaseTests(ClaimSandbox):
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

    def test_release_needs_the_token_then_drops_claims_and_commits(self):
        owner, other = self.fake_owner(), self.fake_owner()
        token = self.claim("ABC-1", owner)["token"]
        self.port("ABC-1", "dev")
        self.rc("target", "--ws", WS, "--key", "ABC-1", "--path", str(self.tmp / "r"), "--root",
                str(self.tmp / "r"), "--branch", "b")
        self.write(self.data / "workspaces" / WS / "runs/ABC-1/06-handoff/handoff.md", "version: 1\n")
        res = self.rc("release", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), code=3)
        self.assertIn("only that run releases it", res["error"])
        self.rc("release", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), "--token", "wrong", code=3)
        res = self.rc("release", "--ws", WS, "--key", "ABC-1", "--pid", str(other.pid), "--token", token)
        self.assertTrue(res["released"])
        self.assertEqual(len(res["dropped"]), 2)
        self.assertEqual(res["message"], "ABC-1 end of run (ticket-execution)")
        self.assertEqual(self.committed(), {"workspaces/ticket-execution/runs/ABC-1/06-handoff/handoff.md"})
        self.assertFalse(self.claim_file("ABC-1").exists())
        self.assertEqual(self.rc("list")["runs"], [])

    def test_release_of_a_stale_claim_needs_no_token(self):
        dead = self.fake_owner()
        self.claim("ABC-1", dead)
        dead.kill()
        dead.wait()
        self.assertTrue(self.rc("release", "--ws", WS, "--key", "ABC-1", "--no-commit")["released"])


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
token = call("claim", "--ws", ws, "--key", key, "--pid", owner)["token"]
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
call("release", "--ws", ws, "--key", key, "--token", token, "--pid", owner)
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


class RepoTextTests(unittest.TestCase):
    def test_no_tracked_file_tells_a_run_to_write_a_run_lock(self):
        repo = HERE.parent.parent
        lock = "stages/" + ".run-lock"
        r = subprocess.run(["git", "-C", str(repo), "grep", "-n", "-F", lock], capture_output=True, text=True)
        hits = [h for h in r.stdout.splitlines() if not h.startswith("workspaces/ticket-execution/tools/test_tools.py")]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
