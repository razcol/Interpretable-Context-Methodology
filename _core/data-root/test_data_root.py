#!/usr/bin/env python3
"""Tests for data_root.py. Each test builds a throwaway ai-system checkout and data root
in a temp folder, with its own HOME and git config. Run: python3 test_data_root.py"""
import fcntl
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data_root as dr  # noqa: E402


class Sandbox(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("[user]\n\tname = Test\n\temail = test@example.invalid\n"
                             "[init]\n\tdefaultBranch = main\n")
        self.env = {k: v for k, v in os.environ.items() if k != dr.ENV_VAR}
        self.env.update(HOME=str(self.home), GIT_CONFIG_GLOBAL=str(gitconfig),
                        GIT_CONFIG_NOSYSTEM="1")
        self._env = mock.patch.dict(os.environ, self.env, clear=True)
        self._env.start()
        self.code = self.tmp / "ai-system"
        shutil.copytree(HERE, self.code / "_core" / "data-root",
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.write(self.code / "workspaces/demo/targets/repos.example.md", "| repo | <path> |\n")
        self.write(self.code / "workspaces/demo/targets/logins/site.example.json", '{"user": "<name>"}\n')
        self.write(self.code / "workspaces/demo/targets/notes.md", "not an example\n")
        self.write(self.code / ".gitignore", "/.data-root\n__pycache__/\n")
        self.git(self.code, "init", "-q", "-b", "my-changes")
        self.git(self.code, "add", ".")
        self.git(self.code, "commit", "-q", "-m", "base")
        self.data = self.tmp / "data"
        self.write(self.code / ".data-root", "# test data root\n" + str(self.data) + "\n")

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                              check=True, env=self.env).stdout.strip()

    def run_helper(self, checkout, *args, ok=True):
        r = subprocess.run([sys.executable, str(checkout / "_core/data-root/data_root.py"), *args],
                           capture_output=True, text=True, env=self.env, stdin=subprocess.DEVNULL)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        else:
            self.assertNotEqual(r.returncode, 0, r.stdout)
        return r

    def head(self, repo):
        return self.git(repo, "rev-parse", "HEAD")

    def add(self, branch):
        wt = self.tmp / "wt" / branch
        self.run_helper(self.code, "add", branch, "--code-path", str(wt))
        return wt, self.data / ".worktrees" / branch


class ResolutionTests(Sandbox):
    def test_order_pointer_then_env_then_default(self):
        self.assertEqual(dr.data_root(self.code), self.data)
        (self.code / ".data-root").unlink()
        self.assertEqual(dr.data_root(self.code), self.home / ".config/ai-system")
        os.environ[dr.ENV_VAR] = str(self.tmp / "from-env")
        self.assertEqual(dr.data_root(self.code), self.tmp / "from-env")
        self.write(self.code / ".data-root", "~/elsewhere\n")
        self.assertEqual(dr.data_root(self.code), self.home / "elsewhere")

    def test_relative_pointer_is_refused(self):
        self.write(self.code / ".data-root", "relative/path\n")
        with self.assertRaises(dr.Stop):
            dr.data_root(self.code)

    def test_resolve_main_and_paired_worktree(self):
        self.run_helper(self.code, "resolve", ok=False)  # no data root yet
        self.run_helper(self.code, "init")
        self.assertEqual(self.run_helper(self.code, "resolve").stdout.strip(), str(self.data))
        wt, data_wt = self.add("maint-x")
        self.assertEqual(self.run_helper(wt, "resolve").stdout.strip(), str(data_wt))
        # a worktree made without add has no data pair: resolve stops instead of using main data
        self.git(self.code, "worktree", "add", "-q", "-b", "loose", str(self.tmp / "loose"))
        r = self.run_helper(self.tmp / "loose", "resolve", ok=False)
        self.assertIn("no data worktree", r.stderr)

    def test_example_target_mapping(self):
        t = dr.example_target
        self.assertEqual(str(t("workspaces/w/targets/repos.example.md")), "workspaces/w/repos.md")
        self.assertEqual(str(t("workspaces/w/targets/logins/a.example.json")), "workspaces/w/logins/a.json")
        self.assertIsNone(t("workspaces/w/targets/repos.md"))
        self.assertIsNone(t("_core/x/targets/a.example.md"))


class InitTests(Sandbox):
    def test_init_seeds_from_examples_and_second_run_changes_nothing(self):
        self.run_helper(self.code, "init")
        d = self.data
        self.assertEqual((d / "LAYOUT").read_text().splitlines()[0], "version: 1")
        for f in (".gitignore", ".gitattributes", "README.md", "log/briefs/.gitkeep",
                  "archive/.gitkeep", "workspaces/.gitkeep"):
            self.assertTrue((d / f).is_file(), f)
        self.assertEqual((d / "workspaces/demo/repos.md").read_text(), "| repo | <path> |\n")
        self.assertTrue((d / "workspaces/demo/logins/site.json").is_file())
        self.assertFalse((d / "workspaces/demo/notes.md").exists())
        self.assertEqual(self.git(d, "status", "--porcelain"), "")
        self.assertEqual(self.git(d, "rev-list", "--count", "HEAD"), "1")
        before = (self.head(d), self.git(d, "ls-files", "-s"))
        r = self.run_helper(self.code, "init")
        self.assertIn("nothing changed", r.stdout)
        self.assertEqual((self.head(d), self.git(d, "ls-files", "-s")), before)
        self.assertEqual(self.git(d, "status", "--porcelain"), "")

    def test_init_never_overwrites_user_edits(self):
        self.run_helper(self.code, "init")
        self.write(self.data / "workspaces/demo/repos.md", "| repo | /real/path |\n")
        self.run_helper(self.code, "init")
        self.assertEqual((self.data / "workspaces/demo/repos.md").read_text(), "| repo | /real/path |\n")

    def test_init_refuses_a_folder_with_files_that_is_not_a_repo(self):
        self.write(self.data / "keep.txt", "user data\n")
        r = self.run_helper(self.code, "init", ok=False)
        self.assertIn("not touched", r.stderr)
        self.assertFalse((self.data / ".git").exists())
        self.assertEqual(sorted(p.name for p in self.data.iterdir()), ["keep.txt"])

    def test_init_stops_on_unknown_layout_version(self):
        self.run_helper(self.code, "init")
        self.write(self.data / "LAYOUT", "version: 2\n")
        self.run_helper(self.code, "init", ok=False)


class IgnoreAndCommitTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.run_helper(self.code, "init")

    def test_env_lock_and_worktree_patterns_are_ignored(self):
        paths = [".env", "jira.env", "workspaces/ticket-execution/test-logins.env", ".env.local",
                 "key.pem", ".run-lock", "workspaces/demo/runs/K-1/claim.lock",
                 ".worktrees/some-branch", "log/x/__pycache__/a.pyc"]
        r = subprocess.run(["git", "-C", str(self.data), "check-ignore", *paths],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.stdout.split(), paths)

    def test_commit_never_stages_secrets(self):
        self.write(self.data / "workspaces/demo/test-logins.env", "SECRET=1\n")
        self.write(self.data / "log/demo/LOG.md", "line\n")
        self.run_helper(self.code, "commit", "-m", "Log line")
        self.assertEqual(self.git(self.data, "ls-files", "--", "*.env"), "")
        self.assertIn("log/demo/LOG.md", self.git(self.data, "ls-files"))
        # a secret-looking name the ignore file misses is still refused
        self.write(self.data / "id_rsa", "x\n")
        r = self.run_helper(self.code, "commit", "-m", "Oops", ok=False)
        self.assertIn("secret", r.stderr)
        self.assertEqual(self.git(self.data, "diff", "--cached", "--name-only"), "")

    def test_commit_waits_for_the_lock(self):
        lock = self.data / ".git" / dr.LOCK_NAME
        self.write(self.data / "log/demo/LOG.md", "line\n")
        with open(lock, "w") as held, mock.patch.object(dr, "LOCK_TIMEOUT", 0.3):
            fcntl.flock(held, fcntl.LOCK_EX)
            with self.assertRaises(dr.Stop):
                dr.commit(self.data, "Blocked")
            fcntl.flock(held, fcntl.LOCK_UN)
            self.assertIsNotNone(dr.commit(self.data, "Free"))


class PairingTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.run_helper(self.code, "init")

    def test_add_edit_merge_then_remove(self):
        wt, data_wt = self.add("maint-x")
        self.write(wt / "workspaces/demo/rule.md", "new rule\n")
        self.git(wt, "add", "workspaces/demo/rule.md")
        self.git(wt, "commit", "-q", "-m", "Rule")
        self.write(data_wt / "workspaces/demo/runs/T-1/record.md", "version: 1\n")
        self.run_helper(self.code, "merge", "maint-x")
        self.assertEqual((self.code / "workspaces/demo/rule.md").read_text(), "new rule\n")
        self.assertEqual((self.data / "workspaces/demo/runs/T-1/record.md").read_text(), "version: 1\n")
        heads = (self.head(self.code), self.head(self.data))
        self.run_helper(self.code, "remove", "maint-x", ok=False)  # no confirmation
        self.run_helper(self.code, "remove", "maint-x", "--yes")
        self.assertFalse(wt.exists())
        self.assertFalse(data_wt.exists())
        self.assertEqual((self.head(self.code), self.head(self.data)), heads)
        self.assertFalse(dr.branch_exists(self.code, "maint-x"))
        self.assertFalse(dr.branch_exists(self.data, "maint-x"))
        self.assertEqual(self.git(self.data, "status", "--porcelain"), "")

    def test_discard_leaves_main_checkouts_unchanged(self):
        heads = (self.head(self.code), self.head(self.data))
        files = sorted(str(p) for p in self.data.rglob("*") if ".git" not in p.parts)
        wt, data_wt = self.add("maint-y")
        self.write(wt / "scratch.md", "code edit\n")
        self.git(wt, "add", "scratch.md")
        self.git(wt, "commit", "-q", "-m", "Scratch")
        self.write(data_wt / "log/briefs/test.md", "data edit\n")
        r = self.run_helper(self.code, "remove", "maint-y", "--yes", ok=False)
        self.assertIn("--discard", r.stderr)
        self.assertTrue(wt.exists() and data_wt.exists())
        self.run_helper(self.code, "remove", "maint-y", "--yes", "--discard")
        self.assertFalse(wt.exists() or data_wt.exists())
        self.assertEqual((self.head(self.code), self.head(self.data)), heads)
        self.assertEqual(sorted(str(p) for p in self.data.rglob("*") if ".git" not in p.parts), files)
        self.assertFalse((self.code / "scratch.md").exists())

    def test_two_branches_appending_to_one_log_merge_without_conflict(self):
        log = "log/demo/LOG.md"
        self.write(self.data / log, "# demo log\n")
        self.run_helper(self.code, "commit", "-m", "Start log")
        _, a = self.add("maint-a")
        _, b = self.add("maint-b")
        with open(a / log, "a") as f:
            f.write("line from a\n")
        with open(b / log, "a") as f:
            f.write("line from b\n")
        self.run_helper(self.code, "merge", "maint-a")
        self.run_helper(self.code, "merge", "maint-b")
        text = (self.data / log).read_text()
        self.assertIn("line from a\n", text)
        self.assertIn("line from b\n", text)
        self.assertNotIn("<<<<<<<", text)

    def test_data_conflict_stops_before_code_merge(self):
        wt, data_wt = self.add("maint-c")
        self.write(wt / "code-change.md", "x\n")
        self.git(wt, "add", "code-change.md")
        self.git(wt, "commit", "-q", "-m", "Code")
        self.write(data_wt / "workspaces/demo/repos.md", "| repo | from branch |\n")
        self.write(self.data / "workspaces/demo/repos.md", "| repo | from main |\n")
        code_head = self.head(self.code)
        r = self.run_helper(self.code, "merge", "maint-c", ok=False)
        self.assertIn("stopped before the code merge", r.stderr)
        self.assertEqual(self.head(self.code), code_head)
        self.assertFalse((self.code / "code-change.md").exists())
        self.assertFalse((self.data / ".git" / "MERGE_HEAD").exists())
        self.assertEqual((self.data / "workspaces/demo/repos.md").read_text(), "| repo | from main |\n")

    def test_merge_refuses_uncommitted_code(self):
        wt, _ = self.add("maint-d")
        self.write(wt / "loose.md", "x\n")
        heads = (self.head(self.code), self.head(self.data))
        self.run_helper(self.code, "merge", "maint-d", ok=False)
        self.assertEqual((self.head(self.code), self.head(self.data)), heads)

    def test_default_code_worktree_sits_next_to_the_checkout(self):
        self.run_helper(self.code, "add", "maint/e")
        wt = self.tmp / "ai-system.worktrees" / "maint/e"
        self.assertEqual(self.run_helper(wt, "resolve").stdout.strip(),
                         str(self.data / ".worktrees/maint/e"))
        self.run_helper(self.code, "remove", "maint/e", "--yes")
        self.assertFalse((self.tmp / "ai-system.worktrees").exists())
        self.assertFalse((self.data / ".worktrees").exists())

    def test_add_refuses_an_existing_branch(self):
        self.git(self.data, "branch", "taken")
        self.run_helper(self.code, "add", "taken", "--code-path", str(self.tmp / "wt/taken"), ok=False)
        self.assertFalse((self.tmp / "wt/taken").exists())
        self.assertFalse(dr.branch_exists(self.code, "taken"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
