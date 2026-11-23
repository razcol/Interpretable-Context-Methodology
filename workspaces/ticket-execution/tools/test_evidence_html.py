"""Tests for evidence_html.py. Run: python3 -m pytest workspaces/ticket-execution/tools/test_evidence_html.py"""

import base64
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import evidence_html  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 24
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 16

REPORT = """# Verify report

| Row | Check | Result |
|-----|-------|--------|
| 1 | Hero title shows | PASS |
| 2 | Button <b>links</b> | FAIL |
| 3 | Mobile layout | NOT VERIFIED |

- Row 4 looks right: passed
Some prose with PASS in it is not a row.
"""


def make_run(tmp, before=(), after=(), report=None, baseline=()):
    run = Path(tmp, "runs", "ABC-1")
    for name, data in baseline:
        p = run / "03b-baseline" / "shots" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for name, data in before:
        p = run / "01-intake" / "attachments" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for name, data in after:
        p = run / "05-verify" / "shots" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    run.mkdir(parents=True, exist_ok=True)
    if report is not None:
        (run / "05-verify").mkdir(parents=True, exist_ok=True)
        (run / "05-verify" / "verify-report.md").write_text(report)
    return run


def run_main(argv, env=None):
    buf = io.StringIO()
    with mock.patch.dict("os.environ", env or {}, clear=False), contextlib.redirect_stdout(buf):
        try:
            evidence_html.main(argv)
            code = 0
        except SystemExit as e:
            code = e.code
    return code, json.loads(buf.getvalue())


class WslPath(unittest.TestCase):
    def test_default_distro(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("WSL_DISTRO_NAME", None)
            self.assertEqual(evidence_html.wsl_path("/srv/work/a.html"), "\\\\wsl.localhost\\Ubuntu\\srv\\work\\a.html")

    def test_env_distro(self):
        with mock.patch.dict("os.environ", {"WSL_DISTRO_NAME": "Debian"}):
            self.assertEqual(evidence_html.wsl_path("/x/y.html"), "\\\\wsl.localhost\\Debian\\x\\y.html")


class Checklist(unittest.TestCase):
    def test_counts_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, "r.md")
            p.write_text(REPORT)
            rows, counts = evidence_html.parse_checklist(p)
        self.assertEqual(counts, {"pass": 2, "fail": 1, "notVerified": 1})
        self.assertEqual([r["status"] for r in rows], ["PASS", "FAIL", "NOT VERIFIED", "PASS"])

    def test_missing_report(self):
        rows, counts = evidence_html.parse_checklist("/nonexistent/report.md")
        self.assertEqual((rows, counts), ([], {"pass": 0, "fail": 0, "notVerified": 0}))


class Collect(unittest.TestCase):
    def test_skips_fake_and_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(tmp, before=[("a.png", PNG), ("fake.png", b"not an image"), ("notes.txt", b"x")],
                           after=[("s1.png", PNG), ("s2.jpg", JPG), ("s3.webp", WEBP)])
            run = run.resolve()
            before, sb = evidence_html.collect_before(run)
            after, sa = evidence_html.collect_after(run)
        self.assertEqual([p.name for p in before], ["a.png"])
        self.assertEqual(sb, 1)
        self.assertEqual([p.name for p in after], ["s1.png", "s2.jpg", "s3.webp"])
        self.assertEqual(sa, 0)

    def test_intake_root_images_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(tmp, before=[("a.png", PNG)]).resolve()
            (run / "01-intake" / "top.jpg").write_bytes(JPG)
            before, _ = evidence_html.collect_before(run)
        self.assertEqual([p.name for p in before], ["a.png", "top.jpg"])

    def test_symlink_outside_run_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp, "outside.png")
            outside.write_bytes(PNG)
            run = make_run(tmp, after=[("ok.png", PNG)]).resolve()
            (run / "05-verify" / "shots" / "link.png").symlink_to(outside)
            after, skipped = evidence_html.collect_after(run)
        self.assertEqual([p.name for p in after], ["ok.png"])
        self.assertEqual(skipped, 1)


class Cli(unittest.TestCase):
    def test_full_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(tmp, before=[("ticket.png", PNG)],
                           after=[("a.png", PNG), ("b.jpg", JPG)], report=REPORT)
            code, out = run_main([str(run)], env={"WSL_DISTRO_NAME": "Ubuntu-22.04"})
            self.assertEqual(code, 0)
            self.assertTrue(out["ok"])
            self.assertEqual((out["beforeCount"], out["afterCount"]), (1, 2))
            html_path = Path(out["html"])
            self.assertEqual(html_path, run.resolve() / "06-handoff" / "evidence.html")
            self.assertTrue(out["wslPath"].startswith("\\\\wsl.localhost\\Ubuntu-22.04\\"))
            self.assertTrue(out["wslPath"].endswith("\\06-handoff\\evidence.html"))
            text = html_path.read_text()
        self.assertIn("data:image/png;base64," + base64.b64encode(PNG).decode(), text)
        self.assertIn("data:image/jpeg;base64,", text)
        self.assertIn("Ticket vs verified #1", text)
        self.assertIn("Verified only #2", text)
        self.assertIn("ticket.png", text)
        self.assertIn("2 of 4 passed, 1 failed, 1 not verified.", text)
        self.assertIn("&lt;b&gt;links&lt;/b&gt;", text)
        self.assertNotIn("<b>links</b>", text)
        self.assertIn("Content-Security-Policy", text)
        self.assertIsNone(re.search(r'(src|href)="https?://', text))
        self.assertNotIn("<script", text)

    def test_out_and_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(tmp, after=[("a.png", PNG)])
            out_path = Path(tmp, "elsewhere", "e.html")
            code, out = run_main([str(run), "--out", str(out_path), "--key", "XYZ-<9>"])
            self.assertEqual(code, 0)
            self.assertEqual(out["html"], str(out_path.resolve()))
            text = out_path.read_text()
        self.assertIn("XYZ-&lt;9&gt;: evidence", text)
        self.assertEqual((out["beforeCount"], out["afterCount"]), (0, 1))

    def test_no_evidence_still_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(tmp)
            code, out = run_main([str(run)])
            self.assertEqual(code, 0)
            text = Path(out["html"]).read_text()
        self.assertEqual((out["beforeCount"], out["afterCount"]), (0, 0))
        self.assertIn("No ticket images or verification screenshots", text)

    def test_missing_run_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run_main([str(Path(tmp, "nope"))])
        self.assertEqual(code, 2)
        self.assertFalse(out["ok"])


class BaselineCollect(unittest.TestCase):
    def test_collect_baseline_recursive_and_skips_fake(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(tmp, baseline=[("a.png", PNG), ("sub/b.jpg", JPG), ("fake.png", b"nope"), ("n.txt", b"x")])
            run = run.resolve()
            shots, skipped = evidence_html.collect_baseline(run)
        self.assertEqual(sorted(p.name for p in shots), ["a.png", "b.jpg"])
        self.assertEqual(skipped, 1)

    def test_collect_baseline_missing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(tmp).resolve()
            self.assertEqual(evidence_html.collect_baseline(run), ([], 0))

    def test_pair_by_stem_case_insensitive_and_deterministic(self):
        b = [Path("x/Row1__1440x900.png"), Path("x/only_b.png")]
        a = [Path("y/row1__1440x900.PNG"), Path("y/only_a.png")]
        pairs = evidence_html.pair_by_stem(b, a)
        self.assertEqual([(s, bool(pb), bool(pa)) for s, pb, pa in pairs],
                         [("only_a", False, True), ("only_b", True, False), ("Row1__1440x900", True, True)])
        self.assertEqual(pairs, evidence_html.pair_by_stem(list(reversed(b)), list(reversed(a))))


class BaselineCli(unittest.TestCase):
    def render_run(self, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(tmp, **kw)
            code, out = run_main([str(run)])
            self.assertEqual(code, 0)
            return out, Path(out["html"]).read_text()

    def test_filename_matched_pairing(self):
        out, text = self.render_run(baseline=[("row1__1440x900.png", PNG), ("row2__375x812.png", PNG)],
                                    after=[("row1__1440x900.png", PNG), ("ROW2__375x812.png", PNG)])
        self.assertIn("<h2>Before vs. After</h2>", text)
        self.assertNotIn("<h2>Screenshots</h2>", text)
        self.assertIn("Before vs. After: row1__1440x900", text)
        self.assertIn("Before vs. After: row2__375x812", text)
        self.assertEqual(text.count("Before (Baseline)"), 2)
        self.assertEqual(text.count("After (Annotated)"), 2)
        self.assertNotIn("Before only", text)
        self.assertNotIn("After only", text)
        # Before sits left of After inside each card.
        card = text.split("Before vs. After: row1__1440x900", 1)[1].split("</section>", 1)[0]
        self.assertLess(card.index("Before (Baseline)"), card.index("After (Annotated)"))
        self.assertIn("Baseline screenshots: 2", text)
        self.assertIn("Verified screenshots: 2", text)
        self.assertIn("Ticket images: 0", text)
        self.assertNotIn("Ticket Reference", text)

    def test_unmatched_cards(self):
        out, text = self.render_run(baseline=[("both.png", PNG), ("gone.png", PNG)],
                                    after=[("both.png", PNG), ("new.jpg", JPG)])
        self.assertIn("Before vs. After: both", text)
        self.assertIn("Before only: gone", text)
        self.assertIn("After only: new", text)
        self.assertEqual(text.count("Before (Baseline)"), 2)
        self.assertEqual(text.count("After (Annotated)"), 2)
        self.assertNotIn("Ticket vs verified", text)

    def test_ticket_reference_coexists(self):
        out, text = self.render_run(before=[("ticket.png", PNG)], baseline=[("a.png", PNG)], after=[("a.png", PNG)])
        self.assertIn("<h2>Before vs. After</h2>", text)
        self.assertIn("<h2>Ticket Reference</h2>", text)
        self.assertLess(text.index("<h2>Before vs. After</h2>"), text.index("<h2>Ticket Reference</h2>"))
        self.assertLess(text.index("<h2>Ticket Reference</h2>"), text.index("<h2>Checklist</h2>"))
        ref = text.split("<h2>Ticket Reference</h2>", 1)[1].split("<h2>Checklist</h2>", 1)[0]
        self.assertIn("ticket.png", ref)
        self.assertNotIn("a.png", ref)
        self.assertIn("Ticket images: 1", text)
        self.assertEqual((out["beforeCount"], out["afterCount"], out["baselineCount"]), (1, 1, 1))

    def test_baseline_count_and_skipped(self):
        out, text = self.render_run(before=[("t.png", PNG), ("tfake.png", b"bad")],
                                    baseline=[("a.png", PNG), ("fake.png", b"not an image"), ("fake2.jpg", b"")],
                                    after=[("a.png", PNG), ("afake.png", b"zzz")])
        self.assertEqual(out["baselineCount"], 1)
        self.assertEqual(out["beforeCount"], 1)
        self.assertEqual(out["afterCount"], 1)
        self.assertEqual(out["skipped"], 4)
        self.assertEqual(set(out), {"ok", "html", "wslPath", "beforeCount", "afterCount",
                                    "baselineCount", "skipped", "checklist"})

    def test_titles_escaped(self):
        out, text = self.render_run(baseline=[("a<b>.png", PNG)], after=[("A<B>.png", PNG)])
        self.assertIn("Before vs. After: a&lt;b&gt;", text)
        self.assertNotIn("a<b>", text)

    def test_baseline_only_run(self):
        out, text = self.render_run(baseline=[("a.png", PNG)])
        self.assertIn("Before only: a", text)
        self.assertEqual((out["beforeCount"], out["afterCount"], out["baselineCount"]), (0, 0, 1))
        self.assertIn("Content-Security-Policy", text)
        self.assertNotIn("<script", text)

    def test_legacy_run_unchanged(self):
        out, text = self.render_run(before=[("t.png", PNG)], after=[("a.png", PNG), ("b.png", PNG)])
        self.assertEqual(out["baselineCount"], 0)
        self.assertIn("<h2>Screenshots</h2>", text)
        self.assertIn("Ticket vs verified #1", text)
        self.assertIn("Verified only #2", text)
        self.assertNotIn("Before vs. After", text)
        self.assertNotIn("Ticket Reference", text)
        self.assertNotIn("Baseline screenshots", text)

    def test_suffixed_folder_title_uses_jira_prefix_when_key_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp, "runs", "ABC-1--dev--try-a")
            run.mkdir(parents=True)
            code, out = run_main([str(run)])
            self.assertEqual(code, 0, out)
            text = Path(out["html"]).read_text(encoding="utf-8")
            self.assertIn("<title>ABC-1 evidence</title>", text)
            self.assertIn("<h1>ABC-1: evidence</h1>", text)


if __name__ == "__main__":
    unittest.main()
