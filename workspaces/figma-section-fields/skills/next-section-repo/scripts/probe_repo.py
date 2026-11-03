#!/usr/bin/env python3
"""Describe a Next.js section repo as a profile JSON. Reads files as text and never runs repo code."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsread  # noqa: E402

SCHEMA_VERSION = 1
FRAGMENT_ROLES = {
    "button": ("button", "buttonitem"),
    "mediaItem": ("mediaitem",),
    "mediaItemNew": ("mediaitemnew",),
    "responsiveMedia": ("responsivemediaitem",),
    "responsiveMediaNew": ("responsivemediaitemnew",),
    "backgroundFields": ("backgroundfields",),
    "layout": ("layout",),
    "seo": ("seo",),
}
SCAFFOLD_FILES = {
    "fragment": "{F}.gql",
    "serverComponent": "Server{F}.js",
    "index": "index.js",
    "component": "Client{F}.js",
    "styled": "Styled{F}.js",
}
CSS_NAMED = {"white": "#ffffff", "black": "#000000", "red": "#ff0000", "transparent": "#00000000"}
CHROME_CANDIDATES = (
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)


class ProbeError(Exception):
    def __init__(self, code: str, message: str, exit_code: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def emit(payload: dict, exit_code: int = 0) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    raise SystemExit(exit_code)


def app_root(repo: Path) -> Path:
    for candidate in (repo, repo / "code"):
        if (candidate / "package.json").is_file() and (candidate / "app").is_dir():
            return candidate.resolve()
    raise ProbeError("NOT_A_SECTION_REPO", "No folder with package.json and app/ was found at the repo or its code/ folder.", 2)


def read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def versions(root: Path, name: str, warnings: list[str]) -> dict:
    package = read_json(root / "package.json") or {}
    declared = None
    for key in ("dependencies", "devDependencies"):
        section = package.get(key) or {}
        if isinstance(section, dict) and name in section:
            declared = str(section[name])
    installed_pkg = read_json(root / "node_modules" / name / "package.json")
    installed = str(installed_pkg["version"]) if installed_pkg and "version" in installed_pkg else None
    if declared and installed:
        want = re.findall(r"\d+", declared)[:2]
        have = re.findall(r"\d+", installed)[:2]
        if want and have and want != have:
            warnings.append(f"{name} declares {declared} but {installed} is installed. Run npm install before trusting this repo's build.")
    elif declared and installed is None:
        warnings.append(f"{name} is declared ({declared}) but not installed.")
    return {"declared": declared, "installed": installed}


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def fragment_dirs(root: Path, warnings: list[str]) -> list[str]:
    text = jsread.read(root / "app" / "core.config.js")
    if not text:
        warnings.append("app/core.config.js was not found.")
        return []
    block = re.search(r"globalFragments\s*:\s*importAll\(\s*\[(.*?)\]\s*\)", text, re.S)
    if not block:
        warnings.append("globalFragments was not found in app/core.config.js.")
        return []
    dirs = []
    for spec in re.findall(r"require\.context\(\s*['\"]([^'\"]+)['\"]", block.group(1)):
        if spec.startswith("@/"):
            path = root / "app" / "components" / spec[2:]
        else:
            path = root / "app" / spec
        dirs.append(rel(root, path))
    return dirs


def gql_fragments(root: Path, dirs: list[str]) -> list[tuple[str, Path]]:
    """(fragment name, file) for every .gql under the given folders, global folders first."""
    seen = []
    for folder in dirs:
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.gql")):
            for name in re.findall(r"fragment\s+([A-Za-z_][A-Za-z0-9_]*)\s+on\b", jsread.read(path)):
                seen.append((name, path))
    return seen


def fragment_roles(root: Path, dirs: list[str]) -> dict:
    fragments = gql_fragments(root, dirs + ["app/components"])
    roles: dict = {}
    for role, names in FRAGMENT_ROLES.items():
        roles[role] = None
        for name, path in fragments:
            if name.lower() in names:
                roles[role] = {"name": name, "path": rel(root, path)}
                break
    return roles


def scaffold(root: Path, warnings: list[str], mixins: list[str]) -> list[str]:
    text = jsread.read(root / "ccTemplates" / "section.js")
    if not text:
        warnings.append("ccTemplates/section.js was not found. Using the common section file set.")
        return ["{F}.gql", "Server{F}.js", "index.js", "Client{F}.js", "Styled{F}.js"]
    exported = re.search(r"module\.exports\s*=\s*\{([^}]*)\}", text)
    names = [part.strip().split(":")[0].strip() for part in exported.group(1).split(",")] if exported else []
    files = [SCAFFOLD_FILES[name] for name in ("fragment", "serverComponent", "index", "component", "styled") if name in names]
    if "theme.mixins.layout" in text and "layout" not in mixins:
        warnings.append("ccTemplates/section.js uses theme.mixins.layout, but the theme registers no layout mixin.")
    return files


def normalize_color(value: str) -> str | None:
    value = value.strip().strip("'\"`").strip().lower()
    if value in CSS_NAMED:
        return CSS_NAMED[value]
    hex_match = re.fullmatch(r"#([0-9a-f]{3,8})", value)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) in (3, 4):
            digits = "".join(char * 2 for char in digits)
        if len(digits) in (6, 8):
            return "#" + digits
        return None
    rgba = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([0-9.]+)\s*)?\)", value)
    if rgba:
        r, g, b = (max(0, min(255, int(rgba.group(i)))) for i in (1, 2, 3))
        alpha = rgba.group(4)
        out = f"#{r:02x}{g:02x}{b:02x}"
        if alpha is not None and float(alpha) < 1:
            out += f"{round(float(alpha) * 255):02x}"
        return out
    return None


def flatten_colors(path: Path, text: str, body: str, prefix: str, out: dict, depth: int = 0) -> None:
    if depth > 4:
        return
    for entry in jsread.entries(body):
        if entry["kind"] == "spread":
            resolved = jsread.resolve_value(path, text, entry["key"])
            if resolved:
                flatten_colors(resolved[0], jsread.read(resolved[0]), resolved[1], prefix, out, depth + 1)
            continue
        key = prefix + entry["key"]
        value = entry["value"] or ""
        if value.startswith("{"):
            flatten_colors(path, text, value[1 : jsread.match_brace(value, 0)], key + ".", out, depth + 1)
            continue
        color = normalize_color(value)
        if color is not None:
            out[key] = color


def theme_info(root: Path, warnings: list[str]) -> dict:
    path = root / "app" / "styles" / "theme" / "index.js"
    text = jsread.read(path)
    info = {"mixins": [], "bps": [], "colors": {}, "fonts": []}
    if not text:
        warnings.append("app/styles/theme/index.js was not found.")
        return info
    body = jsread.default_export_object(text)
    if body is None:
        warnings.append("The theme's default export is not an object literal.")
        return info
    for entry in jsread.entries(body):
        if entry["key"] not in ("mixins", "bps", "colors"):
            continue
        resolved = jsread.resolve_value(path, text, entry["value"] or entry["key"])
        if resolved is None:
            warnings.append(f"theme.{entry['key']} could not be read.")
            continue
        module, part = resolved
        module_text = jsread.read(module)
        if entry["key"] == "colors":
            flatten_colors(module, module_text, part, "", info["colors"])
        else:
            info[entry["key"]] = jsread.object_keys(module, module_text, part)
    info["fonts"] = font_exports(root, warnings)
    return info


def font_exports(root: Path, warnings: list[str]) -> list[dict]:
    text = jsread.read(root / "app" / "styles" / "fonts" / "index.js")
    if not text:
        warnings.append("app/styles/fonts/index.js was not found.")
        return []
    fonts = []
    for match in re.finditer(r"export\s+const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*localFont\(", text):
        start = text.find("(", match.end() - 1)
        call = text[start : jsread.match_brace(text, start) + 1]
        files = []
        for src in re.findall(r"""(?:path|src)\s*:\s*['"]([^'"]+)['"]""", call):
            stem = Path(src).stem
            if stem not in files:
                files.append(stem)
        fonts.append({"export": match.group(1), "files": files})
    return fonts


def line_endings(root: Path, sections: Path) -> str:
    crlf = lf = 0
    for path in sorted(sections.glob("*/*.js"))[:80]:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        crlf += data.count(b"\r\n")
        lf += data.count(b"\n") - data.count(b"\r\n")
    return "crlf" if crlf > lf else "lf"


def eslint_info(root: Path, warnings: list[str]) -> dict:
    text = ""
    for name in (".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", "eslint.config.js", "eslint.config.mjs"):
        text = jsread.read(root / name)
        if text:
            break
    if not text:
        warnings.append("No ESLint config was found.")
        return {"schemaPath": None, "propTypes": None}
    schema = re.search(r"schema\s*:\s*['\"]([^'\"]+)['\"]", text)
    level = re.search(r"['\"]react/prop-types['\"]\s*:\s*\[?\s*['\"]?(\w+)", text)
    return {"schemaPath": schema.group(1) if schema else None, "propTypes": level.group(1) if level else None}


def app_sources(root: Path) -> list[Path]:
    paths = []
    for folder in ("app",):
        base = root / folder
        for path in base.rglob("*.js"):
            if "node_modules" in path.parts:
                continue
            paths.append(path)
    return paths


def code_facts(root: Path) -> dict:
    breadcrumbs = None
    uses_wp = False
    direction = None
    for path in app_sources(root):
        text = jsread.read(path)
        if breadcrumbs is None:
            match = re.search(r"rootData\??\.(?:SEO\??\.)?breadcrumbs", text)
            if match:
                breadcrumbs = match.group(0)
    uses_wp = (root / "app" / "hooks" / "useWP.js").is_file()
    global_style = jsread.read(root / "app" / "styles" / "GlobalStyle.js")
    match = re.search(r"direction\s*:\s*(rtl|ltr)", global_style)
    if match:
        direction = match.group(1)
    return {"breadcrumbs": breadcrumbs, "useWP": uses_wp, "pageDirection": direction}


def dev_info(root: Path, warnings: list[str], next_version: dict) -> tuple[dict, list[str]]:
    package = read_json(root / "package.json") or {}
    scripts = package.get("scripts") or {}
    script = scripts.get("dev")
    port = 3000
    if isinstance(script, str):
        found = re.search(r"(?:-p|--port)\s+(\d+)|PORT=(\d+)", script)
        if found:
            port = int(found.group(1) or found.group(2))
    lint = scripts.get("lint")
    major = re.findall(r"\d+", next_version.get("declared") or "")
    if isinstance(lint, str) and "next lint" in lint and major and int(major[0]) >= 16:
        warnings.append("package.json lint runs next lint, which Next 16 removed. Lint with npx eslint instead.")
    return {"script": script, "port": port}, ["npx", "eslint"]


def browser_path() -> str | None:
    override = os.environ.get("BCDP_CHROME")
    candidates = ([override] if override else []) + list(CHROME_CANDIDATES)
    candidates.append(str(Path.home() / ".cache" / "ms-playwright" / "chromium-1148" / "chrome-linux" / "chrome"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def probe(repo: Path) -> dict:
    warnings: list[str] = []
    root = app_root(repo)
    next_version = versions(root, "next", warnings)
    runtime = versions(root, "@colmobil/next", warnings)
    sections = root / "app" / "components" / "Sections"
    if not sections.is_dir():
        warnings.append("app/components/Sections was not found.")
    dirs = fragment_dirs(root, warnings)
    theme = theme_info(root, warnings)
    dev, lint = dev_info(root, warnings, next_version)
    profile = {
        "schemaVersion": SCHEMA_VERSION,
        "appRoot": str(root),
        "next": next_version,
        "runtime": runtime,
        "sectionsDir": rel(root, sections),
        "existingSections": sorted(path.name for path in sections.iterdir() if path.is_dir()) if sections.is_dir() else [],
        "globalFragmentDirs": dirs,
        "fragments": fragment_roles(root, dirs),
        "scaffold": {"files": scaffold(root, warnings, theme["mixins"])},
        "theme": theme,
        "eol": line_endings(root, sections) if sections.is_dir() else "lf",
        "eslint": eslint_info(root, warnings),
        "lintCommand": lint,
        **code_facts(root),
        "dev": dev,
        "browser": browser_path(),
    }
    return {"ok": True, "profile": profile, "warnings": warnings}


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        emit({"ok": False, "error": {"code": "USAGE", "message": message}}, 1)


def main() -> None:
    parser = Parser(description="Describe a Next.js section repo as a profile JSON.")
    parser.add_argument("--repo", required=True, help="Repo root or its code/ folder.")
    parser.add_argument("--out", help="Write the profile object to this file as well.")
    args = parser.parse_args()
    result = probe(Path(args.repo).expanduser())
    if args.out:
        write_atomic(Path(args.out).expanduser(), json.dumps(result["profile"], ensure_ascii=False, indent=1) + "\n")
    emit(result)


if __name__ == "__main__":
    try:
        main()
    except ProbeError as err:
        emit({"ok": False, "error": {"code": err.code, "message": err.message}}, err.exit_code)
    except SystemExit:
        raise
    except Exception:
        emit({"ok": False, "error": {"code": "INTERNAL", "message": "The probe failed."}}, 99)
