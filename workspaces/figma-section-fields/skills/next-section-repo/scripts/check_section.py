#!/usr/bin/env python3
"""Check one section folder against its repo profile. Prints one JSON object with a row per check."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsread  # noqa: E402
import probe_repo  # noqa: E402

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"}
PAGE_FIELDS = {"breadcrumbs", "breadcrumb", "seo", "order"}
LINT_TIMEOUT = 120
MOBILE_NESTED_MAX = 6
HARD_BP = re.compile(r"@media[^{;`]*\(\s*(?:max|min)-width\s*:\s*\d+(?:\.\d+)?px\s*\)")


def emit(payload: dict, exit_code: int = 0) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    raise SystemExit(exit_code)


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, check_id: str, status: str, detail: str) -> None:
        self.rows.append({"id": check_id, "status": status, "detail": detail})

    def summary(self) -> dict:
        return {status: sum(1 for row in self.rows if row["status"] == status) for status in ("pass", "fail", "warn")}


def first_statement(text: str) -> str:
    for line in jsread.strip_comments(text).splitlines():
        if line.strip():
            return line.strip().rstrip(";").strip()
    return ""


def resolve_folder(profile: dict, folder: str) -> Path:
    path = Path(folder).expanduser()
    if path.is_dir():
        return path.resolve()
    candidate = Path(profile["appRoot"]) / profile["sectionsDir"] / folder
    if candidate.is_dir():
        return candidate.resolve()
    raise probe_repo.ProbeError("FOLDER_NOT_FOUND", f"No section folder {folder} was found.", 4)


def gql_text(folder: Path) -> str:
    return jsread.strip_comments(jsread.read(folder / f"{folder.name}.gql")).replace("#", "")


def top_level_fields(gql: str) -> list[str]:
    start = gql.find("{")
    if start == -1:
        return []
    body = gql[start + 1 : jsread.match_brace(gql, start)]
    names = []
    depth = 0
    for token in re.finditer(r"\{|\}|\.\.\.\s*[A-Za-z_]\w*|[A-Za-z_]\w*", body):
        value = token.group(0)
        if value == "{":
            depth += 1
        elif value == "}":
            depth -= 1
        elif depth == 0 and not value.startswith("..."):
            names.append(value)
    return names


def known_fragments(profile: dict) -> set[str]:
    root = Path(profile["appRoot"])
    names = {name for name, _ in probe_repo.gql_fragments(root, list(profile.get("globalFragmentDirs") or []) + ["app/components"])}
    for role in (profile.get("fragments") or {}).values():
        if role:
            names.add(role["name"])
    return names


def staged_files(app_root: Path) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=app_root,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_files(checks: Checks, profile: dict, folder: Path) -> None:
    name = folder.name
    wanted = [entry.replace("{F}", name) for entry in profile["scaffold"]["files"]]
    missing = [entry for entry in wanted if not (folder / entry).is_file()]
    checks.add("files-present", "fail" if missing else "pass", "Missing: " + ", ".join(missing) if missing else "All scaffold files exist.")
    server = folder / f"Server{name}.js"
    if server.is_file():
        first = first_statement(jsread.read(server))
        ok = first in ("import 'server-only'", 'import "server-only"')
        checks.add("server-only", "pass" if ok else "fail", "Server file starts with import 'server-only'." if ok else f"Server file starts with: {first[:60]}")
    client = folder / f"Client{name}.js"
    if client.is_file():
        first = first_statement(jsread.read(client))
        ok = first in ("'use client'", '"use client"')
        checks.add("use-client", "pass" if ok else "fail", "Client file starts with 'use client'." if ok else f"Client file starts with: {first[:60]}")


def check_name(checks: Checks, profile: dict, folder: Path) -> None:
    name = folder.name
    problems = []
    match = re.search(r"fragment\s+([A-Za-z_]\w*)\s+on\s+([A-Za-z_]\w*)", gql_text(folder))
    if match is None:
        problems.append("the .gql has no fragment line")
    else:
        if match.group(1) != name:
            problems.append(f"fragment is named {match.group(1)}")
        if not re.fullmatch(rf"(?:FieldsFlexible|EnFieldsEnFlexible){re.escape(name)}Layout", match.group(2)):
            problems.append(f"fragment is on {match.group(2)}, not FieldsFlexible{name}Layout")
    if "Server" in name:
        problems.append("the folder name contains Server")
    global_names = {role["name"].lower() for role in (profile.get("fragments") or {}).values() if role}
    if name.lower() in global_names:
        problems.append("the folder name equals a global fragment name, which would override it site-wide")
    checks.add("folder-name", "fail" if problems else "pass", "; ".join(problems) if problems else "Folder, fragment and layout names agree.")


def check_assets(checks: Checks, profile: dict, folder: Path) -> None:
    images = [path.name for path in folder.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES]
    has_assets = (folder / "assets").exists()
    if has_assets or images:
        checks.add("no-assets", "fail", "Images belong in WordPress: " + ", ".join((["assets/"] if has_assets else []) + images[:6]))
    else:
        checks.add("no-assets", "pass", "No image files in the section folder.")
    report = folder / "field-report.md"
    if report.is_file():
        staged = staged_files(Path(profile["appRoot"]))
        relative = str(report.relative_to(Path(profile["appRoot"])))
        repo_relative = [entry for entry in (staged or []) if entry.endswith(relative)]
        if repo_relative:
            checks.add("field-report-staged", "warn", "field-report.md is staged. It is a helper for you, usually not committed.")


def styled_text(folder: Path) -> str:
    return jsread.read(folder / f"Styled{folder.name}.js")


def check_styles(checks: Checks, profile: dict, folder: Path) -> None:
    text = styled_text(folder)
    literal = [value for value in re.findall(r"font-family\s*:\s*([^;\n]+)", text) if "${" not in value]
    checks.add(
        "no-font-literal",
        "fail" if literal else "pass",
        "font-family literal: " + ", ".join(sorted({value.strip() for value in literal}))[:200] if literal else "Fonts come from the theme.",
    )
    colors = profile["theme"].get("colors") or {}
    by_value: dict[str, str] = {}
    for path, value in colors.items():
        by_value.setdefault(value, path)
    matches = []
    for raw in re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)", text):
        value = probe_repo.normalize_color(raw)
        if value and value in by_value:
            matches.append(f"{raw} is theme.colors.{by_value[value]}")
    checks.add("theme-colors", "warn" if matches else "pass", "; ".join(sorted(set(matches)))[:300] if matches else "No literal color equals a theme color.")
    root_block = text.split("`", 2)[1] if text.count("`") >= 2 else ""
    root_level = re.sub(r"\{[^{}]*\}", "", re.sub(r"\{[^{}]*\}", "", root_block))
    root_rtl = re.search(r"(?<![-\w])direction\s*:\s*rtl", root_level) is not None
    rows = re.search(r"display\s*:\s*flex", text) is not None
    resets = re.search(r"(?<![-\w])direction\s*:\s*ltr", text) is not None
    if root_rtl and rows and not resets:
        checks.add("no-root-direction", "fail", "The root sets direction: rtl and no row resets it to ltr, so flex rows run in reverse of Figma.")
    elif root_rtl:
        checks.add("no-root-direction", "pass", "The root sets rtl, and rows reset it to ltr.")
    else:
        checks.add("no-root-direction", "pass", "The root does not set rtl.")
    uses_layout = "mixins.layout" in text
    registered = "layout" in (profile["theme"].get("mixins") or [])
    if uses_layout and not registered:
        checks.add("mixins-layout", "fail", "theme.mixins.layout is used, but this repo's theme has no layout mixin.")
    else:
        checks.add("mixins-layout", "pass", "Mixins match the theme.")


def check_mobile(checks: Checks, profile: dict, folder: Path, mobile_pass: bool) -> None:
    files = {str(path.relative_to(folder)): jsread.read(path) for path in sorted(folder.rglob("Styled*.js"))}
    overlap = probe_repo.bps_overlap(profile["theme"].get("bpsMedia") or {})
    desktop = [name for name, text in files.items() if probe_repo.BPS_DESKTOP.search(text)]
    if overlap and desktop:
        checks.add("bps-overlap", "warn", f"bps.desktop and bps.mobile both match at {overlap}, and {', '.join(desktop)} uses bps.desktop. Check that width too.")
    else:
        checks.add("bps-overlap", "pass", "No bps.desktop rule at an overlapping width.")
    nested = []
    for name, text in files.items():
        for helper, body in probe_repo.css_templates(text):
            if helper:
                continue
            for block in probe_repo.css_tree(body)["children"]:
                count = probe_repo.descendants(block)
                if probe_repo.BPS_MOBILE.search(block["header"]) and count > MOBILE_NESTED_MAX:
                    nested.append(f"{name} ({count} selectors)")
    checks.add(
        "mobile-nested",
        "warn" if nested else "pass",
        "Root-level bps.mobile block instead of nested ones: " + ", ".join(nested) + ". Nest them, or record why." if nested else "Mobile rules are nested.",
    )
    gate = (profile.get("mobile") or {}).get("hoverGate")
    open_hover = sorted({
        name + ": " + " ".join(rule["selector"].split())[:60]
        for name, text in files.items()
        for rule in probe_repo.hover_rules(text)
        if rule["reveals"] and not probe_repo.hover_gated(rule["context"], gate)
    })
    wanted = "@media (hover: hover)" if gate == "hover-media" else "theme.bps.desktop or @media (hover: hover)"
    checks.add(
        "hover-gated",
        ("fail" if mobile_pass else "warn") if open_hover else "pass",
        f"A :hover reveal outside {wanted}, so touch screens never see it: " + "; ".join(open_hover)[:300] if open_hover else "Every :hover reveal is gated.",
    )
    literal = sorted({f"{name}: {match.group(0)}" for name, text in files.items() for match in HARD_BP.finditer(text)})
    checks.add("no-hardcoded-bp", "fail" if literal else "pass", "Use theme.bps instead of " + "; ".join(literal)[:300] if literal else "Breakpoints come from theme.bps.")


def check_props(checks: Checks, folder: Path) -> None:
    client = folder / f"Client{folder.name}.js"
    text = jsread.read(client)
    if not text:
        return
    missing = []
    for match in re.finditer(r"(?:const|function)\s+([A-Z]\w*)\s*=?\s*\(\s*\{", text):
        if not re.search(rf"\b{match.group(1)}\.propTypes\s*=", text):
            missing.append(match.group(1))
    checks.add("prop-types", "fail" if missing else "pass", "No propTypes on: " + ", ".join(missing) if missing else "Every component with props declares propTypes.")


def check_fragment(checks: Checks, profile: dict, folder: Path) -> None:
    gql = gql_text(folder)
    if not gql:
        return
    known = known_fragments(profile)
    unknown = sorted({name for name in re.findall(r"\.\.\.\s*([A-Za-z_]\w*)", gql) if name not in known and not name.startswith("on")})
    checks.add("spreads-exist", "fail" if unknown else "pass", "Unknown fragments: " + ", ".join(unknown) if unknown else "Every spread exists in the repo.")
    shared = [role for role in ("mediaItem", "backgroundFields", "responsiveMedia") if (profile.get("fragments") or {}).get(role)]
    hand = re.search(r"node\s*\{\s*(?:src\s*:\s*)?mediaItemUrl", gql) is not None
    if hand and shared:
        names = ", ".join((profile["fragments"][role] or {})["name"] for role in shared)
        checks.add("no-hand-media", "fail", f"The fragment selects node {{ mediaItemUrl }} by hand. Spread the shared fragment instead ({names}).")
    else:
        checks.add("no-hand-media", "pass", "Media come through shared fragments.")
    page = sorted(set(top_level_fields(gql)) & PAGE_FIELDS)
    checks.add("no-page-fields", "fail" if page else "pass", "Page-level data is not a section field: " + ", ".join(page) if page else "No page-level fields.")


def check_eol(checks: Checks, profile: dict, folder: Path) -> None:
    wrong = []
    for path in sorted(folder.glob("*.js")):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        crlf = data.count(b"\r\n")
        lf = data.count(b"\n") - crlf
        actual = "crlf" if crlf > lf else "lf"
        if (crlf or lf) and actual != profile["eol"]:
            wrong.append(path.name)
    checks.add("eol", "fail" if wrong else "pass", f"Not {profile['eol']}: " + ", ".join(wrong) if wrong else f"Line endings are {profile['eol']}.")


def check_lint(checks: Checks, profile: dict, folder: Path) -> None:
    root = Path(profile["appRoot"])
    command = list(profile.get("lintCommand") or [])
    if not command or not (root / "node_modules").is_dir():
        checks.add("eslint", "warn", "ESLint did not run: node_modules is missing.")
        return
    targets = [str(path) for path in sorted(folder.glob("*.js"))]
    if not targets:
        return
    try:
        result = subprocess.run(
            command + targets,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=LINT_TIMEOUT,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        checks.add("eslint", "warn", f"ESLint did not run: {type(error).__name__}.")
        return
    output = (result.stdout + result.stderr).strip()
    errors = re.search(r"(\d+)\s+errors?", output)
    if result.returncode == 0:
        checks.add("eslint", "pass", "ESLint reports no errors.")
    elif errors and int(errors.group(1)) > 0:
        checks.add("eslint", "fail", f"ESLint: {errors.group(0)}. " + " ".join(output.splitlines()[:6])[:400])
    else:
        lines = [line for line in output.splitlines() if not line.startswith("npm warn")]
        reason = next((line for line in lines if line.startswith("Error")), lines[0] if lines else "no output")
        checks.add("eslint", "warn", "ESLint could not run on this repo: " + reason[:240])


def check_section(profile: dict, folder_arg: str, lint: bool = True, mobile_pass: bool = False) -> dict:
    folder = resolve_folder(profile, folder_arg)
    checks = Checks()
    check_files(checks, profile, folder)
    check_name(checks, profile, folder)
    check_assets(checks, profile, folder)
    check_styles(checks, profile, folder)
    check_mobile(checks, profile, folder, mobile_pass)
    check_props(checks, folder)
    check_fragment(checks, profile, folder)
    check_eol(checks, profile, folder)
    if lint:
        check_lint(checks, profile, folder)
    summary = checks.summary()
    return {"ok": True, "folder": str(folder), "checks": checks.rows, "summary": summary, "pass": summary["fail"] == 0}


def load_profile(path: str | None, repo: str) -> dict:
    if path:
        try:
            profile = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise probe_repo.ProbeError("PROFILE", "The profile file is not readable JSON.", 3)
        if not isinstance(profile, dict) or profile.get("schemaVersion") != probe_repo.SCHEMA_VERSION:
            raise probe_repo.ProbeError("PROFILE", "The profile is not schemaVersion 1.", 3)
        return profile
    return probe_repo.probe(Path(repo).expanduser())["profile"]


def main() -> None:
    parser = probe_repo.Parser(description="Check one section folder against its repo profile.")
    parser.add_argument("--repo", required=True, help="Repo root or its code/ folder.")
    parser.add_argument("--folder", required=True, help="Section folder name under the sections directory, or a path.")
    parser.add_argument("--profile", help="Profile JSON from probe_repo.py. Probed when omitted.")
    parser.add_argument("--no-lint", action="store_true", help="Skip ESLint.")
    parser.add_argument("--mobile-pass", action="store_true", help="After a mobile pass: an ungated :hover reveal fails instead of warning.")
    args = parser.parse_args()
    result = check_section(load_profile(args.profile, args.repo), args.folder, lint=not args.no_lint, mobile_pass=args.mobile_pass)
    emit(result, 0 if result["pass"] else 6)


if __name__ == "__main__":
    try:
        main()
    except probe_repo.ProbeError as err:
        emit({"ok": False, "error": {"code": err.code, "message": err.message}}, err.exit_code)
    except SystemExit:
        raise
    except Exception:
        emit({"ok": False, "error": {"code": "INTERNAL", "message": "The check failed."}}, 99)
