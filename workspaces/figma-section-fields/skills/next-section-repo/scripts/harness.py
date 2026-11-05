#!/usr/bin/env python3
"""Render one section's Client<F>.js standalone in a browser page, bundled with esbuild. Never writes in the repo."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsread  # noqa: E402

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "harness.mjs"
FALLBACK_NODE_MODULES = Path("/home/dev/cli/figma-cli/node_modules")
REQUIRED_PACKAGES = ("react", "react-dom", "styled-components")
THEME_CANDIDATES = ("styles/theme/index.js", "styles/theme/index.ts", "styles/theme/index.mjs", "styles/theme.js")
BUNDLE_TIMEOUT = 300
GIT_TIMEOUT = 20

COMPONENT_STUB = """export default function {name}({{ className }}) {{
  return <div className={{className}} data-harness-stub="{name}"{style} />;
}}
"""
PLACEHOLDER_STYLE = " style={{ background: '#b8b8b8' }}"
FILE_STUBS = (
    ("MediaBackground", PLACEHOLDER_STYLE),
    ("ResponsiveImage", PLACEHOLDER_STYLE),
    ("Breadcrumbs", ""),
)
BARE_STUBS = {
    "next/font/local": """export default function localFont(options = {}) {
  const fallback = Array.isArray(options.fallback) && options.fallback.length ? options.fallback : ['sans-serif'];
  return { className: '', variable: '', style: { fontFamily: fallback.join(', ') } };
}
""",
    "next/image": """import { forwardRef } from 'react';
const Image = forwardRef(function Image({ src, alt = '', fill, priority, quality, placeholder, blurDataURL, loader, unoptimized, style, ...rest }, ref) {
  const url = typeof src === 'string' ? src : src?.src || src?.default?.src || undefined;
  const fillStyle = fill ? { position: 'absolute', inset: 0, width: '100%', height: '100%' } : null;
  return <img ref={ref} src={url} alt={alt} style={{ ...fillStyle, ...style }} {...rest} />;
});
export default Image;
""",
    "next/link": """import { forwardRef } from 'react';
const Link = forwardRef(function Link({ href, prefetch, replace, scroll, shallow, passHref, legacyBehavior, locale, children, ...rest }, ref) {
  const url = typeof href === 'string' ? href : href?.pathname || '#';
  return <a ref={ref} href={url} {...rest}>{children}</a>;
});
export default Link;
""",
    "server-only": "export {};\n",
}
INDEX_HTML = """<!doctype html>
<html lang="{lang}" dir="{dir}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>harness {folder}</title>
<style>body{{margin:0}}*,*::before,*::after{{box-sizing:border-box}}</style>
</head>
<body><div id="root"></div><script src="bundle.js"></script></body>
</html>
"""


class HarnessError(Exception):
    def __init__(self, code: str, message: str, exit_code: int, detail: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.detail = detail


def emit(payload: dict, exit_code: int = 0) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    raise SystemExit(exit_code)


def is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def package_root(repo: Path) -> Path:
    for candidate in (repo, *repo.parents):
        if (candidate / "package.json").is_file():
            return candidate
    return repo


def read_jsonc(path: Path) -> dict | None:
    try:
        text = jsread.strip_comments(path.read_text(encoding="utf-8"))
        data = json.loads(re.sub(r",(\s*[}\]])", r"\1", text))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def read_jsconfig(root: Path) -> dict:
    for name in ("jsconfig.json", "tsconfig.json"):
        path = root / name
        data = read_jsonc(path) if path.is_file() else None
        if data is not None:
            options = data.get("compilerOptions") or {}
            return {"file": str(path), "baseUrl": options.get("baseUrl"), "paths": options.get("paths") or {}}
    return {"file": None, "baseUrl": None, "paths": {}}


def has_packages(node_modules: Path) -> bool:
    return all((node_modules / name / "package.json").is_file() for name in REQUIRED_PACKAGES)


def git_lines(args: list[str], cwd: Path, runner=subprocess.run) -> list[str]:
    try:
        result = runner(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=GIT_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        return []
    return result.stdout.splitlines() if result.returncode == 0 else []


def worktree_roots(root: Path, runner=subprocess.run) -> tuple[Path | None, list[Path]]:
    top = git_lines(["rev-parse", "--show-toplevel"], root, runner)
    listed = [Path(line[len("worktree "):]) for line in git_lines(["worktree", "list", "--porcelain"], root, runner) if line.startswith("worktree ")]
    return (Path(top[0]) if top else None), listed


def find_node_modules(root: Path, runner=subprocess.run) -> tuple[Path, str]:
    for candidate in (root, *root.parents):
        if has_packages(candidate / "node_modules"):
            return candidate / "node_modules", "worktree"
    top, listed = worktree_roots(root, runner)
    if top is not None:
        relative = root.resolve().relative_to(top.resolve()) if is_within(root, top) else Path()
        for index, other in enumerate(listed):
            if other.resolve() == top.resolve():
                continue
            for base in (other / relative, other):
                if has_packages(base / "node_modules"):
                    return base / "node_modules", "main-checkout" if index == 0 else "other-worktree"
    raise HarnessError(
        "NO_NODE_MODULES",
        f"No node_modules with {', '.join(REQUIRED_PACKAGES)} at {root} or its parents, nor in any checkout from `git worktree list`. "
        "Install dependencies in the main checkout (npm ci) and run again.",
        4,
    )


def find_esbuild(node_modules: Path) -> tuple[Path, Path, str]:
    for base, source in ((node_modules, "repo"), (FALLBACK_NODE_MODULES, "figma-cli")):
        package = base / "esbuild"
        if (package / "package.json").is_file() and (package / "lib" / "main.js").is_file():
            binary = base / ".bin" / "esbuild"
            return package, binary if binary.exists() else package / "bin" / "esbuild", source
    raise HarnessError("NO_ESBUILD", f"No esbuild package in {node_modules} or {FALLBACK_NODE_MODULES}.", 4)


def find_theme(repo: Path, root: Path) -> Path | None:
    for base in (repo, root / "app", root):
        for name in THEME_CANDIDATES:
            if (base / name).is_file():
                return (base / name).resolve()
    return None


def stub_definitions() -> tuple[dict[str, str], list[dict]]:
    file_stubs = [
        {
            "name": name,
            "pattern": rf"/components/(?:.+/)?{name}(?:/|\.[jt]sx?$)",
            "source": COMPONENT_STUB.format(name=name, style=style),
        }
        for name, style in FILE_STUBS
    ]
    return dict(BARE_STUBS), file_stubs


def build_entry(client: Path, theme: Path | None, props: dict | None) -> str:
    theme_import = f"import theme from {json.dumps(str(theme))};" if theme else "const theme = {};"
    return "\n".join([
        "import { createElement } from 'react';",
        "import { createRoot } from 'react-dom/client';",
        "import { ThemeProvider } from 'styled-components';",
        theme_import,
        f"import Section from {json.dumps(str(client))};",
        f"const props = {json.dumps(props or {}, ensure_ascii=False)};",
        "createRoot(document.getElementById('root')).render(createElement(ThemeProvider, { theme }, createElement(Section, props)));",
        "",
    ])


def build_config(*, entry: str, out_dir: Path, node_modules: Path, esbuild_package: Path, jsconfig: dict, section_dir: Path) -> dict:
    bare, files = stub_definitions()
    return {
        "esbuildPackage": str(esbuild_package),
        "entry": {"contents": entry, "resolveDir": str(out_dir)},
        "outfile": str(out_dir / "bundle.js"),
        "nodePaths": [str(node_modules)],
        "tsconfig": jsconfig["file"],
        "sectionDir": str(section_dir) + os.sep,
        "bareStubs": bare,
        "fileStubs": files,
    }


def write_text(path: Path, text: str) -> None:
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run_bundle(config: dict, node: str, runner=subprocess.run) -> dict:
    try:
        result = runner([node, str(RUNNER)], input=json.dumps(config), capture_output=True, text=True, timeout=BUNDLE_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as err:
        raise HarnessError("BUNDLE_FAILED", f"esbuild did not finish in {BUNDLE_TIMEOUT}s.", 3) from err
    if result.returncode != 0:
        raise HarnessError("BUNDLE_FAILED", "esbuild could not bundle the section. Its errors are on stderr.", 3, result.stderr)
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as err:
        raise HarnessError("BUNDLE_FAILED", "The esbuild runner printed no result.", 3, result.stderr) from err


def load_props(path: str | None) -> dict | None:
    if path is None:
        return None
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise HarnessError("USAGE", f"--props is not a readable JSON file: {err}", 1) from err
    if not isinstance(data, dict):
        raise HarnessError("USAGE", "--props must hold one JSON object of component props.", 1)
    return data


def harness(args: argparse.Namespace, runner=subprocess.run) -> dict:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", args.folder):
        raise HarnessError("USAGE", "--folder must be a component folder name such as ImageGrid.", 1)
    repo = Path(args.repo).expanduser().resolve()
    if not (repo / "components").is_dir():
        raise HarnessError("USAGE", f"--repo {repo} has no components/ folder. Pass the app root.", 1)
    section_dir = (repo / (args.section_path or f"components/Sections/{args.folder}")).resolve()
    if not is_within(section_dir, repo):
        raise HarnessError("USAGE", "--section-path must stay inside --repo.", 1)
    client = section_dir / f"Client{args.folder}.js"
    if not client.is_file():
        raise HarnessError("USAGE", f"{client} does not exist.", 1)
    root = package_root(repo)
    out_dir = Path(args.out_dir).expanduser().resolve()
    if is_within(out_dir, root) or is_within(out_dir, repo):
        raise HarnessError("USAGE", f"--out-dir {out_dir} is inside the repo. Use the stage output folder.", 1)
    props = load_props(args.props)
    node = shutil.which("node")
    if node is None:
        raise HarnessError("NO_NODE", "node is not on PATH.", 4)

    node_modules, nm_source = find_node_modules(root, runner)
    esbuild_package, esbuild_bin, esbuild_source = find_esbuild(node_modules)
    jsconfig = read_jsconfig(root)
    theme = find_theme(repo, root)
    entry = build_entry(client, theme, props)

    out_dir.mkdir(parents=True, exist_ok=True)
    config = build_config(entry=entry, out_dir=out_dir, node_modules=node_modules, esbuild_package=esbuild_package, jsconfig=jsconfig, section_dir=section_dir)
    bundled = run_bundle(config, node, runner)
    write_text(out_dir / "index.html", INDEX_HTML.format(lang=args.lang, dir=args.dir, folder=args.folder))

    bare, files = stub_definitions()
    warnings = list(bundled.get("warnings") or [])
    if theme is None:
        warnings.append("No styles/theme/index.js was found, so the section renders with an empty theme and theme.bps is undefined.")
    record = {
        "level": "harness",
        "note": "Media (MediaBackground, ResponsiveImage) and Breadcrumbs are stubbed as plain divs, so this is not a Level 2 render.",
        "folder": args.folder,
        "client": str(client),
        "repo": str(repo),
        "packageRoot": str(root),
        "theme": str(theme) if theme else None,
        "jsconfig": jsconfig,
        "nodeModules": {"path": str(node_modules), "source": nm_source},
        "esbuild": {"package": str(esbuild_package), "binary": str(esbuild_bin), "source": esbuild_source},
        "props": str(Path(args.props).expanduser().resolve()) if args.props else None,
        "propsNote": None if args.props else "No --props: the component renders with its defaults. Sections with cards or lists need --props JSON.",
        "stubs": {"modules": sorted(bare), "components": [stub["name"] for stub in files]},
        "stubbed": bundled.get("stubsHit") or [],
        "files": {"index": str(out_dir / "index.html"), "bundle": str(out_dir / "bundle.js")},
        "warnings": warnings,
    }
    write_text(out_dir / "harness-record.json", json.dumps(record, ensure_ascii=False, indent=1) + "\n")
    return {
        "ok": True,
        "url": (out_dir / "index.html").as_uri(),
        "outDir": str(out_dir),
        "record": str(out_dir / "harness-record.json"),
        "stubbed": [hit["module"] for hit in record["stubbed"]],
        "nodeModules": record["nodeModules"],
        "warnings": warnings,
    }


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        emit({"ok": False, "error": {"code": "USAGE", "message": message}}, 1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = Parser(description="Bundle Client<F>.js with the repo's theme into a standalone page under --out-dir.")
    parser.add_argument("--repo", required=True, help="App root: the folder with components/ (package.json may be a parent).")
    parser.add_argument("--folder", required=True, help="Section folder name, e.g. ImageGrid.")
    parser.add_argument("--out-dir", required=True, help="Where index.html, bundle.js and harness-record.json go. Must be outside the repo.")
    parser.add_argument("--props", help="JSON file with one object of props for Client<F>. Default: none, so component defaults.")
    parser.add_argument("--section-path", help="Section folder relative to --repo. Default: components/Sections/<F>.")
    parser.add_argument("--dir", choices=("rtl", "ltr"), default="rtl", help="Page direction. Default: rtl.")
    parser.add_argument("--lang", default="he", help="Page lang attribute. Default: he.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    emit(harness(parse_args(argv)))


if __name__ == "__main__":
    try:
        main()
    except HarnessError as err:
        if err.detail:
            sys.stderr.write(err.detail if err.detail.endswith("\n") else err.detail + "\n")
        emit({"ok": False, "error": {"code": err.code, "message": err.message}}, err.exit_code)
    except SystemExit:
        raise
    except Exception as err:
        emit({"ok": False, "error": {"code": "INTERNAL", "message": f"The harness failed: {err}"}}, 99)
