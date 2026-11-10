#!/usr/bin/env python3
"""Tests for intake.py, review_urls.py, dev_server.py and write_record.py. Run: python3 tools/test_tools.py"""

import argparse
import contextlib
import io
import json
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

import dev_server  # noqa: E402
import intake  # noqa: E402


def run(*args, cwd=None):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=cwd)


ISSUE = {
    "key": "OND-1",
    "fields": {
        "summary": "כותרת",
        "project": {"key": "OND", "name": "ORA"},
        "issuetype": {"name": "Task"},
        "status": {"name": "To Do"},
        "assignee": {"displayName": "Raz"},
        "labels": ["model-page"],
        "description": {"type": "doc", "content": [
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Steps to reproduce"}]},
            {"type": "orderedList", "attrs": {"order": 1}, "content": [
                {"type": "listItem", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "Open "}, {"type": "text", "text": "/model", "marks": [{"type": "code"}]}]}]},
            ]},
            {"type": "mediaSingle", "content": [{"type": "media", "attrs": {"alt": "shot.png", "id": "x"}}]},
            {"type": "table", "content": [
                {"type": "tableRow", "content": [{"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "a|b"}]}]}]},
                {"type": "tableRow", "content": [{"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "1"}]}]}]},
            ]},
        ]},
        "comment": {"total": 3, "comments": [
            {"author": {"displayName": "Alon"}, "created": "2026-11-08",
             "body": {"type": "doc", "content": [{"type": "paragraph", "content": [
                 {"type": "mention", "attrs": {"text": "@Raz"}}, {"type": "text", "text": " h2 please"}]}]}},
        ]},
        "attachment": [{"filename": "shot.png", "mimeType": "image/png", "content": "https://switchil.atlassian.net/rest/api/3/attachment/content/1"}],
        "issuelinks": [{"type": {"outward": "blocks"}, "outwardIssue": {"key": "OND-2", "fields": {"summary": "other"}}}],
        "customfield_10500": "{}",
        "customfield_10007": "0|i04sam:",
        "customfield_10900": {"value": "Mobile"},
    },
}


class IntakeTests(unittest.TestCase):
    def test_parse_key(self):
        self.assertEqual(intake.parse_key("ond-7"), "OND-7")
        self.assertEqual(intake.parse_key("https://switchil.atlassian.net/browse/MAIN-4164"), "MAIN-4164")
        self.assertEqual(intake.parse_key("https://switchil.atlassian.net/jira/software/projects/NSS/boards/1?selectedIssue=NSS-1"), "NSS-1")
        self.assertIsNone(intake.parse_key("nope"))

    def test_ticket_from_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp, "in.json")
            src.write_text(json.dumps(ISSUE, ensure_ascii=False))
            env = {k: v for k, v in os.environ.items() if k not in ("JIRA_EMAIL", "JIRA_API_TOKEN")}
            res = subprocess.run([sys.executable, HERE / "intake.py", "OND-1", "--out", Path(tmp, "o"), "--json-in", src],
                                 capture_output=True, text=True, env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            summary = json.loads(res.stdout)
            self.assertTrue(summary["commentsTruncated"])
            self.assertEqual(summary["attachmentsMissing"], ["shot.png"])
            md = Path(tmp, "o", "ticket.md").read_text()
            self.assertIn("#### Steps to reproduce", md)
            self.assertIn("1. Open `/model`", md)
            self.assertIn("[image: shot.png, not downloaded]", md)
            self.assertIn("| a\\|b |", md)
            self.assertIn("@Raz h2 please", md)
            self.assertIn("- blocks: OND-2 other", md)
            self.assertIn("Mobile", md)
            self.assertNotIn("customfield_10500", md)
            self.assertNotIn("0|i04sam", md)
            self.assertIn("## Comments (1 of 3)", md)

    def test_download_refuses_other_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp, "f")
            self.assertTrue(intake.download("https://evil.example.com/x", dest, "Basic x").startswith("refused"))
            self.assertTrue(intake.download("http://switchil.atlassian.net/x", dest, "Basic x").startswith("refused"))
            self.assertFalse(dest.exists())

    def test_download_url_built_from_attachment_id(self):
        seen = []
        original = intake.download
        intake.download = lambda url, dest, auth: seen.append(url) or "http 403"
        os.environ.update(JIRA_EMAIL="a@b.c", JIRA_API_TOKEN="t")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                intake.fetch_attachments([{"id": "88754", "filename": "s.png",
                                           "content": "https://jira-prod-us-17-2.prod.atl-paas.net/rest/api/3/attachment/content/88754"}], Path(tmp))
        finally:
            intake.download = original
            del os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]
        self.assertEqual(seen, ["https://switchil.atlassian.net/rest/api/3/attachment/content/88754"])

    def test_dropped_attachment_is_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp, "in.json")
            src.write_text(json.dumps(ISSUE, ensure_ascii=False))
            Path(tmp, "o", "attachments").mkdir(parents=True)
            Path(tmp, "o", "attachments", "shot.png").write_bytes(b"png")
            env = {k: v for k, v in os.environ.items() if k not in ("JIRA_EMAIL", "JIRA_API_TOKEN")}
            res = subprocess.run([sys.executable, HERE / "intake.py", "OND-1", "--out", Path(tmp, "o"), "--json-in", src],
                                 capture_output=True, text=True, env=env)
            self.assertEqual(json.loads(res.stdout)["attachmentsMissing"], [])
            md = Path(tmp, "o", "ticket.md").read_text()
            self.assertIn("![shot.png](attachments/shot.png)", md)
            self.assertIn("| provided |", md)


def make_repo(root):
    files = {
        "code/package.json": "{}",
        "code/jsconfig.json": '{\n "compilerOptions": {\n  "baseUrl": "./app", // root\n  "paths": {"@/*": ["components/*"],},\n }\n}',
        "code/app/layout.js": "import Header from '@/Layout/Header';\n",
        "code/app/components/Layout/Header.js": "export default 1;\n",
        "code/app/(pages)/page.js": "import Hero from '@/Hero';\n",
        "code/app/(pages)/[...pageUri]/page.js": "import Card from 'components/Card';\n",
        "code/app/(dynamic-pages)/showrooms/page.js": "import Card from '../../components/Card';\n",
        "code/app/purchase/[model]/page.js": "const M = dynamic(() => import('@/Buy'));\n",
        "code/app/components/Card/index.js": "export { default } from './Card';\n",
        "code/app/components/Card/Card.js": "import s from './Card.module.css';\n",
        "code/app/components/Card/Card.module.css": ".a{}\n",
        "code/app/components/Hero/index.js": "export default 1;\n",
        "code/app/components/Buy/index.js": "export default 1;\n",
        "code/app/components/Sections/Grid/ClientGrid.js": "export default 1;\n",
        "code/app/components/Templates/ContactUs/ContactUs.js": "export default 1;\n",
        "code/app/components/Unused.js": "export default 1;\n",
    }
    for name, text in files.items():
        p = Path(root, name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git = lambda *a: subprocess.run(["git", "-C", root, *a], check=True, capture_output=True)
    git("init", "-q", "-b", "dev")
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    git("checkout", "-qb", "OND-1/test")


class ReviewUrlTests(unittest.TestCase):
    def test_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp)
            code = Path(tmp, "code")
            for rel in ("Card/Card.module.css", "Buy/index.js", "Sections/Grid/ClientGrid.js",
                        "Templates/ContactUs/ContactUs.js", "Layout/Header.js", "Unused.js"):
                with Path(code, "app/components", rel).open("a") as fh:
                    fh.write("/* changed */\n")
            Path(code, "app/components/New.js").write_text("export default 1;\n")
            res = run(HERE / "review_urls.py", "--app-root", code, "--base", "dev", "--port", "3001",
                      "--test-route", "/test/")
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(res.stdout)
            by = {f["file"]: f for f in data["files"]}
            card = by["app/components/Card/Card.module.css"]
            self.assertEqual(card["kind"], "static")
            self.assertEqual({r["route"] for r in card["routes"]}, {"/showrooms", "/[...pageUri]"})
            self.assertEqual(by["app/components/Buy/index.js"]["kind"], "dynamic")
            self.assertEqual(by["app/components/Sections/Grid/ClientGrid.js"]["section"], "Grid")
            self.assertEqual(by["app/components/Templates/ContactUs/ContactUs.js"]["kind"], "template")
            self.assertEqual(by["app/components/Layout/Header.js"]["kind"], "all-pages")
            self.assertEqual(by["app/components/Unused.js"]["kind"], "unmapped")
            self.assertEqual(by["app/components/New.js"]["kind"], "unmapped")
            self.assertEqual(sorted(data["urls"]), ["http://localhost:3001/", "http://localhost:3001/showrooms",
                                                    "http://localhost:3001/test/"])

    def locale_repo(self, tmp):
        make_repo(tmp)
        code = Path(tmp, "code")
        files = {
            "app/i18n/Lang/He.json": json.dumps({"a": {"x": "1"}, "b": {"y": "2"}}),
            "app/one/page.js": "import heb from '../i18n/Lang/He.json';\nexport default () => heb.a.x;\n",
            "app/two/page.js": "import heb from '../i18n/Lang/He.json';\nimport Hero from '@/Hero';\n"
                               "export default () => heb.b.y;\n",
        }
        for name, text in files.items():
            Path(code, name).parent.mkdir(parents=True, exist_ok=True)
            Path(code, name).write_text(text)
        git = lambda *a: subprocess.run(["git", "-C", tmp, "-c", "user.email=t@t", "-c", "user.name=t", *a],
                                        check=True, capture_output=True)
        git("checkout", "-q", "dev")
        git("add", ".")
        git("commit", "-qm", "strings")
        git("checkout", "-qB", "OND-1/test")
        Path(code, "app/i18n/Lang/He.json").write_text(json.dumps({"a": {"x": "3"}, "b": {"y": "2"}}))
        return code

    def review(self, code):
        res = run(HERE / "review_urls.py", "--app-root", code, "--base", "dev", "--port", "3001")
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_shared_strings_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self.review(self.locale_repo(tmp))
            self.assertIn("http://localhost:3001/one", data["urls"])
            self.assertNotIn("http://localhost:3001/two", data["urls"])
            self.assertEqual(data["sharedStringsOnly"], ["/two"])
            he = {f["file"]: f for f in data["files"]}["app/i18n/Lang/He.json"]
            self.assertEqual(he["changedKeys"], ["a.x"])
            self.assertEqual({r["route"] for r in he["routes"] if r.get("sharedStringsOnly")}, {"/two"})

    def test_shared_strings_kept_when_code_also_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self.locale_repo(tmp)
            with Path(code, "app/components/Hero/index.js").open("a") as fh:
                fh.write("/* changed */\n")
            data = self.review(code)
            self.assertIn("http://localhost:3001/two", data["urls"])
            self.assertEqual(data["sharedStringsOnly"], [])

    def test_shared_strings_unknown_keeps_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self.locale_repo(tmp)
            Path(code, "app/i18n/Lang/He.json").write_text("{not json")
            data = self.review(code)
            self.assertIn("http://localhost:3001/two", data["urls"])
            self.assertEqual(data["sharedStringsOnly"], [])
            he = {f["file"]: f for f in data["files"]}["app/i18n/Lang/He.json"]
            self.assertIsNone(he["changedKeys"])


class DevServerTests(unittest.TestCase):
    def test_down_without_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run(HERE / "dev_server.py", "down", "--state", Path(tmp, "none.json"))
            self.assertEqual(json.loads(res.stdout)["stopped"], False)

    def test_down_refuses_foreign_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp, "s.json")
            state.write_text(json.dumps({"pid": 1, "startedBy": "someone"}))
            res = run(HERE / "dev_server.py", "down", "--state", state)
            self.assertEqual(res.returncode, 2)
            self.assertTrue(state.exists())

    def test_up_rejects_bad_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "package.json").write_text("{}")
            res = run(HERE / "dev_server.py", "up", "--app-root", tmp, "--state", Path(tmp, "s.json"), "--path", "//evil")
            self.assertEqual(res.returncode, 2)

    def test_split_sorts_by_cwd(self):
        fake = [{"port": 3000, "pid": 1, "cwd": "/a/code", "cmd": "next-server (v16)"},
                {"port": 3001, "pid": 2, "cwd": "/a/code-other", "cmd": "node next dev"},
                {"port": 3002, "pid": 3, "cwd": "/a/code/sub", "cmd": "next-server"},
                {"port": 40000, "pid": 4, "cwd": "/home", "cmd": "cursorsandbox --policy x"}]
        original = dev_server.listeners
        dev_server.listeners = lambda: fake
        try:
            matches, others = dev_server.split("/a/code")
        finally:
            dev_server.listeners = original
        self.assertEqual([m["port"] for m in matches], [3000, 3002])
        self.assertEqual([o["port"] for o in others], [3001])

    def test_reuse_of_foreign_server_is_recorded_not_ours(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp, "s.json")
            record = dev_server.reuse_record(state, {"port": 3000, "pid": os.getpid()}, "/a/code", "s.log")
            self.assertFalse(record["startedByUs"])
            self.assertEqual(record["pid"], os.getpid())

    def test_reuse_keeps_own_record_for_same_process_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp, "s.json")
            state.write_text(json.dumps({"startedBy": "ticket-execution", "pid": os.getpgid(0), "port": 3000}))
            record = dev_server.reuse_record(state, {"port": 3001, "pid": os.getpid()}, "/a/code", "s.log")
            self.assertTrue(record["startedByUs"])
            self.assertEqual((record["pid"], record["port"]), (os.getpgid(0), 3001))
            self.assertEqual(record["listenerPid"], os.getpid())

    def up_reused(self, tmp, statuses, timeout):
        Path(tmp, "package.json").write_text("{}")
        state = Path(tmp, "s.json")
        args = argparse.Namespace(app_root=tmp, state=str(state), port=None, path="/", timeout=timeout,
                                  keep_schema=False)
        match = {"port": 3000, "pid": 4242, "cwd": tmp, "cmd": "next-server"}
        calls = []

        def status(port, path):
            calls.append((port, path))
            return statuses[min(len(calls), len(statuses)) - 1]

        buf = io.StringIO()
        with mock.patch.object(dev_server, "split", return_value=([match], [])), \
                mock.patch.object(dev_server, "http_status", side_effect=status), \
                mock.patch.object(dev_server.time, "sleep"), \
                contextlib.redirect_stdout(buf), self.assertRaises(SystemExit) as exc:
            dev_server.cmd_up(args)
        return exc.exception.code, json.loads(buf.getvalue()), state, calls

    def test_reuse_waits_for_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, data, state, calls = self.up_reused(tmp, [None, 503, 200], 300)
            self.assertEqual(code, 0)
            self.assertEqual(data["httpStatus"], 200)
            self.assertEqual(len(calls), 3)
            self.assertEqual(data["listenerPid"], 4242)
            self.assertEqual(json.loads(state.read_text())["listenerPid"], 4242)

    def test_reuse_times_out_with_7(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, data, state, _ = self.up_reused(tmp, [500], 0)
            self.assertEqual(code, 7)
            self.assertTrue(state.exists())
            self.assertTrue(data["reused"])

    def test_listener_pid_by_port(self):
        fake = [{"port": 3000, "pid": 11, "cwd": "/a/code", "cmd": "next-server"},
                {"port": 3001, "pid": 12, "cwd": "/a/code", "cmd": "next-server"}]
        with mock.patch.object(dev_server, "listeners", return_value=fake):
            self.assertEqual(dev_server.listener_pid("/a/code", 3001), 12)
            self.assertIsNone(dev_server.listener_pid("/a/code", 3005))

    def test_reuse_replaces_stale_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp, "s.json")
            state.write_text(json.dumps({"startedBy": "ticket-execution", "pid": 999999999, "port": 3000}))
            record = dev_server.reuse_record(state, {"port": 3000, "pid": os.getpid()}, "/a/code", "s.log")
            self.assertFalse(record["startedByUs"])

    def test_down_leaves_reused_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp, "s.json")
            state.write_text(json.dumps({"startedBy": "ticket-execution", "startedByUs": False, "pid": os.getpid()}))
            res = run(HERE / "dev_server.py", "down", "--state", state)
            data = json.loads(res.stdout)
            self.assertEqual((res.returncode, data["stopped"]), (0, False))
            self.assertFalse(state.exists())


class WriteRecordTests(unittest.TestCase):
    RECORD = "version: 3\n\n# Verify\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name).resolve()
        Path(self.ws, "tools").mkdir()
        Path(self.ws, "stages", "05-verify").mkdir(parents=True)
        shutil.copy(HERE / "write_record.py", Path(self.ws, "tools", "write_record.py"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, stage, key, text):
        res = subprocess.run([sys.executable, Path(self.ws, "tools", "write_record.py"), "--stage", stage, "--key", key],
                             input=text, capture_output=True, text=True)
        return res.returncode, json.loads(res.stdout)

    def test_writes_stage_record(self):
        code, data = self.write("05", "ABC-1", self.RECORD)
        target = Path(self.ws, "stages", "05-verify", "output", "ABC-1", "verify-report.md")
        self.assertEqual(code, 0)
        self.assertEqual(Path(data["path"]), target)
        self.assertEqual(target.read_text(), self.RECORD)
        self.assertFalse(data["replaced"])

    def test_replaces_atomically(self):
        self.write("05", "ABC-1", self.RECORD)
        code, data = self.write("05", "ABC-1", "version: 3\nsecond\n")
        folder = Path(self.ws, "stages", "05-verify", "output", "ABC-1")
        self.assertEqual(code, 0)
        self.assertTrue(data["replaced"])
        self.assertEqual(Path(folder, "verify-report.md").read_text(), "version: 3\nsecond\n")
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["verify-report.md"])

    def test_refuses_bad_key(self):
        for key in ("../x", "abc", "ABC-1/../../..", "ABC-1\n"):
            code, data = self.write("05", key, self.RECORD)
            self.assertEqual(code, 2, key)
            self.assertFalse(data["ok"])
        self.assertFalse(Path(self.ws, "stages", "05-verify", "output").exists())
        self.assertFalse(Path(self.ws, "stages", ".run-lock").exists())

    def test_refuses_symlinked_output(self):
        with tempfile.TemporaryDirectory() as outside:
            Path(self.ws, "stages", "05-verify", "output").mkdir()
            Path(self.ws, "stages", "05-verify", "output", "ABC-1").symlink_to(outside)
            code, _ = self.write("05", "ABC-1", self.RECORD)
            self.assertEqual(code, 2)
            self.assertEqual(list(Path(outside).iterdir()), [])
        with tempfile.TemporaryDirectory() as outside:
            shutil.rmtree(Path(self.ws, "stages", "05-verify", "output"))
            Path(self.ws, "stages", "05-verify", "output").symlink_to(outside)
            code, _ = self.write("05", "ABC-1", self.RECORD)
            self.assertEqual(code, 2)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_refuses_empty_or_unversioned(self):
        for text in ("", "  \n", "# Verify\n\nno version\n", "a\nb\nc\nd\ne\nversion: 3\n"):
            code, data = self.write("05", "ABC-1", text)
            self.assertEqual(code, 3, repr(text))
            self.assertFalse(data["ok"])
        self.assertFalse(Path(self.ws, "stages", "05-verify", "output", "ABC-1", "verify-report.md").exists())

    def test_unknown_stage(self):
        for stage in ("08", "5", "00"):
            code, data = self.write(stage, "ABC-1", self.RECORD)
            self.assertEqual(code, 2, stage)
            self.assertFalse(data["ok"])
        self.assertFalse(Path(self.ws, "stages", "05-verify", "output").exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
