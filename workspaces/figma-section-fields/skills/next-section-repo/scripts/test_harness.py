#!/usr/bin/env python3
"""Fixture checks for harness.py. No real repo, no network; subprocess is mocked except one local git worktree test."""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness  # noqa: E402


def write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def install(node_modules: Path, packages=("react", "react-dom", "styled-components", "esbuild")) -> Path:
    for name in packages:
        write(node_modules / name / "package.json", json.dumps({"name": name}))
    if "esbuild" in packages:
        write(node_modules / "esbuild" / "lib" / "main.js")
    return node_modules


def ora_like(root: Path, with_node_modules: bool = True) -> Path:
    code = root / "code"
    write(code / "package.json", "{}")
    write(code / "jsconfig.json", '{\n  "compilerOptions": {\n    // comment\n    "baseUrl": "./app",\n    "paths": { "@/*": ["components/*"], },\n  }\n}\n')
    app = code / "app"
    write(app / "styles" / "theme" / "index.js", "export default { bps: {} };\n")
    write(app / "components" / "Sections" / "Hero" / "ClientHero.js", "export default () => null;\n")
    if with_node_modules:
        install(code / "node_modules")
    return app


def args(**overrides) -> list[str]:
    values = {"--repo": None, "--folder": "Hero", "--out-dir": None, **overrides}
    out = []
    for key, value in values.items():
        if value is not None:
            out += [key, str(value)]
    return out


def tree(path: Path) -> dict[str, float]:
    return {str(p.relative_to(path)): p.stat().st_mtime_ns for p in path.rglob("*")}


class FakeRunner:
    def __init__(self, bundle_returncode: int = 0, stderr: str = "", porcelain: str = "", toplevel: str = ""):
        self.calls: list[tuple[list[str], dict]] = []
        self.bundle_returncode = bundle_returncode
        self.stderr = stderr
        self.porcelain = porcelain
        self.toplevel = toplevel
        self.config: dict | None = None

    def __call__(self, argv, **kwargs):
        assert isinstance(argv, list), "subprocess must get an argument list"
        assert not kwargs.get("shell"), "subprocess must not use a shell"
        self.calls.append((argv, kwargs))
        if argv[0] == "git":
            out = self.toplevel + "\n" if "rev-parse" in argv else self.porcelain
            return subprocess.CompletedProcess(argv, 0 if out.strip() else 128, out, "")
        self.config = json.loads(kwargs["input"])
        if self.bundle_returncode:
            return subprocess.CompletedProcess(argv, self.bundle_returncode, "", self.stderr)
        Path(self.config["outfile"]).write_text("/* bundle */\n", encoding="utf-8")
        hit = {"module": "next/font/local", "importers": ["/x/styles/fonts/index.js"]}
        return subprocess.CompletedProcess(argv, 0, json.dumps({"ok": True, "stubsHit": [hit], "warnings": []}) + "\n", "")


class HarnessCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        which = mock.patch.object(harness.shutil, "which", return_value="/usr/bin/node")
        which.start()
        self.addCleanup(which.stop)

    def run_harness(self, argv: list[str], runner=None):
        runner = runner or FakeRunner()
        return harness.harness(harness.parse_args(argv), runner), runner


class ArgumentTests(HarnessCase):
    def expect_usage(self, argv: list[str], fragment: str):
        runner = FakeRunner()
        with self.assertRaises(harness.HarnessError) as caught:
            self.run_harness(argv, runner)
        self.assertEqual(caught.exception.exit_code, 1)
        self.assertIn(fragment, caught.exception.message)
        self.assertEqual(runner.calls, [])

    def test_missing_required_argument_exits_1_with_json(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            harness.parse_args(["--folder", "Hero"])
        self.assertEqual(caught.exception.code, 1)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["error"]["code"], "USAGE")

    def test_bad_inputs_are_usage_errors(self):
        app = ora_like(self.tmp)
        out = self.tmp / "out"
        self.expect_usage(args(**{"--repo": app, "--out-dir": out, "--folder": "../Hero"}), "--folder")
        self.expect_usage(args(**{"--repo": self.tmp, "--out-dir": out}), "components/")
        self.expect_usage(args(**{"--repo": app, "--out-dir": out, "--folder": "Nope"}), "ClientNope.js")
        self.expect_usage(args(**{"--repo": app, "--out-dir": out, "--section-path": "../../elsewhere"}), "inside --repo")
        self.expect_usage(args(**{"--repo": app, "--out-dir": app.parent / "tmp-out"}), "inside the repo")
        self.expect_usage(args(**{"--repo": app, "--out-dir": out, "--props": self.tmp / "missing.json"}), "--props")
        self.expect_usage(args(**{"--repo": app, "--out-dir": out, "--props": write(self.tmp / "list.json", "[1]")}), "one JSON object")
        self.assertFalse(out.exists())

    def test_section_path_override(self):
        app = ora_like(self.tmp)
        write(app / "components" / "Other" / "Hero" / "ClientHero.js", "export default () => null;\n")
        result, runner = self.run_harness(args(**{"--repo": app, "--out-dir": self.tmp / "out", "--section-path": "components/Other/Hero"}))
        self.assertTrue(result["ok"])
        self.assertIn(str(app / "components" / "Other" / "Hero" / "ClientHero.js"), runner.config["entry"]["contents"])


class NodeModulesTests(HarnessCase):
    def test_worktree_node_modules_in_a_parent_wins(self):
        app = ora_like(self.tmp)
        found, source = harness.find_node_modules(harness.package_root(app), FakeRunner())
        self.assertEqual((found, source), (app.parent / "node_modules", "worktree"))

    def test_incomplete_node_modules_is_skipped(self):
        app = ora_like(self.tmp, with_node_modules=False)
        install(app.parent / "node_modules", ("react", "react-dom"))
        with self.assertRaises(harness.HarnessError) as caught:
            harness.find_node_modules(app.parent, FakeRunner())
        self.assertEqual(caught.exception.exit_code, 4)

    def test_main_checkout_from_git_worktree_list(self):
        main = self.tmp / "main"
        install(main / "code" / "node_modules")
        worktree = self.tmp / "main" / ".worktrees" / "T1"
        app = ora_like(worktree, with_node_modules=False)
        porcelain = f"worktree {main}\nHEAD abc\nbranch refs/heads/dev\n\nworktree {worktree}\nHEAD def\nbranch refs/heads/T1\n"
        runner = FakeRunner(porcelain=porcelain, toplevel=str(worktree))
        found, source = harness.find_node_modules(app.parent, runner)
        self.assertEqual((found, source), (main / "code" / "node_modules", "main-checkout"))
        self.assertEqual([argv[3:] for argv, _ in runner.calls], [["rev-parse", "--show-toplevel"], ["worktree", "list", "--porcelain"]])

    def test_no_node_modules_anywhere_exits_4(self):
        app = ora_like(self.tmp, with_node_modules=False)
        with self.assertRaises(harness.HarnessError) as caught:
            self.run_harness(args(**{"--repo": app, "--out-dir": self.tmp / "out"}))
        self.assertEqual(caught.exception.exit_code, 4)
        self.assertIn("node_modules", caught.exception.message)

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_real_git_worktree(self):
        main = self.tmp / "main"
        ora_like(main)
        env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "PATH": "/usr/bin:/bin"}
        git = lambda *a: subprocess.run(["git", "-C", str(main), *a], check=True, capture_output=True, env=env)  # noqa: E731
        write(main / ".gitignore", "node_modules/\n")
        git("init", "-q", "-b", "dev")
        git("add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
        git("worktree", "add", "-q", str(main / ".worktrees" / "T1"), "-b", "T1")
        app = main / ".worktrees" / "T1" / "code" / "app"
        self.assertFalse((app.parent / "node_modules").exists())
        found, source = harness.find_node_modules(app.parent)
        self.assertEqual(found.resolve(), (main / "code" / "node_modules").resolve())
        self.assertEqual(source, "main-checkout")


class EsbuildTests(HarnessCase):
    def test_repo_esbuild_then_figma_cli_fallback(self):
        node_modules = install(self.tmp / "nm")
        self.assertEqual(harness.find_esbuild(node_modules)[2], "repo")
        bare = install(self.tmp / "bare", ("react",))
        fallback = install(self.tmp / "figma-cli-nm", ("esbuild",))
        with mock.patch.object(harness, "FALLBACK_NODE_MODULES", fallback):
            package, _, source = harness.find_esbuild(bare)
        self.assertEqual((package, source), (fallback / "esbuild", "figma-cli"))
        with mock.patch.object(harness, "FALLBACK_NODE_MODULES", self.tmp / "none"), self.assertRaises(harness.HarnessError) as caught:
            harness.find_esbuild(bare)
        self.assertEqual(caught.exception.exit_code, 4)


class EntryTests(HarnessCase):
    def test_entry_wraps_section_in_the_repo_theme(self):
        entry = harness.build_entry(Path("/r/app/components/Sections/Hero/ClientHero.js"), Path("/r/app/styles/theme/index.js"), {"title": "שלום"})
        self.assertIn("import { ThemeProvider } from 'styled-components';", entry)
        self.assertIn('import theme from "/r/app/styles/theme/index.js";', entry)
        self.assertIn('import Section from "/r/app/components/Sections/Hero/ClientHero.js";', entry)
        self.assertIn('const props = {"title": "שלום"};', entry)
        self.assertIn("createElement(ThemeProvider, { theme }, createElement(Section, props))", entry)

    def test_no_props_and_no_theme(self):
        entry = harness.build_entry(Path("/r/ClientHero.js"), None, None)
        self.assertIn("const props = {};", entry)
        self.assertIn("const theme = {};", entry)

    def test_stub_list(self):
        bare, files = harness.stub_definitions()
        self.assertEqual(set(bare), {"next/font/local", "next/image", "next/link", "server-only"})
        self.assertEqual([stub["name"] for stub in files], ["MediaBackground", "ResponsiveImage", "Breadcrumbs"])
        for stub in files:
            self.assertIn("className={className}", stub["source"])
        pattern = {stub["name"]: re.compile(stub["pattern"]) for stub in files}
        self.assertTrue(pattern["MediaBackground"].search("/r/app/components/UIComponents/MediaBackground/index.js"))
        self.assertTrue(pattern["ResponsiveImage"].search("/r/app/components/Core/Image/ResponsiveImage.js"))
        self.assertTrue(pattern["Breadcrumbs"].search("/r/app/components/Layout/Breadcrumbs.js"))
        self.assertFalse(pattern["Breadcrumbs"].search("/r/app/components/Sections/Hero/BreadcrumbsTitle.js"))
        self.assertFalse(any(p.search("/r/app/components/Sections/Hero/StyledHero.js") for p in pattern.values()))
        self.assertIn("fontFamily", bare["next/font/local"])

    def test_jsconfig_with_comments_and_trailing_commas(self):
        app = ora_like(self.tmp)
        config = harness.read_jsconfig(app.parent)
        self.assertEqual(config["baseUrl"], "./app")
        self.assertEqual(config["paths"], {"@/*": ["components/*"]})


class WriteTests(HarnessCase):
    def test_writes_only_under_out_dir(self):
        app = ora_like(self.tmp)
        repo_before = tree(self.tmp / "code")
        out = self.tmp / "stage" / "out"
        result, runner = self.run_harness(args(**{"--repo": app, "--out-dir": out}))
        self.assertTrue(result["ok"])
        self.assertEqual(tree(self.tmp / "code"), repo_before)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["bundle.js", "harness-record.json", "index.html"])
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["code", "stage"])
        config = runner.config
        self.assertEqual(config["outfile"], str(out.resolve() / "bundle.js"))
        self.assertEqual(config["entry"]["resolveDir"], str(out.resolve()))
        self.assertEqual(config["nodePaths"], [str(app.parent / "node_modules")])
        self.assertEqual(config["tsconfig"], str(app.parent / "jsconfig.json"))
        self.assertIn(str(app / "styles" / "theme" / "index.js"), config["entry"]["contents"])
        self.assertEqual(runner.calls[0][0], ["/usr/bin/node", str(harness.RUNNER)])
        record = json.loads((out / "harness-record.json").read_text(encoding="utf-8"))
        self.assertEqual(record["level"], "harness")
        self.assertIn("not a Level 2", record["note"])
        self.assertEqual(record["stubbed"][0]["module"], "next/font/local")
        self.assertIn("--props", record["propsNote"])
        self.assertIn('src="bundle.js"', (out / "index.html").read_text(encoding="utf-8"))

    def test_bundle_failure_exits_3_with_stderr_and_no_page(self):
        app = ora_like(self.tmp)
        out = self.tmp / "out"
        runner = FakeRunner(bundle_returncode=3, stderr="✘ [ERROR] Could not resolve \"x\"\n")
        with self.assertRaises(harness.HarnessError) as caught:
            self.run_harness(args(**{"--repo": app, "--out-dir": out}), runner)
        self.assertEqual(caught.exception.exit_code, 3)
        self.assertIn("Could not resolve", caught.exception.detail)
        self.assertFalse((out / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
