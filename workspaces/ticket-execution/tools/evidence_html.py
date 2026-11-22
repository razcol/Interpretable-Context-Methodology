#!/usr/bin/env python3
"""Bundle a run's ticket images and verification screenshots into one self-contained HTML file.

Usage:
  evidence_html.py <runs>/<KEY> [--out <path>] [--key <KEY>]

Reads from the run folder:
  01-intake/attachments/*   ticket images (also images directly in 01-intake/)
  05-verify/shots/**        verification screenshots (png, jpg, jpeg, webp, gif)
  05-verify/verify-report.md  checklist rows (PASS, FAIL, NOT VERIFIED), when present

Only real images are embedded: the extension must be an image type, the first bytes
must match that type, the file must resolve inside the run folder, and it must be
under 15 MB. Anything else is counted under "skipped".

Writes one HTML file (default <runs>/<KEY>/06-handoff/evidence.html). Images are
embedded as base64 data: URIs, so the file needs no server, no network and no
sibling files. The page carries a Content-Security-Policy that blocks scripts and
every external request. On WSL, open it from Windows through the wslPath below.

Cards pair the Nth ticket image with the Nth verified screenshot (ticket vs verified);
leftovers get a card of their own.

Prints one JSON object:
  {"ok": true, "html": "<linux path>", "wslPath": "\\\\wsl.localhost\\<distro>\\<path>",
   "beforeCount": N, "afterCount": M, "skipped": K, "checklist": {...}}
Exit codes: 0 done, 2 the run folder is missing or the file cannot be written.
"""

import argparse
import base64
import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
STATUS_RE = re.compile(r"\b(NOT[ _-]VERIFIED|PASS(?:ED)?|FAIL(?:ED)?)\b", re.I)
CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'"


def sniff_mime(head):
    """Image type from the first bytes of a file, or None."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def is_embeddable(path, root):
    """True for a real image of allowed size that resolves inside the run folder."""
    try:
        real = path.resolve()
        if not real.is_relative_to(root) or not real.is_file():
            return False
        if real.stat().st_size > MAX_IMAGE_BYTES:
            return False
        with real.open("rb") as f:
            head = f.read(16)
    except OSError:
        return False
    return sniff_mime(head) == IMAGE_TYPES.get(path.suffix.lower())


def list_images(folder, root, recursive=False):
    """(images, skipped) for a folder, sorted by name. A missing folder gives ([], 0)."""
    folder = Path(folder)
    if not folder.is_dir():
        return [], 0
    walker = folder.rglob("*") if recursive else folder.iterdir()
    candidates = sorted(p for p in walker if p.suffix.lower() in IMAGE_TYPES and not p.is_dir())
    good = [p for p in candidates if is_embeddable(p, root)]
    return good, len(candidates) - len(good)


def collect_before(run_dir):
    """Ticket images: 01-intake/attachments first, then images directly in 01-intake."""
    intake = Path(run_dir, "01-intake")
    a, sa = list_images(intake / "attachments", run_dir, recursive=True)
    b, sb = list_images(intake, run_dir)
    return a + b, sa + sb


def collect_after(run_dir):
    return list_images(Path(run_dir, "05-verify", "shots"), run_dir, recursive=True)


def data_uri(path):
    mime = IMAGE_TYPES[Path(path).suffix.lower()]
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


def normalize_status(word):
    word = word.upper()
    if word.startswith("NOT"):
        return "NOT VERIFIED"
    return "PASS" if word.startswith("PASS") else "FAIL"


def parse_checklist(report_path):
    """Rows of verify-report.md that carry a status word.

    Returns (rows, counts). A row is {"status", "text"}; a table row or list item
    whose text holds PASS, FAIL or NOT VERIFIED counts once, by its first status word.
    """
    rows = []
    counts = {"pass": 0, "fail": 0, "notVerified": 0}
    path = Path(report_path)
    if not path.is_file():
        return rows, counts
    keys = {"PASS": "pass", "FAIL": "fail", "NOT VERIFIED": "notVerified"}
    for raw in path.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"[|\s:-]+", line):
            continue
        if not (line.startswith("|") or re.match(r"([-*+]|\d+[.)])\s", line)):
            continue
        m = STATUS_RE.search(line)
        if not m:
            continue
        status = normalize_status(m.group(1))
        text = line.strip("|").replace("|", " · ")
        text = re.sub(r"^([-*+]|\d+[.)])\s+", "", text).replace("**", "").replace("`", "").strip()
        rows.append({"status": status, "text": re.sub(r"\s+", " ", text)})
        counts[keys[status]] += 1
    return rows, counts


def wsl_path(linux_path, distro=None):
    """Windows UNC path to a Linux file, for example \\\\wsl.localhost\\Ubuntu\\home\\me\\a.html."""
    distro = distro or os.environ.get("WSL_DISTRO_NAME") or "Ubuntu"
    rel = str(linux_path).lstrip("/").replace("/", "\\")
    return f"\\\\wsl.localhost\\{distro}\\{rel}"


def figure(path, label, run_dir):
    esc = html.escape
    try:
        shown = str(Path(path).relative_to(run_dir))
    except ValueError:
        shown = str(path)
    return (f'<figure><figcaption class="tag">{esc(label)}</figcaption>'
            f'<img src="{data_uri(path)}" alt="{esc(Path(path).name)}">'
            f'<figcaption class="name">{esc(Path(path).name)}<br><span>{esc(shown)}</span></figcaption></figure>')


def build_cards(before, after, run_dir):
    cards = []
    for i in range(max(len(before), len(after))):
        parts = []
        if i < len(before):
            parts.append(figure(before[i], "Ticket", run_dir))
        if i < len(after):
            parts.append(figure(after[i], "Verified", run_dir))
        title = "Ticket vs verified" if len(parts) == 2 else ("Ticket only" if i < len(before) else "Verified only")
        cards.append(f'<section class="card"><h3>{title} #{i + 1}</h3><div class="pair">{"".join(parts)}</div></section>')
    return cards


STYLE = """
body{font:15px/1.5 system-ui,sans-serif;margin:0;background:#f4f5f7;color:#1d2125}
header,main{max-width:1280px;margin:0 auto;padding:16px 24px}
h1{margin:0 0 4px;font-size:22px}h2{font-size:18px;margin-top:28px}h3{margin:0 0 10px;font-size:15px}
.meta{color:#5e6c84}
.card{background:#fff;border:1px solid #dfe1e6;border-radius:8px;padding:14px;margin:14px 0}
.pair{display:flex;gap:16px;flex-wrap:wrap}
figure{flex:1 1 360px;margin:0;min-width:0}
figure img{max-width:100%;height:auto;border:1px solid #dfe1e6;border-radius:4px;display:block}
.tag{font-weight:600;text-transform:uppercase;font-size:12px;letter-spacing:.05em;color:#5e6c84;margin-bottom:6px}
.name{font-size:13px;margin-top:6px;word-break:break-all}.name span{color:#6b778c}
table{border-collapse:collapse;width:100%;background:#fff}td{border:1px solid #dfe1e6;padding:6px 10px;vertical-align:top}
td.s{white-space:nowrap;font-weight:600;width:1%}
.PASS{color:#1b7f3b}.FAIL{color:#c9372c}.NV{color:#b65c02}
details{margin-top:12px}pre{white-space:pre-wrap;background:#fff;border:1px solid #dfe1e6;padding:10px;border-radius:6px}
"""


def render(key, before, after, rows, counts, report_text, run_dir):
    esc = html.escape
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
           f'<title>{esc(key)} evidence</title><style>{STYLE}</style></head><body>',
           f'<header><h1>{esc(key)}: evidence</h1><div class="meta">Generated '
           f'{datetime.now().strftime("%Y-%m-%d %H:%M")}. Ticket images: {len(before)}. '
           f'Verified screenshots: {len(after)}.</div></header><main>']
    out.append("<h2>Screenshots</h2>")
    if before or after:
        out += build_cards(before, after, run_dir)
    else:
        out.append('<p class="meta">No ticket images or verification screenshots were found.</p>')
    out.append("<h2>Checklist</h2>")
    if rows:
        total = counts["pass"] + counts["fail"] + counts["notVerified"]
        out.append(f'<p>{counts["pass"]} of {total} passed, {counts["fail"]} failed, '
                   f'{counts["notVerified"]} not verified.</p><table>')
        for r in rows:
            cls = {"PASS": "PASS", "FAIL": "FAIL"}.get(r["status"], "NV")
            out.append(f'<tr><td class="s {cls}">{esc(r["status"])}</td><td>{esc(r["text"])}</td></tr>')
        out.append("</table>")
    else:
        out.append('<p class="meta">No checklist rows found (05-verify/verify-report.md missing or without statuses).</p>')
    if report_text:
        out.append(f"<details><summary>verify-report.md</summary><pre>{esc(report_text)}</pre></details>")
    out.append("</main></body></html>")
    return "\n".join(out)


def fail(message):
    print(json.dumps({"ok": False, "error": message}))
    sys.exit(2)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", help="the run folder, <runs>/<KEY>")
    ap.add_argument("--out", help="HTML path (default <run dir>/06-handoff/evidence.html)")
    ap.add_argument("--key", help="ticket key shown in the title (default: the run folder name)")
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.is_dir():
        fail(f"run folder not found: {run_dir}")
    key = args.key or run_dir.name
    out = Path(args.out).expanduser().resolve() if args.out else run_dir / "06-handoff" / "evidence.html"

    before, skipped_before = collect_before(run_dir)
    after, skipped_after = collect_after(run_dir)
    report = run_dir / "05-verify" / "verify-report.md"
    rows, counts = parse_checklist(report)
    report_text = report.read_text(errors="replace") if report.is_file() else ""
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(key, before, after, rows, counts, report_text, run_dir), encoding="utf-8")
    except OSError as e:
        fail(f"cannot write {out}: {e}")

    print(json.dumps({
        "ok": True,
        "html": str(out),
        "wslPath": wsl_path(out),
        "beforeCount": len(before),
        "afterCount": len(after),
        "skipped": skipped_before + skipped_after,
        "checklist": counts,
    }))


if __name__ == "__main__":
    main()
