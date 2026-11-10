#!/usr/bin/env python3
"""Tests for session_digest.py and check_debrief.py. Run: python3 -m unittest (in this folder).

All fixtures are synthetic and built in temp dirs; no real session file is touched.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_debrief  # noqa: E402
import session_digest  # noqa: E402

CWD = "/work/proj"
A = "aaaaaa11-0000-4000-8000-000000000001"  # cursor parent
B = "bbbbbb22-0000-4000-8000-000000000002"  # cursor parent, older
SUB = "cccccc33-0000-4000-8000-000000000003"  # cursor subagent of A
K = "aaaaaa33-0000-4000-8000-000000000004"  # kiro main session
KS = "dddddd44-0000-4000-8000-000000000005"  # kiro subagent of K
RW = "ffffff66-0000-4000-8000-000000000006"  # kiro "rewind" session with a parent_session_id (NOT a subagent)
D = "eeeeee55-0000-4000-8000-000000000007"  # cursor session with repos, long text, auto notification
FAKE_FIGMA = "figd_" + "abcDEF0123456789xyz"
FAKE_JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk1234"
KS_FINAL = "HEADMARK " + "word " * 700 + "TAILMARK"  # 3.5k chars: cut at 500 in Meta, at 3000 by --subagent all


def jl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write((row if isinstance(row, str) else json.dumps(row)) + "\n")


def cur_user(text, ts="Thursday, Nov 5, 2026, 11:11 AM (UTC+2)"):
    body = f"<timestamp>{ts}</timestamp>\n<user_query>\n{text}\n</user_query>\n<available_subagent_types>x</available_subagent_types>"
    return {"role": "user", "message": {"content": [{"type": "text", "text": body}]}}


def cur_asst(*blocks):
    return {"role": "assistant", "message": {"content": list(blocks)}}


def txt(s):
    return {"type": "text", "text": s}


def tool(name, inp):
    return {"type": "tool_use", "name": name, "input": inp}


def dyn(tool_name, args):
    return tool("CallDynamicTool", {"namespace": "cursor", "toolName": tool_name, "arguments": args})


PATCH = ("*** Begin Patch\n*** Add File: /tmp/x/new.py\n+print(1)\n"
         "*** Update File: /tmp/x/a.py\n@@\n-a\n+b\n*** End Patch")


def kiro_text(kind, blocks, **extra):
    return {"version": "v1", "kind": kind, "data": {"message_id": "m", "content": blocks, **extra}}


def kblock(kind, data):
    return {"kind": kind, "data": data}


def make_env(root):
    cursor = Path(root) / "cursor"
    kiro = Path(root) / "kiro"
    base = cursor / "work-proj" / "agent-transcripts"
    jl(base / A / f"{A}.jsonl", [
        cur_user(f"Build the thing, token {FAKE_FIGMA} is in my env"),
        cur_asst(txt("Building.\n\n[REDACTED]"), tool("Shell", {"command": "ls -la", "description": "list"}),
                 dyn("Task", {"description": "Explore X", "prompt": "Explore the repo thoroughly and report back"}),
                 dyn("Delete", {"path": "/tmp/x/old.txt"}),
                 tool("ApplyPatch", PATCH),
                 tool("Write", {"path": "/tmp/x/a.py", "contents": "x"}),
                 tool("StrReplace", {"path": "/tmp/x/a.py", "old_string": "a", "new_string": "b"})),
        "this is not json",
        cur_asst(txt(f"I could not verify the build. Do you want me to deploy? Header Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123 {FAKE_JWT}")),
        {"type": "turn_ended", "status": "success"},
        {"role": "user", "message": {"content": [txt("<system_notification>Subagent finished</system_notification>")]}},
        cur_asst(txt("Explorer reported: found 3 files.")),
        cur_user("Ship it", ts="Thursday, Nov 5, 2026, 12:00 PM (UTC+2)"),
        cur_asst(txt("Done. Deferred: the tests."), tool("AskQuestion", {"title": "Pick", "questions": [{"prompt": "Which env?"}]})),
        {"type": "turn_ended", "status": "success"},
    ])
    jl(base / A / "subagents" / f"{SUB}.jsonl", [cur_user("Explore the repo thoroughly and report back"),
                                                 cur_asst(txt("[REDACTED]")),
                                                 cur_asst(txt(f"Explored the repo, found 3 files. Leaked {FAKE_FIGMA} by mistake."))])
    jl(base / B / f"{B}.jsonl", [cur_user("Old session"), cur_asst(txt("ok"))])
    now = time.time()
    os.utime(base / B / f"{B}.jsonl", (now - 5000, now - 5000))
    os.utime(base / A / f"{A}.jsonl", (now - 3000, now - 3000))
    os.utime(base / A / "subagents" / f"{SUB}.jsonl", (now - 100, now - 100))  # newest, but a subagent

    kiro.mkdir(parents=True)
    jl(kiro / f"{K}.jsonl", [
        kiro_text("Prompt", [kblock("text", 'Edit it <attached_file path="/w/f.md">BODY BODY</attached_file> now')],
                  meta={"timestamp": 1791204762}),
        kiro_text("AssistantMessage", [
            kblock("text", "Working on it."),
            kblock("toolUse", {"toolUseId": "t1", "name": "write", "input": {"command": "create", "path": "/w/f.md", "content": "hi"}}),
            kblock("toolUse", {"toolUseId": "t2", "name": "shell", "input": {"command": "npm test", "working_dir": "/w"}}),
            kblock("toolUse", {"toolUseId": "t3", "name": "subagent", "input": {"task": "Review it", "stages": [{"name": "rev"}]}}),
            kblock("toolUse", {"toolUseId": "t4", "name": "shell", "input": {"command": "echo ok", "working_dir": "/w"}}),
        ]),
        kiro_text("ToolResults", [
            kblock("toolResult", {"toolUseId": "t2", "content": [kblock("text", "ignored")], "status": "success"}),
            kblock("toolResult", {"toolUseId": "t4", "content": [kblock("text", "ok")], "status": "success"}),
            kblock("toolResult", {"toolUseId": "t8", "status": "success", "content": [
                {"kind": "json", "data": {"exit_status": "exit status: 0", "stdout": f"found key {FAKE_FIGMA} in env", "stderr": ""}},
                {"kind": "image", "data": {"format": "png", "source": "QUJD" * 40}}]}),
            kblock("toolResult", {"toolUseId": "t9", "status": "success", "content": [
                kblock("text", f"again {FAKE_FIGMA} and {FAKE_JWT} here")]}),
            kblock("text", "[LIVE STEERING - New message from user]\n\nThe user sent a new message while you are working. "
                           "As the currently active agent, adjust your approach.\n\n"
                           '<user_message id="steer-1">\nplease also run lint\n</user_message>\n\n'
                           "IMPORTANT: After completing your work, include a brief note."),
        ], results={"t2": {"tool": None, "result": {"Success": {"items": [
            {"Json": {"exit_status": "exit status: 1", "stdout": "", "stderr": "boom " + "err " * 100}}]}}},
            "t4": {"tool": None, "result": {"Success": {"items": [
                {"Json": {"exit_status": "exit status: 0", "stdout": "ok", "stderr": "warnonly"}}]}}}}),
        kiro_text("Compaction", [], summary="Earlier we did the setup. Pending: lint.\n- `cd /x && make`"),
        {"version": "v1", "kind": "Clear"},
        "{broken",
        kiro_text("Prompt", [kblock("text", "second prompt")], meta={"timestamp": 1791208362}),
        kiro_text("AssistantMessage", [kblock("text", "All set, still open: lint is a follow-up.")]),
    ])
    (kiro / f"{K}.json").write_text(json.dumps({"session_id": K, "cwd": CWD, "title": "Edit it now", "created_at": "2026-10-05T12:52:42.306330694Z"}))
    jl(kiro / f"{KS}.jsonl", [kiro_text("Prompt", [kblock("text", "sub work")], meta={"timestamp": 1791204800}),
                              kiro_text("AssistantMessage", [kblock("text", "first words")]),
                              kiro_text("AssistantMessage", [kblock("text", KS_FINAL)])])
    (kiro / f"{KS}.json").write_text(json.dumps({"session_id": KS, "cwd": CWD, "title": "Review it",
                                                 "session_created_reason": "subagent", "parent_session_id": K}))
    # cursor session with real repos on disk (a .git dir and a worktree-style .git file), a long final
    # text with a table, and a stock "subagent finished" auto prompt
    repo, wt, gone = Path(root) / "repo", Path(root) / "wt", Path(root) / "gone"
    (repo / ".git").mkdir(parents=True)
    (repo / "src").mkdir()
    wt.mkdir()
    (wt / ".git").write_text("gitdir: /elsewhere")
    table = "| col | val |\n|---|---|\n" + "\n".join(f"| row{i} | {'v' * 40} |" for i in range(60))
    jl(cursor / "other-proj" / "agent-transcripts" / D / f"{D}.jsonl", [
        cur_user("Do the repo work " + "long " * 400),
        cur_asst(txt("Starting."),
                 tool("Shell", {"command": f"cd {repo}/src && ls", "working_directory": str(gone)}),
                 tool("Shell", {"command": f"git -C {repo} status && echo `date`"}),
                 tool("Write", {"path": str(repo / "src" / "m.ts"), "contents": "x"}),
                 tool("Write", {"path": str(wt / "deep" / "w.ts"), "contents": "x"})),
        cur_asst(txt("Result:\n\n" + table + "\n\nNot fixed yet: the overlay. It needs a separate change.\n- item one\n- item two")),
        cur_user("Perform any necessary follow-up actions in response to the subagent completion above. "
                 "If no follow-up work is needed, no further action is required.", ts="Thursday, Nov 5, 2026, 1:00 PM (UTC+2)"),
        cur_asst(txt("The explorer finished: it found the bug in m.ts. " + "detail " * 80)),
        cur_user("Real follow-up question", ts="Thursday, Nov 5, 2026, 2:00 PM (UTC+2)"),
        cur_asst(txt("Fine.")),
    ])
    os.utime(cursor / "other-proj" / "agent-transcripts" / D / f"{D}.jsonl", (now - 9000, now - 9000))

    jl(kiro / f"{RW}.jsonl", [kiro_text("Prompt", [kblock("text", "rewound prompt one")], meta={"timestamp": 1791204900}),
                              kiro_text("AssistantMessage", [kblock("text", "ok")]),
                              kiro_text("Prompt", [kblock("text", "rewound prompt two")], meta={"timestamp": 1791204950})])
    (kiro / f"{RW}.json").write_text(json.dumps({"session_id": RW, "cwd": CWD, "title": "rewound",
                                                 "session_created_reason": "rewind", "parent_session_id": K}))
    os.utime(kiro / f"{RW}.jsonl", (now - 9000, now - 9000))
    return cursor, kiro


def run_digest(env_dirs, *args):
    cursor, kiro = env_dirs
    env = dict(os.environ, CURSOR_PROJECTS_DIR=str(cursor), KIRO_SESSIONS_DIR=str(kiro))
    return subprocess.run([sys.executable, str(HERE / "session_digest.py"), *args], capture_output=True, text=True, env=env)


class DigestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = make_env(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_lookup_by_prefix_cursor(self):
        r = run_digest(self.env, "aaaaaa1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- Source: cursor", r.stdout)
        self.assertIn(f"- Session id: {A}", r.stdout)
        self.assertIn("User turns: 2 (auto notifications collapsed: 1", r.stdout)
        self.assertIn("Explore X", r.stdout)  # subagent child matched to Task description
        self.assertIn(f"  - [1] {SUB[:8]}: Explore X [prompt,", r.stdout)
        self.assertRegex(r.stdout, r"<!-- digest: \d+ chars, truncated: no -->\s*$")

    def test_lookup_subagent_and_kiro(self):
        r = run_digest(self.env, SUB[:8])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Subagent session: yes", r.stdout)
        self.assertIn(f"parent {A}", r.stdout)
        r = run_digest(self.env, KS)
        self.assertIn("Subagent session: yes", r.stdout)
        self.assertIn(f"(parent {K})", r.stdout)

    def test_kiro_rewind_with_parent_is_not_subagent(self):
        out = run_digest(self.env, RW).stdout
        self.assertIn("- Subagent session: no", out)
        self.assertIn(f"- Created reason: rewind (parent_session_id {K})", out)
        self.assertIn("User turns: 2", out)
        self.assertTrue(session_digest.kiro_is_subagent({"session_created_reason": "subagent"}))
        self.assertTrue(session_digest.kiro_is_subagent({"parent_session_id": "x"}))  # no reason recorded
        self.assertFalse(session_digest.kiro_is_subagent({"session_created_reason": "rewind", "parent_session_id": "x"}))
        self.assertFalse(session_digest.kiro_is_subagent({}))

    def test_ambiguous_prefix_exit_3(self):
        r = run_digest(self.env, "aaaaaa")
        self.assertEqual(r.returncode, 3)
        data = json.loads(r.stdout)
        self.assertEqual({m["source"] for m in data["matches"]}, {"cursor", "kiro"})
        self.assertTrue(all({"path", "source", "mtime"} <= set(m) for m in data["matches"]))

    def test_not_found_and_bad_args(self):
        self.assertEqual(run_digest(self.env, "eeeeee99").returncode, 2)
        self.assertEqual(run_digest(self.env, "abc").returncode, 2)
        self.assertEqual(run_digest(self.env).returncode, 2)
        self.assertEqual(run_digest(self.env, "aaaaaa1", "--max-chars", "10").returncode, 2)
        missing = (Path(self.tmp.name) / "nope1", Path(self.tmp.name) / "nope2")
        self.assertEqual(run_digest(missing, "aaaaaa1").returncode, 2)

    def test_redaction(self):
        r = run_digest(self.env, A)
        out = r.stdout
        for needle in (FAKE_FIGMA, "figd_abc", "abcdefghijklmnopqrstuvwxyz0123", "eyJhbGci"):
            self.assertNotIn(needle, out)
        self.assertIn("[REDACTED_FIGMA_TOKEN]", out)
        self.assertIn("Bearer [REDACTED]", out)

    def test_redact_function_patterns(self):
        samples = {
            "p": "password=hunter2hunter2 x",
            "k": "-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----",
            "g": "ghp_" + "a" * 36,
            "gp": "github_pat_" + "B" * 30,
            "s": "xoxb-1234567890-abcdefghij",
            "aws": "AKIA" + "A" * 16,
            "b64": "x" + "QUJD" * 20,
            "data": "data:image/png;base64," + "A" * 40,
        }
        for key, value in samples.items():
            self.assertNotEqual(session_digest.redact(value), value, key)
        keep = "/home/dev/ai-system/workspaces/skill-factory/stages/04-draft-and-test/output/draft-skill/scripts"
        self.assertEqual(session_digest.redact("/Users/aaaa/bbbbbbbbb/cccccccccc/ddddddddd/eeeeeeeeee/fffffffff/gggggggg/hhhhhhhh"),
                         "/Users/aaaa/bbbbbbbbb/cccccccccc/ddddddddd/eeeeeeeeee/fffffffff/gggggggg/hhhhhhhh")
        self.assertEqual(session_digest.redact(keep), keep)

    def test_files_touched_table(self):
        out = run_digest(self.env, A).stdout
        self.assertIn("| /tmp/x/a.py | no | 3 | 1 | 1 |", out)  # ApplyPatch update + Write + StrReplace
        self.assertIn("| /tmp/x/new.py | no | 1 | 1 | 1 |", out)
        self.assertIn("| /tmp/x/old.txt | no | 1 | 1 | 1 |", out)  # Delete via CallDynamicTool
        self.assertIn("Shell x1", out)
        self.assertIn("Task x1", out)  # CallDynamicTool normalised to its toolName
        self.assertNotIn("CallDynamicTool", out)

    def test_cursor_turn_content(self):
        out = run_digest(self.env, A).stdout
        self.assertIn("### Turn 1 — Thursday, Nov 5, 2026, 11:11 AM (UTC+2) — jsonl lines 1-5", out)
        self.assertIn("### Turn 3 — Thursday, Nov 5, 2026, 12:00 PM (UTC+2) — jsonl lines 8-10", out)
        self.assertIn("`ls -la`", out)
        self.assertIn("Subagents launched: Explore X", out)
        self.assertIn("Do you want me to deploy?", out)
        self.assertIn("Which env?", out)
        self.assertNotIn("<user_query>", out)
        self.assertNotIn("available_subagent_types", out)
        self.assertIn("Turn 2: auto notification — Subagent finished → result: Explorer reported: found 3 files.", out)
        self.assertNotIn("### Turn 2", out)  # collapsed to one line, no section
        self.assertRegex(out, r"Turn 1: I could not verify")
        self.assertIn("## Final assistant message\n- jsonl line: 9\n> Done. Deferred: the tests.", out)

    def test_kiro_digest(self):
        out = run_digest(self.env, K).stdout
        self.assertIn("- Source: kiro", out)
        self.assertIn("- Cwd: " + CWD, out)
        self.assertIn("- Title: Edit it now", out)
        self.assertIn("`npm test` (exit 1; stderr: " + ("boom " + "err " * 100)[:200] + ")", out)  # first 200 chars of stderr
        self.assertIn("`echo ok` (exit 0)", out)  # no stderr when the exit status is 0
        self.assertNotIn("warnonly", out)
        self.assertIn("| /w/f.md | no | 1 | 1 | 1 |", out)
        self.assertIn("[attached file: /w/f.md]", out)
        self.assertNotIn("BODY BODY", out)
        self.assertIn("> (mid-turn user message) please also run lint", out)
        self.assertNotIn("LIVE STEERING", out)
        self.assertNotIn("currently active agent", out)
        self.assertIn("#### Compaction summary (jsonl line 4)\n> Earlier we did the setup. Pending: lint.\n> - `cd /x && make`", out)
        self.assertIn("### Turn 1 — 2026-10-05 12:52 UTC — jsonl lines 1-3", out)
        self.assertIn("### Turn 2 — 2026-10-05 13:52 UTC — jsonl lines 7-8", out)
        self.assertLess(out.index("### Turn 1"), out.index("— /clear —"))  # the Clear row sits between the turns
        self.assertLess(out.index("— /clear —"), out.index("### Turn 2"))
        self.assertIn("- Working dirs: /w ×2 (missing now), /work/proj ×1 (missing now)", out)
        self.assertIn("- Subagent session: no", out)
        self.assertNotIn(RW[:8], out)  # a rewind session is not a subagent child
        self.assertIn("Review it [stages: rev]", out)
        self.assertIn(f"{KS[:8]}: Review it", out)  # child via parent_session_id
        self.assertIn("2026-10-", out)  # epoch timestamps rendered
        self.assertIn("unparseable line(s) skipped", out)
        self.assertIn("still open: lint is a follow-up", out)

    def test_latest_cursor_ignores_subagent(self):
        r = run_digest(self.env, "--latest", "--cwd", CWD, "--source", "cursor")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"- Session id: {A}", r.stdout)  # not the newer subagent file, not B

    def test_latest_both_sources_picks_newest(self):
        now = time.time()
        os.utime(Path(self.env[1]) / f"{K}.jsonl", (now, now))
        r = run_digest(self.env, "--latest", "--cwd", CWD)
        self.assertIn(f"- Session id: {K}", r.stdout)
        self.assertIn("picked newest overall: kiro", r.stdout)
        r = run_digest(self.env, "--latest", "--cwd", CWD + "/sub/dir", "--source", "kiro")  # ancestor cwd match
        self.assertIn(f"- Session id: {K}", r.stdout)
        r = run_digest(self.env, "--latest", "--cwd", CWD + "/sub", "--source", "cursor")  # slug walk-up
        self.assertIn(f"- Session id: {A}", r.stdout)

    def test_latest_unknown_cwd(self):
        self.assertEqual(run_digest(self.env, "--latest", "--cwd", "/nowhere/else").returncode, 2)

    def test_json_and_path(self):
        r = run_digest(self.env, "--path", str(Path(self.env[0]) / "work-proj/agent-transcripts" / A / f"{A}.jsonl"), "--json")
        data = json.loads(r.stdout)
        self.assertEqual(data["meta"]["user_turns"], 2)
        self.assertEqual(data["meta"]["source"], "cursor")
        self.assertIn("digest", data)
        self.assertNotIn(FAKE_FIGMA, r.stdout)

    def test_budget_shrinks_and_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor, kiro = Path(tmp) / "c", Path(tmp) / "k"
            kiro.mkdir()
            big = "9f8e7d6c-0000-4000-8000-000000000009"
            rows = []
            for i in range(30):
                rows.append(cur_user(f"question {i} " + "word " * 300))
                rows.append(cur_asst(txt(f"answer {i} " + "text " * 400),
                                     *[tool("Shell", {"command": f"echo {j} && " + "x" * 300}) for j in range(12)]))
            jl(cursor / "work-proj" / "agent-transcripts" / big / f"{big}.jsonl", rows)
            r = run_digest((cursor, kiro), big[:8], "--max-chars", "9000")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertLessEqual(len(r.stdout), 9100)
            self.assertIn("truncated: yes", r.stdout)
            self.assertIn("### Turn 1 ", r.stdout)
            self.assertIn("### Turn 30 ", r.stdout)
            self.assertIn("## Files touched", r.stdout)
            self.assertIn("## Final assistant message", r.stdout)


    def test_working_dirs_hint(self):
        root = Path(self.tmp.name)
        out = run_digest(self.env, D).stdout
        line = next(l for l in out.splitlines() if l.startswith("- Working dirs:"))
        self.assertIn(f"{root}/gone ×1 (missing now)", line)  # Shell working_directory that no longer exists
        self.assertIn(f"{root}/repo/src ×1", line)  # cd <path>
        self.assertIn(f"{root}/repo ×2", line)  # git -C <path> + git toplevel of the edited file
        self.assertIn(f"{root}/wt ×1", line)  # worktree-style `.git` file, found by walking up
        self.assertLessEqual(line.count(" ×"), 5)
        cache = {}
        self.assertEqual(session_digest.git_toplevel(f"{root}/repo/src/deep/x.ts", cache), f"{root}/repo")
        self.assertIsNone(session_digest.git_toplevel("relative/x.ts", cache))

    def test_turn_option_prints_meta_and_turn_in_full(self):
        out = run_digest(self.env, D, "--turn", "1").stdout
        self.assertNotIn("## Meta", out)  # compact 3-line header instead of Meta
        self.assertEqual(out.splitlines()[:3], [f"Session id: {D}", "Source: cursor",
                                                "Turns: 2 user turns (3 numbered, 1 of them auto notifications)"])
        self.assertNotIn("Working dirs", out)
        self.assertNotIn("Later sessions", out)
        self.assertIn("### Turn 1 ", out)
        self.assertNotIn("### Turn 3", out)
        self.assertNotIn("## Files touched", out)
        self.assertNotIn("## Final assistant message", out)
        self.assertIn("long " * 399 + "long", out)  # 2000-char user text not cut
        self.assertIn("| row59 | " + "v" * 40 + " |", out)  # long final text kept whole, table preserved
        self.assertIn("|---|---|", out)
        self.assertIn("- item two", out)
        self.assertNotIn("[…]", out)
        self.assertRegex(out, r"### Turn 1 — .*jsonl lines 1-3")
        out = run_digest(self.env, D, "--turn", "3", "--turn", "1").stdout
        self.assertIn("### Turn 1 ", out)
        self.assertIn("### Turn 3 ", out)
        self.assertIn("Real follow-up question", out)
        self.assertIn("**Assistant (final text, jsonl line 7):**\n> Fine.", out)  # not folded into the final section
        # turn 2 of D is an auto notification: shown in full when requested
        out = run_digest(self.env, D, "--turn", "2").stdout
        self.assertIn("### Turn 2 ", out)
        self.assertIn("detail " * 79 + "detail", out)
        self.assertEqual(run_digest(self.env, D, "--turn", "99").returncode, 2)
        self.assertEqual(run_digest(self.env, D, "--turn", "0").returncode, 2)
        r = run_digest(self.env, A, "--turn", "1")
        self.assertNotIn(FAKE_FIGMA, r.stdout)
        self.assertNotIn(FAKE_JWT, r.stdout)
        self.assertIn("[REDACTED_FIGMA_TOKEN]", r.stdout)

    def test_turn_option_shows_clear_and_compaction_for_that_turn(self):
        out = run_digest(self.env, K, "--turn", "1").stdout
        self.assertIn("#### Compaction summary", out)
        self.assertNotIn("### Turn 2", out)
        out = run_digest(self.env, K, "--turn", "2").stdout
        self.assertNotIn("### Turn 1", out)

    def test_default_truncates_and_full_does_not(self):
        default = run_digest(self.env, D).stdout
        self.assertNotIn("long " * 399 + "long", default)  # the 2000-char user text is cut at 1500
        full = run_digest(self.env, D, "--full")
        self.assertEqual(full.returncode, 0, full.stderr)
        self.assertIn("long " * 399 + "long", full.stdout)
        self.assertIn("| row59 | " + "v" * 40 + " |", full.stdout)
        self.assertEqual(full.stderr, "")  # small output: no warning
        full_a = run_digest(self.env, A, "--full").stdout
        self.assertNotIn(FAKE_FIGMA, full_a)
        self.assertIn("[REDACTED_FIGMA_TOKEN]", full_a)

    def test_full_warns_over_150k_and_broken_pipe_is_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor, kiro = Path(tmp) / "c", Path(tmp) / "k"
            kiro.mkdir()
            big = "9f8e7d6c-0000-4000-8000-00000000000a"
            rows = []
            for i in range(14):
                rows.append(cur_user(f"question {i} " + ("word " * 500 + "\n") * 8))
                rows.append(cur_asst(txt(f"answer {i} " + ("text " * 500 + "\n") * 8)))
            jl(cursor / "work-proj" / "agent-transcripts" / big / f"{big}.jsonl", rows)
            r = run_digest((cursor, kiro), big[:8], "--full")
            self.assertEqual(r.returncode, 0)
            self.assertGreater(len(r.stdout), 150_000)
            self.assertIn("over 150,000", r.stderr)
            default = run_digest((cursor, kiro), big[:8])
            self.assertEqual(default.stderr, "")
            env = dict(os.environ, CURSOR_PROJECTS_DIR=str(cursor), KIRO_SESSIONS_DIR=str(kiro))
            proc = subprocess.Popen([sys.executable, str(HERE / "session_digest.py"), big[:8], "--full"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            first = proc.stdout.read(20)  # like `| head -c 20`
            proc.stdout.close()
            err = proc.stderr.read().decode()
            proc.wait()
            proc.stderr.close()
            self.assertEqual(first, b"# Session digest 9f8")
            self.assertEqual(proc.returncode, 0)
            self.assertNotIn("Traceback", err)
            self.assertNotIn("BrokenPipe", err)

    def test_help_epilog(self):
        r = run_digest(self.env, "--help")
        self.assertEqual(r.returncode, 0)
        for needle in ("common usages", "--turn 3", "--full", "--latest", "| head", "--final-only", "--subagent",
                       "--no-related"):
            self.assertIn(needle, r.stdout)
        self.assertIn("default 40000", r.stdout)

    def test_auto_notification_lines(self):
        out = run_digest(self.env, D).stdout
        self.assertIn("User turns: 2 (auto notifications collapsed: 1", out)
        line = next(l for l in out.splitlines() if l.startswith("Turn 2:"))
        self.assertTrue(line.startswith("Turn 2: auto notification — subagent completion → result: "), line)
        self.assertNotIn("Perform any necessary", out)
        self.assertNotIn("no further action", out)
        self.assertIn("→ result: The explorer finished: it found the bug in m.ts.", line)
        self.assertLessEqual(len(line.split("→ result: ")[1].split(" (jsonl")[0]), 300)
        self.assertNotIn("### Turn 2", out)
        self.assertIn("### Turn 3 ", out)  # real turns keep counting through the notification

    def test_open_signal_markers(self):
        for text in ("Not fixed yet: the overlay.", "These are not changed here.", "One item is left over for you.",
                     "I will do it later on.", "This needs a separate change.", "Open question: which env?",
                     "The owner is unknown right now.", "It needs a review first."):
            self.assertTrue(session_digest.SIGNAL_RE.search(text), text)
        self.assertFalse(session_digest.SIGNAL_RE.search("Everything shipped and passed."))

    def test_open_signals_survive_budget_and_final_message_is_scanned(self):
        out = run_digest(self.env, D).stdout
        section = out.split("## Open-signal lines")[1].split("## Final assistant message")[0]
        self.assertIn("Not fixed yet: the overlay.", section)
        self.assertNotIn("(none", section)
        self.assertNotIn("(omitted", section)
        # a tight budget still keeps the open-signal lines (the old ladder dropped them to zero)
        with tempfile.TemporaryDirectory() as tmp:
            cursor, kiro = Path(tmp) / "c", Path(tmp) / "k"
            kiro.mkdir()
            big = "9f8e7d6c-0000-4000-8000-00000000000b"
            rows = []
            for i in range(30):
                rows.append(cur_user(f"question {i} " + "word " * 300))
                rows.append(cur_asst(txt(f"answer {i} " + "text " * 400),
                                     *[tool("Shell", {"command": f"echo {j} && " + "x" * 300}) for j in range(12)]))
            rows.append(cur_asst(txt("Wrapping up. Not fixed yet: the overlay values. This needs a separate change.")))
            jl(cursor / "work-proj" / "agent-transcripts" / big / f"{big}.jsonl", rows)
            r = run_digest((cursor, kiro), big[:8], "--max-chars", "5000")
            section = r.stdout.split("## Open-signal lines")[1].split("## Final assistant message")[0]
            self.assertIn("Not fixed yet: the overlay values.", section)
            self.assertIn("truncated: yes", r.stdout)
        # "none found" and "omitted for budget" are different texts
        out = run_digest(self.env, B).stdout
        self.assertIn("## Open-signal lines\n(none found)", out)
        view = {"meta": {"uuid": "x" * 36, "source": "cursor", "working_dirs": [], "title": None, "children": [],
                         "first_timestamp": None, "last_timestamp": None, "file": "f", "bytes": 1, "file_mtime": "t",
                         "auto_notifications": 0, "compactions": 0, "empty_user_lines_skipped": 0, "user_turns": 0,
                         "is_subagent": False, "parent_id": None, "lines_skipped_oversize": 0, "lines_skipped_bad_json": 0},
                "turns": [], "markers": [], "files_touched": {"rows": [], "more": 0, "total": 0},
                "open_signals": [], "open_signals_total": 3, "final_message": "", "final_message_line": None}
        self.assertIn("## Open-signal lines\n(omitted for budget)", session_digest.render_md(view))

    def test_budget_keeps_final_text_of_turns_with_questions_or_open_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor, kiro = Path(tmp) / "c", Path(tmp) / "k"
            kiro.mkdir()
            big = "9f8e7d6c-0000-4000-8000-00000000000c"
            rows = []
            for i in range(30):
                tail = " Do you want me to deploy it?" if i == 12 else (" Not fixed yet: the overlay." if i == 14 else "")
                rows.append(cur_user(f"question {i} " + "word " * 100))
                rows.append(cur_asst(txt(f"answer {i} " + "plain filler " * 300 + tail)))
            jl(cursor / "work-proj" / "agent-transcripts" / big / f"{big}.jsonl", rows)
            r = run_digest((cursor, kiro), big[:8], "--max-chars", "6000")
            out = r.stdout
            self.assertIn("truncated: yes", out)
            for turn, phrase in ((13, "Do you want me to deploy it?"), (15, "Not fixed yet: the overlay.")):
                part = out.split(f"### Turn {turn} ")[1].split("### Turn")[0]
                self.assertIn("**Assistant (final text", part)
                self.assertIn(phrase, part)  # tail of the text survives head+tail truncation
                self.assertIn("[…]", part)
            plain = out.split("### Turn 8 ")[1].split("### Turn")[0]
            self.assertNotIn("plain filler plain filler plain filler plain filler", plain)

    def test_turn_final_only(self):
        out = run_digest(self.env, D, "--turn", "1", "--final-only").stdout
        self.assertEqual(out.splitlines()[:2], [f"Session id: {D}", "Source: cursor"])
        self.assertIn("### Turn 1 ", out)
        self.assertIn("long " * 399 + "long", out)  # user text in full
        self.assertIn("**Assistant (final text, jsonl line 3):**", out)
        self.assertIn("| row59 | " + "v" * 40 + " |", out)  # final text in full
        for gone in ("- Tools:", "- Commands", "- Files written", "## Meta", "## Files touched", "Later sessions"):
            self.assertNotIn(gone, out)
        self.assertNotIn("git -C", out)
        # Kiro: no compaction summary, no mid-turn steering, no command list
        out = run_digest(self.env, K, "--turn", "1", "--final-only").stdout
        self.assertNotIn("Compaction", out)
        self.assertNotIn("mid-turn", out)
        self.assertNotIn("npm test", out)
        self.assertIn("Working on it.", out)
        # a turn without any assistant text
        self.assertIn("**Assistant (final text):** none", run_digest(self.env, RW, "--turn", "2", "--final-only").stdout)
        data = json.loads(run_digest(self.env, D, "--turn", "1", "--final-only", "--json").stdout)
        self.assertEqual(sorted(data["turns"][0]), ["auto", "collapsed", "final", "final_line", "final_only", "lines", "n", "ts", "user"])
        self.assertEqual(sorted(data["meta"]), sorted(session_digest.HEADER_KEYS))
        r = run_digest(self.env, D, "--final-only")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--final-only needs --turn", r.stderr)

    def test_subagent_reports_in_meta(self):
        out = run_digest(self.env, A).stdout
        base = Path(self.env[0]) / "work-proj/agent-transcripts" / A / "subagents" / f"{SUB}.jsonl"
        self.assertIn("    - Final: Explored the repo, found 3 files. Leaked [REDACTED_FIGMA_TOKEN] by mistake.", out)
        self.assertIn(f"    - File: {base}", out)
        self.assertNotIn(FAKE_FIGMA, out)
        out = run_digest(self.env, K).stdout
        line = next(l for l in out.splitlines() if l.startswith("    - Final: HEADMARK"))
        self.assertLessEqual(len(line) - len("    - Final: "), 500)
        self.assertIn(" […] ", line)  # head + tail
        self.assertTrue(line.endswith("TAILMARK"))
        self.assertIn(f"    - File: {Path(self.env[1]) / (KS + '.jsonl')}", out)
        self.assertIn(f"  - [1] {KS[:8]}: Review it [parent_session_id]", out)
        data = json.loads(run_digest(self.env, K, "--json").stdout)
        kid = data["meta"]["children"][0]
        self.assertTrue(kid["final"].startswith("HEADMARK") and len(kid["final"]) <= 500)
        self.assertTrue(kid["path"].endswith(KS + ".jsonl"))
        self.assertNotIn("final_text", kid)
        # a child without assistant text says so
        self.assertIn("(no final assistant text)", session_digest.render_meta(
            {**data["meta"], "children": [{**kid, "final": ""}]}).__str__())

    def test_subagent_option_prints_full_final_text(self):
        r = run_digest(self.env, K, "--subagent", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertEqual(out.splitlines()[:2], [f"Session id: {K}", "Source: kiro"])
        self.assertNotIn("## Meta", out)
        self.assertNotIn("### Turn", out)
        self.assertIn(f"## Subagent 1 of 1 — {KS[:8]}: Review it", out)
        self.assertIn(f"- File: {Path(self.env[1]) / (KS + '.jsonl')}", out)
        self.assertIn("> HEADMARK " + "word " * 700 + "TAILMARK", out)  # whole text, nothing cut
        self.assertNotIn("[…]", out)
        out = run_digest(self.env, K, "--subagent", "all").stdout
        part = out.split("## Subagent 1 of 1")[1]
        self.assertIn("HEADMARK", part)
        self.assertIn(" […] ", part)  # cut to 3000 chars, head+tail
        self.assertLessEqual(len(part.split("> ", 1)[1].split("\n<!--")[0]), 3010)
        # cursor child, redacted, together with --turn
        out = run_digest(self.env, A, "--subagent", "1", "--turn", "3").stdout
        self.assertIn("### Turn 3 ", out)
        self.assertIn("> Explored the repo, found 3 files. Leaked [REDACTED_FIGMA_TOKEN] by mistake.", out)
        self.assertNotIn(FAKE_FIGMA, out)
        data = json.loads(run_digest(self.env, K, "--subagent", "1", "--json").stdout)
        self.assertEqual(data["subagent_reports"][0]["id"], KS)
        self.assertTrue(data["subagent_reports"][0]["final"].endswith("TAILMARK"))
        # bad values
        self.assertEqual(run_digest(self.env, K, "--subagent", "2").returncode, 2)
        self.assertEqual(run_digest(self.env, K, "--subagent", "0").returncode, 2)
        self.assertEqual(run_digest(self.env, K, "--subagent", "x").returncode, 2)
        r = run_digest(self.env, B, "--subagent", "1")  # no children
        self.assertEqual(r.returncode, 2)
        self.assertIn("no subagent children", r.stderr)

    def test_kiro_tool_output_secrets_are_reported_by_rule_without_values(self):
        out = run_digest(self.env, K).stdout
        self.assertIn("- Secret-like values seen in tool output: turn 1 (figma token, JWT) (values not shown)", out)
        for needle in (FAKE_FIGMA, FAKE_JWT, "figd_abc", "eyJhbGci"):
            self.assertNotIn(needle, out)
        self.assertEqual(out.count("Secret-like values seen"), 1)  # deduped: the figma token is in two results
        self.assertNotIn("long base64", out)  # the image payload is not flagged
        data = json.loads(run_digest(self.env, K, "--json").stdout)
        self.assertEqual(data["meta"]["tool_secrets"], [{"turn": 1, "rules": ["figma token", "JWT"]}])
        self.assertNotIn(FAKE_FIGMA, json.dumps(data))
        # sessions without matching tool output, and Cursor sessions, have no such line
        self.assertNotIn("Secret-like", run_digest(self.env, RW).stdout)
        self.assertNotIn("Secret-like", run_digest(self.env, A).stdout)
        # unit: rule names only, path-like text and placeholders do not count
        self.assertEqual(session_digest.secret_rules(f"x {FAKE_FIGMA} y"), ["figma token"])
        self.assertEqual(session_digest.secret_rules("Authorization: Bearer abcdefghij0123"), ["authorization header"])
        self.assertEqual(session_digest.secret_rules("token: <your-secret-token> and Bearer [REDACTED]"), [])
        self.assertEqual(session_digest.secret_rules("/Users/aaaa/bbbbbbbbb/cccccccccc/ddddddddd/eeeeeeeeee/fffffffff/gggggggg/hhhhhhhh"), [])

    def test_auto_notification_boilerplate_is_stripped(self):
        stock = ("Perform any necessary follow-up actions in response to the subagent completion above. If no follow-up work "
                 "is needed, no further action is required. If you mention an agent or subagent in your response, link it "
                 "with the `[Name](id)` Don't use generic label such as `[agent]`, `[worker]`, or `[subagent]`. For cloud "
                 "subagents, when the agent has edited code, link to `[Review](bc-id#changes)`. Never write A or D "
                 "literally. Don't repeat the same confirmation every time.")
        self.assertEqual(session_digest.strip_boilerplate(stock), "")
        self.assertEqual(session_digest.strip_boilerplate(stock + " Subagent Explore X done"), "Subagent Explore X done")
        self.assertEqual(session_digest.strip_boilerplate("Explore X finished. " + stock), "Explore X finished.")
        self.assertEqual(session_digest.strip_boilerplate("Briefly inform the user about the task result. Tests pass."), "Tests pass.")
        self.assertEqual(session_digest.strip_boilerplate("Perform any necessary follow-up actions in response to the "
                                                          "subagent completion above. Reviewer found 2 bugs"), "Reviewer found 2 bugs")
        with tempfile.TemporaryDirectory() as tmp:
            cursor, kiro = Path(tmp) / "c", Path(tmp) / "k"
            kiro.mkdir()
            sid = "9f8e7d6c-0000-4000-8000-0000000000d1"
            jl(cursor / "work-proj" / "agent-transcripts" / sid / f"{sid}.jsonl", [
                cur_user("start"), cur_asst(txt("launched")),
                cur_user(stock + " Explore X finished with 3 files " + "z" * 200),
                cur_asst(txt("Explore X reported 3 files.")),
                cur_user(stock), cur_asst(txt("Second one done."))])
            out = run_digest((cursor, kiro), sid[:8]).stdout
            lines = [l for l in out.splitlines() if l.startswith("Turn ") and "auto notification" in l]
            self.assertEqual(len(lines), 2)
            self.assertTrue(lines[0].startswith("Turn 2: auto notification — Explore X finished with 3 files "), lines[0])
            self.assertLessEqual(len(lines[0].split(" → ")[0]) - len("Turn 2: auto notification — "), 120)
            self.assertTrue(lines[1].startswith("Turn 3: auto notification — subagent completion → result: Second one done."), lines[1])
            self.assertNotIn("Perform any", out)

    def test_open_signals_skip_the_agents_own_narration(self):
        text = ("I'm weighing whether to deploy, which is still risky. I'll look at it later. Let me know if the test failed. "
                "I should say the overlay is not fixed yet. I need to retry, so the migration is deferred. "
                "The build failed on CI. I\u2019ll leave it, which is out of scope. Let me check the left over item. "
                "I need to ask about the pending approval.")
        with tempfile.TemporaryDirectory() as tmp:
            cursor, kiro = Path(tmp) / "c", Path(tmp) / "k"
            kiro.mkdir()
            sid = "9f8e7d6c-0000-4000-8000-0000000000d2"
            jl(cursor / "work-proj" / "agent-transcripts" / sid / f"{sid}.jsonl", [cur_user("go"), cur_asst(txt(text))])
            out = run_digest((cursor, kiro), sid[:8]).stdout
            section = out.split("## Open-signal lines")[1].split("## Final assistant message")[0]
            for kept in ("I should say the overlay is not fixed yet.", "I need to retry, so the migration is deferred.",
                         "The build failed on CI.", "I\u2019ll leave it, which is out of scope.", "Let me check the left over item."):
                self.assertIn(kept, section)
            for dropped in ("I'm weighing", "I'll look at it later", "Let me know if", "pending approval"):
                self.assertNotIn(dropped, section)

    def test_many_subagent_reports_shrink_to_fit_the_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor, kiro = Path(tmp) / "c", Path(tmp) / "k"
            kiro.mkdir()
            sid = "9f8e7d6c-0000-4000-8000-0000000000d3"
            folder = cursor / "work-proj" / "agent-transcripts" / sid
            jl(folder / f"{sid}.jsonl", [cur_user("go " + "word " * 50), cur_asst(txt("done " * 50))])
            for i in range(12):
                jl(folder / "subagents" / f"cccccc{i:02d}-0000-4000-8000-000000000000.jsonl",
                   [cur_user(f"job {i}"), cur_asst(txt(f"Report {i}: " + "finding " * 300))])
            big = run_digest((cursor, kiro), sid[:8], "--max-chars", "100000").stdout
            self.assertEqual(big.count("    - Final: Report"), 12)
            self.assertNotIn("truncated: yes", big)
            small = run_digest((cursor, kiro), sid[:8], "--max-chars", "3000")
            self.assertEqual(small.returncode, 0, small.stderr)
            self.assertIn("truncated: yes", small.stdout)
            self.assertLess(len(small.stdout), len(big))
            self.assertLess(small.stdout.count("finding finding"), big.count("finding finding"))

    def test_kiro_steering_parts_without_wrapper(self):
        parts = session_digest.steer_parts("[LIVE STEERING - New message from user]\n\nThe user sent a new message while you are "
                                           "working. Adjust.\n\nplease stop\n\nIMPORTANT: After completing your work, note it.")
        self.assertEqual(parts, [(None, "please stop")])
        parts = session_digest.steer_parts('x <user_message id="steer-9">\nhello\n</user_message> y')
        self.assertEqual(parts, [("steer-9", "hello")])


T = "12345678-aaaa-4000-8000-00000000abcd"  # target cursor parent
M1 = "22222222-aaaa-4000-8000-000000000001"  # cursor parent, mentions T, dated Nov 6
M3 = "33333333-aaaa-4000-8000-000000000003"  # cursor parent, mentions T, no <timestamp>: mtime
KM = "44444444-aaaa-4000-8000-000000000004"  # kiro session, mentions T, dated Oct 26
KT = "55555555-aaaa-4000-8000-000000000005"  # target kiro session
KC = "66666666-aaaa-4000-8000-000000000006"  # kiro subagent child of KT, mentions KT
KO = "77777777-aaaa-4000-8000-000000000007"  # kiro session mentioning KT
NOT1 = "88888888-aaaa-4000-8000-000000000008"  # mentions only the 8-char prefix of T


class RelatedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cursor, self.kiro = root / "cursor", root / "kiro"
        self.kiro.mkdir()
        c = self.cursor
        jl(c / "p1" / "agent-transcripts" / T / f"{T}.jsonl", [
            cur_user("target session"), cur_asst(txt(f"my own id is {T}"))])  # self mention: skipped
        jl(c / "p2" / "agent-transcripts" / M1 / f"{M1}.jsonl", [
            cur_user(f"Follow up on {T}, key {FAKE_FIGMA}. " + "long " * 100, ts="Friday, Nov 6, 2026, 9:00 AM (UTC+2)"),
            cur_asst(txt("ok"))])
        # a subagent of M1 also mentions T; subagent files are not scanned
        jl(c / "p2" / "agent-transcripts" / M1 / "subagents" / f"{NOT1}.jsonl", [cur_user(f"sub of M1 about {T}")])
        jl(c / "p3" / "agent-transcripts" / M3 / f"{M3}.jsonl", [
            "not json at all " + T, {"role": "user", "message": {"content": [txt("plain prompt without timestamp tag")]}}])
        jl(c / "p3" / "agent-transcripts" / NOT1 / f"{NOT1}.jsonl", [cur_user(f"only the prefix {T[:8]} here")])
        stamp = time.mktime((2026, 11, 9, 12, 0, 0, 0, 0, -1))
        os.utime(c / "p3" / "agent-transcripts" / M3 / f"{M3}.jsonl", (stamp, stamp))
        jl(self.kiro / f"{KM}.jsonl", [
            kiro_text("Prompt", [kblock("text", "kiro prompt that cites it")], meta={"timestamp": 1793000000}),
            kiro_text("AssistantMessage", [kblock("text", f"see {T}")])])
        (self.kiro / f"{KM}.json").write_text(json.dumps({"session_id": KM, "cwd": "/k/cwd-one"}))
        jl(self.kiro / f"{KT}.jsonl", [kiro_text("Prompt", [kblock("text", "kiro target")], meta={"timestamp": 1790000000})])
        (self.kiro / f"{KT}.json").write_text(json.dumps({"session_id": KT, "cwd": "/k/target"}))
        jl(self.kiro / f"{KC}.jsonl", [kiro_text("Prompt", [kblock("text", f"child of {KT}")], meta={"timestamp": 1790000100})])
        (self.kiro / f"{KC}.json").write_text(json.dumps({"session_id": KC, "cwd": "/k/target",
                                                          "session_created_reason": "subagent", "parent_session_id": KT}))
        jl(self.kiro / f"{KO}.jsonl", [kiro_text("Prompt", [kblock("text", f"look at {KT}")], meta={"timestamp": 1791000000})])
        (self.kiro / f"{KO}.json").write_text(json.dumps({"session_id": KO, "cwd": "/k/other"}))
        self.env = (self.cursor, self.kiro)

    def tearDown(self):
        self.tmp.cleanup()

    def section(self, out):
        self.assertIn("## Later sessions that mention this one", out)
        return out.split("## Later sessions that mention this one\n")[1].split("\n\n## ")[0]

    def test_related_cursor_target_lists_cursor_and_kiro_sorted_by_date(self):
        out = run_digest(self.env, T).stdout
        self.assertLess(out.index("## Meta"), out.index("## Later sessions that mention this one"))
        self.assertLess(out.index("## Later sessions that mention this one"), out.index("## Turns"))
        rows = self.section(out).splitlines()
        self.assertEqual([r.split(" — ")[0] for r in rows], [f"- {KM}", f"- {M1}", f"- {M3}"])  # Oct 26, Nov 6, Nov 9 (mtime)
        self.assertIn(f"- {KM} — kiro — /k/cwd-one — 2026-", rows[0])
        self.assertIn("UTC: kiro prompt that cites it", rows[0])
        self.assertIn(f"- {M1} — cursor — p2 — 2026-11-06 07:00 UTC: Follow up on {T}, key [REDACTED_FIGMA_TOKEN].", rows[1])
        self.assertIn("— cursor — p3 — 2026-11-09", rows[2])
        self.assertIn("UTC (mtime): plain prompt without timestamp tag", rows[2])
        body = rows[1].split("UTC: ", 1)[1]
        self.assertLessEqual(len(body), 160)
        self.assertIn("[…]", body)
        text = "\n".join(rows)
        self.assertNotIn(FAKE_FIGMA, text)
        self.assertNotIn(NOT1, text)  # prefix-only mention and M1's subagent are not hits
        self.assertNotIn(f"- {T}", text)  # the session itself is skipped
        self.assertNotIn("+", text.replace("+02", ""))  # no "more" line for 3 hits

    def test_related_kiro_target_skips_own_subagents(self):
        rows = self.section(run_digest(self.env, KT).stdout).splitlines()
        self.assertEqual([r.split(" — ")[0] for r in rows], [f"- {KO}"])
        self.assertIn("— kiro — /k/other —", rows[0])
        self.assertNotIn(KC, "\n".join(rows))

    def test_related_none_found_and_no_related_flag_and_drill_modes(self):
        self.assertEqual(self.section(run_digest(self.env, M3).stdout), "(none found)")
        self.assertEqual(self.section(run_digest(self.env, KM).stdout), "(none found)")
        for args in (("--no-related",), ("--turn", "1"), ("--subagent", "all")):
            out = run_digest(self.env, T, *args).stdout
            self.assertNotIn("Later sessions that mention", out, args)
        out = run_digest(self.env, T, "--no-related").stdout
        self.assertIn("## Meta", out)
        data = json.loads(run_digest(self.env, T, "--json").stdout)
        self.assertEqual([h["uuid"] for h in data["meta"]["related"]], [KM, M1, M3])
        self.assertEqual(data["meta"]["related_total"], 3)
        self.assertEqual(sorted(data["meta"]["related"][0]), ["date", "first_user", "source", "uuid", "where"])
        self.assertNotIn("related", json.loads(run_digest(self.env, T, "--json", "--no-related").stdout)["meta"])

    def test_related_is_capped_at_ten_with_a_more_line(self):
        for i in range(12):
            sid = f"99999999-aaaa-4000-8000-{i:012d}"
            jl(self.cursor / "p4" / "agent-transcripts" / sid / f"{sid}.jsonl", [
                cur_user(f"mention {i} of {T}", ts=f"Thursday, Oct 29, 2026, 10:{i:02d} AM (UTC+0)")])
        rows = self.section(run_digest(self.env, T).stdout).splitlines()
        self.assertEqual(len(rows), 11)
        self.assertTrue(rows[0].startswith(f"- {KM} — kiro"))  # Oct 26, before the Oct 29 mentions
        self.assertTrue(rows[1].startswith("- 99999999-aaaa-4000-8000-000000000000 — cursor — p4 — 2026-10-29 10:00 UTC"))
        self.assertEqual(rows[-1], "- +5 later matches not shown (earliest 10 listed)")  # 15 hits in total

    def test_cursor_timestamp_parsing(self):
        dt = session_digest.parse_cursor_ts("Thursday, Nov 5, 2026, 11:11 AM (UTC+2)")
        self.assertEqual(dt.isoformat(), "2026-11-05T11:11:00+02:00")
        self.assertEqual(session_digest.parse_cursor_ts("Friday, Nov 6, 2026, 12:30 PM (UTC-5)").isoformat(), "2026-11-06T12:30:00-05:00")
        self.assertEqual(session_digest.parse_cursor_ts("Friday, Nov 6, 2026, 1:00 AM").isoformat(), "2026-11-06T01:00:00+00:00")
        self.assertIsNone(session_digest.parse_cursor_ts("yesterday"))
        self.assertIsNone(session_digest.parse_cursor_ts(None))

    def test_mentions_is_a_plain_byte_search(self):
        path = Path(self.tmp.name) / "x.jsonl"
        path.write_bytes(b"{broken json\n\xff\xfe binary " + T.encode() + b" tail\n")
        self.assertTrue(session_digest.mentions(path, T.encode()))
        self.assertFalse(session_digest.mentions(path, T[:-1].encode() + b"z"))
        self.assertFalse(session_digest.mentions(Path(self.tmp.name) / "missing.jsonl", b"x"))


GOOD = """# Debrief

## Bottom line
**Partly done.** The export works, the import does not yet. Pick a store to unblock it.

## How it works
The export reads the file, the import writes it back.

```mermaid
flowchart TD
  A[Start] --> B[Export]
  B --> C[Import]
```

## Decisions you own
### Pick a store
**Recommendation:** use the file store.
**If you do nothing:** the import stays broken.
**Do it if:** you want the import this week.
**Skip it if:** the import is not needed yet.

## Left undone on purpose
| Item | Status now | Agent's reason |
|---|---|---|
| Import retry | Open | Out of scope for this change |

Do it if: imports fail often.
Skip it if: imports are rare.

## Status board
| Item | State |
|---|---|
| Export | ✅ verified |
| Import | ⚠️ reported by the agent |

## What changed
| File | Kind |
|---|---|
| scripts/a.py | introduced by this work |

## Questions you would ask next
**What is left?** The import.
**Is the export safe to run twice?** Yes.
**Who owns the store?** Not known.

## Words used here
- **Digest**: a short summary.

## Say it to your lead
We shipped half of it.

## Dig deeper
See the session file.
"""

CARD_BLOCK = ("### Pick a store\n**Recommendation:** use the file store.\n**If you do nothing:** the import stays broken.\n"
              "**Do it if:** you want the import this week.\n**Skip it if:** the import is not needed yet.")
UNDONE_BLOCK = ("| Item | Status now | Agent's reason |\n|---|---|---|\n"
                "| Import retry | Open | Out of scope for this change |\n\n"
                "Do it if: imports fail often.\nSkip it if: imports are rare.")
CHANGED_BLOCK = "## What changed\n| File | Kind |\n|---|---|\n| scripts/a.py | introduced by this work |\n\n"
LEAD_BLOCK = "## Say it to your lead\nWe shipped half of it.\n\n"
STATUS_BLOCK = "## Status board\n| Item | State |\n|---|---|\n| Export | ✅ verified |\n| Import | ⚠️ reported by the agent |\n\n"
WORDS_BLOCK = "## Words used here\n- **Digest**: a short summary.\n\n"


def errors_of(text):
    return [m for _l, lvl, m in check_debrief.check(text) if lvl == "ERROR"]


def warns_of(text):
    return [m for _l, lvl, m in check_debrief.check(text) if lvl == "WARN"]


def with_bottom(text):
    """GOOD with the Bottom line body replaced."""
    return GOOD.replace("**Partly done.** The export works, the import does not yet. Pick a store to unblock it.", text)


def card(i):
    return (f"### Card {i}\n**Recommendation:** do {i}.\n**If you do nothing:** it waits.\n"
            f"**Do it if:** you care.\n**Skip it if:** you do not.\n\n")


def run_cli(text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(text)
    try:
        return subprocess.run([sys.executable, str(HERE / "check_debrief.py"), fh.name], capture_output=True, text=True)
    finally:
        os.unlink(fh.name)


class CheckerTests(unittest.TestCase):
    def test_good_passes_via_cli_without_warnings(self):
        r = run_cli(GOOD)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.strip().splitlines(), ["OK"])
        self.assertEqual(check_debrief.check(GOOD), [])

    def test_cli_failure_exit_1(self):
        r = run_cli(GOOD.replace("## Dig deeper", "## Other"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERROR 1: missing required section '## Dig deeper'", r.stdout)
        self.assertRegex(r.stdout.strip().splitlines()[-1], r"^FAIL \(\d+ errors\)$")

    def test_missing_required_section(self):
        for name in check_debrief.REQUIRED:
            errs = errors_of(GOOD.replace(f"## {name}\n", "## Renamed\n"))
            self.assertTrue(any(f"missing required section '## {name}'" in e for e in errs), (name, errs))

    def test_required_out_of_order(self):
        swapped = GOOD.replace("## How it works", "## TMP").replace("## Decisions you own", "## How it works").replace("## TMP", "## Decisions you own")
        self.assertTrue(any("out of order" in e for e in errors_of(swapped)))
        late = GOOD.replace("## Left undone on purpose", "## TMP").replace("## Questions you would ask next", "## Left undone on purpose").replace("## TMP", "## Questions you would ask next")
        self.assertTrue(any("out of order" in e for e in errors_of(late)))
        # the old required sections are optional now: dropping them is fine
        self.assertEqual(errors_of(GOOD.replace(CHANGED_BLOCK, "").replace(LEAD_BLOCK, "")), [])

    def test_optional_sections_do_not_break_order_and_may_sit_anywhere_in_the_window(self):
        self.assertFalse(errors_of(GOOD.replace(STATUS_BLOCK, "")))
        self.assertFalse(errors_of(GOOD.replace(WORDS_BLOCK, "")))
        self.assertFalse(errors_of(GOOD.replace(STATUS_BLOCK, "").replace(WORDS_BLOCK, "")))
        # Words used here right after Left undone, Status board right before Dig deeper
        moved = GOOD.replace(STATUS_BLOCK, "").replace(WORDS_BLOCK, "")
        moved = moved.replace("## What changed", WORDS_BLOCK + "## What changed").replace("## Dig deeper", STATUS_BLOCK + "## Dig deeper")
        self.assertEqual(errors_of(moved), [])
        # both between two required sections, in either order
        both = GOOD.replace(STATUS_BLOCK, "").replace(WORDS_BLOCK, "").replace("## Say it to your lead", WORDS_BLOCK + STATUS_BLOCK + "## Say it to your lead")
        self.assertEqual(errors_of(both), [])
        # What changed and Say it to your lead are optional too and may sit anywhere in the window, in any order
        stripped = GOOD.replace(CHANGED_BLOCK, "").replace(LEAD_BLOCK, "").replace(STATUS_BLOCK, "").replace(WORDS_BLOCK, "")
        shuffled = stripped.replace("## Questions you would ask next", LEAD_BLOCK + "## Questions you would ask next") \
                           .replace("## Dig deeper", CHANGED_BLOCK + WORDS_BLOCK + "## Dig deeper")
        self.assertEqual(errors_of(shuffled), [])
        self.assertEqual(warns_of(shuffled), [])
        self.assertEqual(errors_of(stripped), [])

    def test_optional_sections_outside_the_window_are_errors(self):
        before = GOOD.replace(STATUS_BLOCK, "").replace("## How it works", STATUS_BLOCK + "## How it works")
        self.assertTrue(any("Status board" in e and "after '## Left undone on purpose'" in e for e in errors_of(before)))
        after = GOOD.replace(WORDS_BLOCK, "") + "\n" + WORDS_BLOCK
        self.assertTrue(any("Words used here" in e and "before '## Dig deeper'" in e for e in errors_of(after)))
        for block, name in ((CHANGED_BLOCK, "What changed"), (LEAD_BLOCK, "Say it to your lead")):
            early = GOOD.replace(block, "").replace("## How it works", block + "## How it works")
            self.assertTrue(any(name in e and "after '## Left undone on purpose'" in e for e in errors_of(early)), name)
            late = GOOD.replace(block, "") + "\n" + block
            self.assertTrue(any(name in e and "before '## Dig deeper'" in e for e in errors_of(late)), name)
        # a misplaced optional section does not also trigger a required-order error
        self.assertFalse(any(e.startswith("section out of order: '## Left") or "missing" in e for e in errors_of(before)))

    def test_your_answers_section_is_optional_and_last(self):
        self.assertFalse(errors_of(GOOD + "\n## Your answers\n- Q1: yes, use the file store.\n"))
        early = GOOD.replace("## Dig deeper", "## Your answers\n- Q1: yes\n\n## Dig deeper")
        self.assertTrue(any("Your answers" in e and "after '## Dig deeper'" in e for e in errors_of(early)))
        leak = errors_of(GOOD + f"\n## Your answers\n- key {FAKE_FIGMA}\n")
        self.assertTrue(any("figma token" in e for e in leak))

    def test_unknown_h2_is_a_warning_not_an_error(self):
        text = GOOD.replace("## Say it to your lead", "## Appendix\nextra notes\n\n## Say it to your lead")
        self.assertEqual(errors_of(text), [])
        self.assertTrue(any("unexpected section '## Appendix'" in w for w in warns_of(text)))

    def test_secrets(self):
        for secret, rule in ((FAKE_FIGMA, "figma token"), (FAKE_JWT, "JWT"),
                             ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123", "bearer token"),
                             ("password=hunter2hunter2", "password assignment"),
                             ("AKIA" + "B" * 16, "AWS"), ("ghp_" + "c" * 36, "GitHub"),
                             ("x" + "QUJD" * 20, "base64")):
            errs = errors_of(GOOD + f"\nleak {secret}\n")
            self.assertTrue(any(rule in e for e in errs), (rule, errs))
            self.assertFalse(any(secret in e for e in errs))
        results = check_debrief.check(GOOD + f"\nleak {FAKE_FIGMA}\n")
        self.assertFalse(any(FAKE_FIGMA in m for _l, _v, m in results))

    def test_bottom_line_word_limit(self):
        self.assertFalse(errors_of(with_bottom("w " * 69 + "end.")))  # 70 words
        errs = errors_of(with_bottom("w " * 70 + "end."))  # 71 words
        self.assertTrue(any("71 words (max 70)" in e for e in errs), errs)

    def test_bottom_line_sentence_limit(self):
        self.assertFalse(errors_of(with_bottom("One. Two? Three!")))
        errs = errors_of(with_bottom("One. Two? Three! Four."))
        self.assertTrue(any("4 sentences (max 3)" in e for e in errs), errs)
        # enders inside backticks and inside numbers do not count; the last ender may end the text
        self.assertFalse(errors_of(with_bottom("It took 1.5 hours. Run `a. b. c. d.` to see it. Done.")))
        self.assertFalse(errors_of(with_bottom("**Done.** Version 2.0.1 shipped")))

    def test_bottom_line_hash_and_term_warnings(self):
        warns = warns_of(with_bottom("Fixed in a1b2c3d4. Digest ok."))
        self.assertTrue(any("commit-hash-like" in w for w in warns), warns)
        self.assertTrue(any("commit-hash-like" in w for w in warns_of(with_bottom("Fixed in `9f8e7d6c5b4a`."))))
        for harmless in ("deadbeef", "1234567", "abcdefg", "Build 20261105 finished."):
            self.assertFalse(any("commit-hash-like" in w for w in warns_of(with_bottom(harmless))), harmless)
        self.assertFalse(any("commit-hash-like" in w for w in warns_of(GOOD)))

    def test_bottom_line_backticked_terms_need_a_gloss(self):
        text = with_bottom("The `digest` works, `src/a.py` and `x.y` are skipped, `Mystery` is open.")
        warns = [w for w in warns_of(text) if "Bottom line term" in w]
        self.assertEqual(warns, ["Bottom line term `Mystery` is not explained in '## Words used here' or inline"])
        self.assertFalse([w for w in warns_of(GOOD) if "Bottom line term" in w])
        # warns even without a glossary section
        self.assertTrue(any("`Mystery`" in w for w in warns_of(text.replace(WORDS_BLOCK, ""))))
        # inline gloss in a later line, three accepted forms
        for gloss in ("`Mystery` (the unknown owner) is tracked.", "**`Mystery`** — the unknown owner.", "`Mystery`: the unknown owner."):
            glossed = text.replace("## Say it to your lead\n", "## Say it to your lead\n" + gloss + "\n")
            self.assertFalse([w for w in warns_of(glossed) if "Bottom line term" in w], gloss)
        too_far = text.replace("## Say it to your lead\n", "## Say it to your lead\n`Mystery` " + "x" * 90 + " (late)\n")
        self.assertTrue(any("`Mystery`" in w for w in warns_of(too_far)))
        secret = with_bottom(f"The `{FAKE_FIGMA}` works")
        self.assertFalse(any(FAKE_FIGMA in m for _l, _v, m in check_debrief.check(secret)))
        line = next(l for l, lvl, m in check_debrief.check(text) if "Mystery" in m)
        self.assertEqual(text.splitlines()[line - 1].count("`Mystery`"), 1)  # points at the Bottom line text

    def test_how_it_works_needs_mermaid(self):
        self.assertTrue(any("How it works has no ```mermaid" in e for e in errors_of(GOOD.replace("```mermaid", "```text"))))
        self.assertTrue(any("mermaid" in e for e in errors_of(GOOD.replace("```mermaid\nflowchart TD\n  A[Start] --> B[Export]\n  B --> C[Import]\n```", "no diagram"))))
        # a mermaid block in another section does not satisfy the rule
        moved = GOOD.replace("```mermaid", "```text") .replace("## Say it to your lead\n", "## Say it to your lead\n```mermaid\nflowchart TD\n  A --> B\n```\n")
        self.assertTrue(any("How it works has no" in e for e in errors_of(moved)))

    def test_how_it_works_warnings(self):
        def chain(n):
            return "\n".join(f"  N{i}[Node {i}] --> N{i + 1}[Node {i + 1}]" for i in range(n))
        base = "  A[Start] --> B[Export]\n  B --> C[Import]"
        self.assertFalse([w for w in warns_of(GOOD.replace(base, chain(11))) if "mermaid" in w])  # 12 nodes
        many = GOOD.replace(base, chain(30))
        self.assertTrue(any("mermaid block has about 31 nodes (max 12)" in w for w in warns_of(many)))
        self.assertEqual(errors_of(many), [])
        prose = "The export reads the file, the import writes it back."
        self.assertFalse([w for w in warns_of(GOOD.replace(prose, "w " * 140)) if "How it works has" in w])
        self.assertTrue(any("How it works has 141 words" in w for w in warns_of(GOOD.replace(prose, "w " * 141))))
        # diagram text is not prose
        big_diagram = GOOD.replace(base, base + "\n  %% " + "w " * 300)
        self.assertFalse([w for w in warns_of(big_diagram) if "How it works has" in w])

    def test_card_error_must_start_a_line_and_names_the_card(self):
        inline = GOOD.replace("**Recommendation:** use the file store.", "I think so. **Recommendation:** use the file store.")
        errs = [e for e in errors_of(inline) if "Recommendation" in e]
        self.assertEqual(len(errs), 1, errs)
        self.assertIn("must start a line", errs[0])
        self.assertIn("'Pick a store'", errs[0])
        self.assertIn("inside a line", errs[0])

    def test_each_card_label_is_required(self):
        for label in ("Recommendation", "If you do nothing", "Do it if", "Skip it if"):
            errs = errors_of(GOOD.replace(f"**{label}:**", "Other:"))
            self.assertTrue(any("must start a line" in e and "'Pick a store'" in e and label in e for e in errs), (label, errs))
        # Do it if and Skip it if are both required, not either/or
        only_do = errors_of(GOOD.replace("**Skip it if:** the import is not needed yet.", ""))
        self.assertEqual(len([e for e in only_do if "decision card" in e]), 1)
        # a second card is checked on its own
        two = GOOD.replace(CARD_BLOCK, CARD_BLOCK + "\n\n### Second one\n**Recommendation:** go.\n")
        errs = errors_of(two)
        self.assertTrue(any("'Second one'" in e and "If you do nothing" in e for e in errs))
        self.assertFalse(any("'Pick a store'" in e for e in errs))

    def test_no_cards_needs_no_decisions_text(self):
        no_cards = GOOD.replace(CARD_BLOCK, "Just FYI.")
        self.assertTrue(any("No decisions" in e for e in errors_of(no_cards)))
        self.assertFalse(errors_of(no_cards.replace("Just FYI.", "No decisions needed from you.")))
        self.assertFalse(errors_of(no_cards.replace("Just FYI.", "NO DECISIONS this time.")))

    def test_more_than_four_cards_warns(self):
        four = GOOD.replace(CARD_BLOCK, "".join(card(i) for i in range(4)))
        self.assertFalse([w for w in warns_of(four) if "cards" in w])
        five = GOOD.replace(CARD_BLOCK, "".join(card(i) for i in range(5)))
        self.assertTrue(any("5 cards (max 4)" in w for w in warns_of(five)))
        self.assertEqual(errors_of(five), [])

    def test_left_undone_needs_table_or_nothing_text(self):
        self.assertEqual(errors_of(GOOD), [])
        nothing = GOOD.replace(UNDONE_BLOCK, "Nothing was left undone.")
        self.assertEqual(errors_of(nothing), [])
        self.assertEqual(warns_of(nothing), [])
        self.assertEqual(errors_of(GOOD.replace(UNDONE_BLOCK, "NOTHING WAS LEFT UNDONE")), [])
        empty = errors_of(GOOD.replace(UNDONE_BLOCK, "Some things were skipped."))
        self.assertTrue(any("Left undone on purpose needs a table" in e for e in empty), empty)
        self.assertIn("Status now", empty[0])
        for col in ("Item", "Status now", "Agent's reason"):
            missing = errors_of(GOOD.replace(col, "Other", 1) if col != "Item" else GOOD.replace("| Item | Status now", "| Thing | Status now"))
            self.assertTrue(any("Left undone on purpose needs a table" in e for e in missing), (col, missing))
        # the old four-column table (Do it if / Skip it if as columns, no Status now) is no longer accepted
        old = GOOD.replace(UNDONE_BLOCK, "| Item | Agent's reason | Do it if | Skip it if |\n|---|---|---|---|\n| Import retry | Out of scope | Often | Rare |")
        self.assertTrue(any("Left undone on purpose needs a table" in e for e in errors_of(old)))
        # case-insensitive columns, curly apostrophe, any order
        loose = GOOD.replace("| Item | Status now | Agent's reason |", "| AGENT\u2019s reason | item | STATUS now |") \
                    .replace("| Import retry | Open | Out of scope for this change |", "| Out of scope | Import retry | Open |")
        self.assertEqual(errors_of(loose), [])

    def test_left_undone_column_and_open_row_warnings(self):
        four = GOOD.replace("| Item | Status now | Agent's reason |\n|---|---|---|\n| Import retry | Open | Out of scope for this change |",
                            "| Item | Status now | Agent's reason | Size |\n|---|---|---|---|\n| Import retry | Open | Out of scope | S |")
        self.assertEqual(warns_of(four), [])
        five = four.replace("| Size |", "| Size | Owner |").replace("|---|---|---|---|", "|---|---|---|---|---|").replace("| S |", "| S | me |")
        w = warns_of(five)
        self.assertEqual(errors_of(five), [])
        self.assertEqual([x for x in w if "Left undone" in x], ["Left undone table has 5 columns (max 4)"])
        # an open row needs Do it if and Skip it if somewhere in the section (case-insensitive)
        no_lines = GOOD.replace("\n\nDo it if: imports fail often.\nSkip it if: imports are rare.", "")
        self.assertEqual(errors_of(no_lines), [])
        self.assertEqual([x for x in warns_of(no_lines) if "open item" in x],
                         ["Left undone has an open item but no 'Do it if' and 'Skip it if' lines"])
        only_do = GOOD.replace("Skip it if: imports are rare.", "")
        self.assertTrue(any("open item" in x for x in warns_of(only_do)))
        self.assertFalse([x for x in warns_of(GOOD.replace("Do it if: imports", "DO IT IF imports").replace("Skip it if: imports", "SKIP IT IF imports")) if "open item" in x])
        # open is matched case-insensitively inside the Status now cell
        self.assertTrue(any("open item" in x for x in warns_of(no_lines.replace("| Open |", "| still OPEN |"))))
        # no open row: no lines needed
        closed = no_lines.replace("| Open |", "| Dropped |")
        self.assertFalse([x for x in warns_of(closed) if "open item" in x])
        # "open" in another column does not count
        other = no_lines.replace("| Open | Out of scope for this change |", "| Dropped | Open question for later |")
        self.assertFalse([x for x in warns_of(other) if "open item" in x])

    def test_any_table_over_five_columns_warns(self):
        six = GOOD.replace("| File | Kind |\n|---|---|\n| scripts/a.py | introduced by this work |",
                           "| File | Kind | A | B | C | D |\n|---|---|---|---|---|---|\n| scripts/a.py | introduced by this work | 1 | 2 | 3 | 4 |")
        w = [x for x in warns_of(six) if "columns" in x]
        self.assertEqual(w, ["table has 6 columns (max 5)"])
        line = next(l for l, lvl, m in check_debrief.check(six) if "columns" in m)
        self.assertTrue(six.splitlines()[line - 1].startswith("| File | Kind | A"))
        five = six.replace("| C | D |", "| C |").replace("|---|---|---|---|---|---|", "|---|---|---|---|---|").replace("| 3 | 4 |", "| 3 |")
        self.assertFalse([x for x in warns_of(five) if "columns" in x])

    def test_line_count_warning(self):
        padded = GOOD.replace("## Dig deeper\nSee the session file.\n", "## Dig deeper\n" + "\n".join(f"- file {i}" for i in range(90)))
        n = sum(1 for l in padded.splitlines() if l.strip())
        self.assertGreater(n, 110)
        self.assertEqual([x for x in warns_of(padded) if "non-empty lines" in x], [f"file has {n} non-empty lines (max 110)"])
        exact = GOOD.replace("## Dig deeper\nSee the session file.\n", "## Dig deeper\n" + "\n".join(f"- f{i}" for i in range(111 - sum(1 for l in GOOD.splitlines() if l.strip()))))
        self.assertEqual(sum(1 for l in exact.splitlines() if l.strip()), 110)
        self.assertFalse([x for x in warns_of(exact) if "non-empty lines" in x])
        # blank lines do not count
        self.assertFalse([x for x in warns_of(GOOD + "\n" * 200) if "non-empty lines" in x])

    def test_what_changed_warnings(self):
        self.assertFalse([w for w in warns_of(GOOD) if "What changed" in w])
        no_table = GOOD.replace("| File | Kind |\n|---|---|\n| scripts/a.py | introduced by this work |", "- scripts/a.py introduced here")
        w = [x for x in warns_of(no_table) if "What changed" in x]
        self.assertEqual(w, ["What changed has no table"])
        no_words = GOOD.replace("introduced by this work", "new file")
        w = [x for x in warns_of(no_words) if "What changed" in x]
        self.assertEqual(len(w), 1)
        self.assertIn("none of", w[0])
        for word in ("pre-existing", "extra", "required"):
            self.assertFalse([x for x in warns_of(GOOD.replace("introduced", word)) if "What changed" in x], word)
        # the section is optional: absent means no error and no warning about it
        absent = GOOD.replace(CHANGED_BLOCK, "")
        self.assertEqual(errors_of(absent), [])
        self.assertFalse([x for x in warns_of(absent) if "What changed" in x])

    def test_question_count_warning(self):
        q = "**What is left?** The import.\n**Is the export safe to run twice?** Yes.\n**Who owns the store?** Not known."
        self.assertIn(q, GOOD)
        two = [w for w in warns_of(GOOD.replace("\n**Who owns the store?** Not known.", "")) if "Questions" in w]
        self.assertEqual(len(two), 1)
        self.assertIn("2 bold question lines", two[0])
        eight = GOOD.replace(q, "\n".join(f"**Question {i}?** a" for i in range(8)))
        self.assertFalse([w for w in warns_of(eight) if "Questions" in w])
        nine = GOOD.replace(q, "\n".join(f"- **Question {i}?** a" for i in range(9)))
        self.assertTrue(any("9 bold question lines" in w for w in warns_of(nine)))
        plain = GOOD.replace(q, "\n".join(f"- Question {i}?" for i in range(4)))
        self.assertTrue(any("0 bold question lines" in w for w in warns_of(plain)))

    def test_word_budget_scales_with_cards_and_skips_mermaid(self):
        prose, _blocks = check_debrief.split_mermaid(GOOD.splitlines())
        base = len(" ".join(prose).split())

        def over(text):
            return [w for w in warns_of(text) if "words (target" in w]
        # 1 card -> 900 + 140 = 1040
        self.assertFalse(over(GOOD + "w " * (1040 - base)))
        hit = over(GOOD + "w " * (1050 - base))
        self.assertEqual(len(hit), 1)
        self.assertIn("target max 1040 = 900 + 140 x 1 decision cards, cap 1600", hit[0])
        none = GOOD.replace(CARD_BLOCK, "No decisions needed from you.")
        self.assertIn("target max 900", over(none + "w " * 1000)[0])
        three = GOOD.replace(CARD_BLOCK, "".join(card(i) for i in range(3)))
        self.assertIn("target max 1320", over(three + "w " * 1500)[0])
        many = GOOD.replace(CARD_BLOCK, "".join(card(i) for i in range(12)))
        self.assertIn("cap 1600", over(many + "w " * 2000)[0])
        self.assertIn("target max 1600", over(many + "w " * 2000)[0])
        self.assertFalse(over(many + "w " * 400))
        # words inside a mermaid block are not counted
        diagram = GOOD.replace("  B --> C[Import]", "  B --> C[Import]\n  %% " + "w " * 3000)
        self.assertFalse(over(diagram))

    def test_review_opening_warnings(self):
        self.assertFalse([w for w in warns_of(GOOD) if w.startswith("review ")])
        titled = GOOD.replace("# Debrief", "# Debrief: Rovo review of the button PR", 1)
        hit = [w for w in warns_of(titled) if "review bottom line" in w]
        self.assertEqual(len(hit), 1)
        bare = titled.replace("introduced by this work", "new file").replace("scripts/a.py", "the helper")
        msgs = warns_of(bare)
        self.assertTrue(any("never says introduced" in w for w in msgs))
        self.assertTrue(any("cites no source file" in w for w in msgs))

    def test_other_warnings(self):
        self.assertFalse(warns_of(GOOD))
        cell = GOOD.replace("| Export | ✅ verified |", "| Export | ✅ verified " + "w " * 31 + "|")
        self.assertTrue(any("table cell" in w for w in warns_of(cell)))
        glossary = GOOD.replace("- **Digest**: a short summary.", "\n".join(f"- **T{i}**: x" for i in range(13)))
        self.assertTrue(any("Words used here" in w for w in warns_of(glossary)))
        self.assertTrue(any("coverage" in w for w in warns_of(GOOD + "\n42 transcripts scanned, 3 files matched\n")))

    def test_status_board_words_and_marks_only_when_present(self):
        checked = GOOD.replace("✅ verified", "✅ checked").replace("⚠️ reported by the agent", "⚠️ not checked")
        self.assertFalse(warns_of(checked))
        no_words = GOOD.replace("verified", "ok").replace("reported by the agent", "fine")
        self.assertTrue(any("none of 'verified'" in w for w in warns_of(no_words)))
        no_marks = GOOD.replace("✅ ", "").replace("⚠️ ", "")
        w = warns_of(no_marks)
        self.assertTrue(any("no status marks" in x for x in w), w)
        self.assertFalse(any("none of 'verified'" in x for x in w))
        for mark in ("❌", "❓", "⚠️", "✅"):
            only = GOOD.replace("✅ ", "").replace("⚠️ ", mark + " ")
            self.assertFalse(any("no status marks" in x for x in warns_of(only)), mark)
        absent = GOOD.replace(STATUS_BLOCK, "")
        self.assertFalse([x for x in warns_of(absent) if "Status board" in x])


if __name__ == "__main__":
    unittest.main()
