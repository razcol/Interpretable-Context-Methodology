#!/usr/bin/env python3
"""Map the files a branch changed to the app routes that render them.

Usage:
  review_urls.py --app-root <dir> --base <ref> [--port N] [--test-route /path]

Changed files are everything that differs from the merge base with <ref>, committed
or not, plus untracked files. Imports are followed backwards (relative paths and the
jsconfig/tsconfig `paths` and `baseUrl`) until they reach `page.*` or `layout.*`
files under app/.

Each changed file gets a kind:
  static         a page with a fixed route, for example /showrooms
  dynamic        a page with [param] segments; the route keeps the brackets
  wordpress      reached only through a catch-all page, so any CMS page may show it
  section        under components/Sections/, loaded by the CMS, shown on pages that use it
  template       under components/Templates/, a CMS page template, shown on pages that use it
  all-pages      reached from the root layout
  unmapped       no page found

A route is marked `sharedStringsOnly` when every changed file that reaches it is a
locale JSON file (under i18n/, locale(s)/, lang/, messages/ or translations/) and none
of the changed keys is used by the route's page, its layouts, or anything they import.
Those routes are listed at the top level and left out of `urls`. When a locale file
cannot be compared (missing at the merge base, or not valid JSON), nothing is marked.

Prints one JSON object. `urls` lists localhost URLs that can be opened as they are.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

CODE_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
RESOLVE_EXT = CODE_EXT + (".css", ".scss", ".json", ".gql", ".graphql")
IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^'"]*?\s+from\s+)?|export\s+[^'"]*?\s+from\s+|import\s*\(\s*|require\s*\(\s*)['"]([^'"]+)['"]""")
PAGE_RE = re.compile(r"^(page|layout)\.(js|jsx|ts|tsx|mdx)$")
LAYOUT_NAMES = [f"layout.{e}" for e in ("js", "jsx", "ts", "tsx", "mdx")]
LOCALE_DIRS = {"i18n", "locale", "locales", "lang", "messages", "translations"}
BINDING_RE = re.compile(
    r"""import\s+(?:\*\s+as\s+)?([A-Za-z_$][\w$]*)\s+from\s+['"]([^'"]+)['"]"""
    r"""|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
IMPORT_STMT_RE = re.compile(
    r"""import\s+[^'";]*?\s+from\s+['"][^'"]+['"]"""
    r"""|(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*require\s*\(\s*['"][^'"]+['"]\s*\)""")


def git(app_root, *args):
    res = subprocess.run(["git", "-C", app_root, *args], capture_output=True, text=True)
    if res.returncode != 0:
        print(json.dumps({"ok": False, "error": res.stderr.strip()[:300]}))
        sys.exit(2)
    return res.stdout


def changed_files(app_root, base):
    merge_base = git(app_root, "merge-base", base, "HEAD").strip()
    names = set(git(app_root, "diff", "--name-only", "--relative", merge_base).split())
    names |= set(git(app_root, "ls-files", "--others", "--exclude-standard").split())
    return merge_base, sorted(n for n in names if (Path(app_root) / n).exists())


def read_config(app_root):
    for name in ("jsconfig.json", "tsconfig.json"):
        p = Path(app_root, name)
        if p.exists():
            text = re.sub(r"(?m)//.*$", "", p.read_text())
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            text = re.sub(r",(\s*[}\]])", r"\1", text)
            try:
                opts = json.loads(text).get("compilerOptions", {})
            except ValueError:
                return Path(app_root), {}
            return Path(app_root, opts.get("baseUrl", ".")).resolve(), opts.get("paths") or {}
    return Path(app_root), {}


def resolve_file(base):
    candidates = [base] + [base.with_name(base.name + e) for e in RESOLVE_EXT] + [base / f"index{e}" for e in CODE_EXT]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    return None


class Resolver:
    def __init__(self, app_root):
        self.app_root = Path(app_root).resolve()
        self.base_url, self.paths = read_config(app_root)

    def resolve(self, spec, importer):
        if spec.startswith("."):
            return resolve_file((importer.parent / spec))
        for pattern, targets in self.paths.items():
            if pattern.endswith("/*") and spec.startswith(pattern[:-1]):
                rest = spec[len(pattern) - 1:]
                for t in targets:
                    hit = resolve_file(self.base_url / t.replace("*", rest))
                    if hit:
                        return hit
            elif spec == pattern:
                for t in targets:
                    hit = resolve_file(self.base_url / t)
                    if hit:
                        return hit
        return resolve_file(self.base_url / spec)


def is_locale(name):
    p = Path(name)
    return p.suffix.lower() == ".json" and any(part.lower() in LOCALE_DIRS for part in p.parts[:-1])


def flatten(value, prefix=""):
    if isinstance(value, dict):
        leaves = {}
        for k, v in value.items():
            leaves.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        return leaves
    return {prefix: value}


def changed_keys(app_root, merge_base, name):
    """Dotted leaf keys added, removed or changed since the merge base, or None when it cannot tell."""
    old = subprocess.run(["git", "-C", app_root, "show", f"{merge_base}:./{name}"], capture_output=True, text=True)
    if old.returncode != 0:
        return None
    try:
        before = flatten(json.loads(old.stdout))
        after = flatten(json.loads(Path(app_root, name).read_text()))
    except (OSError, ValueError):
        return None
    missing = object()
    return sorted(k for k in before.keys() | after.keys() if before.get(k, missing) != after.get(k, missing))


def key_used(text, binding, key):
    """True when the text may read the key. When it cannot tell, the key counts as used."""
    if any(f"{q}{key}{q}" in text for q in "'\"`") or f".{key}" in text:
        return True
    if not binding:
        return False
    b = re.escape(binding)
    parts = key.split(".")
    for i in range(1, len(parts) + 1):
        if re.search(rf"(?<![\w$.]){b}\.{re.escape('.'.join(parts[:i]))}(?![\w$.])", text):
            return True
    if re.search(rf"(?<![\w$.]){b}\s*(?:\?\.\s*)?\[", text):
        return True
    return bool(re.search(rf"(?<![\w$.]){b}(?![\w$])(?!\s*\.)", IMPORT_STMT_RE.sub("", text)))


def binding_of(text, path, locale, resolver):
    for m in BINDING_RE.finditer(text):
        name, spec = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        if resolver.resolve(spec, path) == locale:
            return name
    return None


def ancestor_layouts(file, app_dir):
    found, cur = [], file.parent
    while cur.is_relative_to(app_dir):
        found += [cur / n for n in LAYOUT_NAMES if (cur / n).is_file()]
        if cur == app_dir:
            break
        cur = cur.parent
    return found


def uses_changed_keys(starts, locales, forward, resolver, cache):
    """locales maps a resolved locale file to its changed keys."""
    seen, queue = set(starts), deque(starts)
    while queue:
        cur = queue.popleft()
        for nxt in forward.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    for path in seen:
        if not path.name.endswith(CODE_EXT):
            continue
        if path not in cache:
            try:
                cache[path] = path.read_text(errors="replace")
            except OSError:
                cache[path] = ""
        text = cache[path]
        for locale, keys in locales.items():
            binding = binding_of(text, path, locale, resolver)
            if binding is None and locale in forward.get(path, ()):
                return True
            if any(key_used(text, binding, k) for k in keys):
                return True
    return False


def build_reverse_graph(app_root, resolver):
    app_dir = Path(app_root, "app").resolve()
    reverse, forward = {}, {}
    for dirpath, dirnames, filenames in os.walk(app_dir):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".next")]
        for name in filenames:
            if not name.endswith(CODE_EXT):
                continue
            path = Path(dirpath, name).resolve()
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            for spec in IMPORT_RE.findall(text):
                target = resolver.resolve(spec, path)
                if target:
                    reverse.setdefault(target, set()).add(path)
                    forward.setdefault(path, set()).add(target)
    return app_dir, reverse, forward


def route_of(page, app_dir):
    parts = list(page.relative_to(app_dir).parts[:-1])
    kind, segments = "static", []
    for part in parts:
        if part.startswith("(") and part.endswith(")") or part.startswith("@"):
            continue
        if part.startswith("[[...") or part.startswith("[..."):
            kind = "wordpress" if "(pages)" in parts else "dynamic"
            segments.append(part)
        elif part.startswith("["):
            kind = "dynamic"
            segments.append(part)
        else:
            segments.append(part)
    return "/" + "/".join(segments), kind


def classify(file, app_dir, reverse):
    rel = file.relative_to(app_dir) if file.is_relative_to(app_dir) else None
    if rel and len(rel.parts) > 3 and rel.parts[0] == "components" and rel.parts[1] in ("Sections", "Templates"):
        kind = "section" if rel.parts[1] == "Sections" else "template"
        return {"kind": kind, kind: rel.parts[2], "routes": [], "_pages": {}}

    pages, layouts, seen = set(), set(), {file}
    queue = deque([file])
    while queue:
        cur = queue.popleft()
        if cur.is_relative_to(app_dir) and PAGE_RE.match(cur.name):
            (pages if cur.name.startswith("page.") else layouts).add(cur)
            if cur.name.startswith("page."):
                continue
        for importer in reverse.get(cur, ()):
            if importer not in seen:
                seen.add(importer)
                queue.append(importer)

    routes = sorted({route_of(p, app_dir) for p in pages})
    behind = {}
    root_layout = any(l.parent == app_dir for l in layouts)
    if root_layout and not pages:
        behind["/"] = {l for l in layouts if l.parent == app_dir}
        return {"kind": "all-pages", "routes": [{"route": "/", "kind": "all-pages"}], "_pages": behind}
    if pages:
        for p in pages:
            behind.setdefault(route_of(p, app_dir)[0], set()).add(p)
    elif layouts:
        routes = sorted({(route_of(l, app_dir)[0], "layout") for l in layouts})
        for l in layouts:
            behind.setdefault(route_of(l, app_dir)[0], set()).add(l)
    if not routes:
        return {"kind": "unmapped", "routes": [], "_pages": {}}
    kinds = {k for _, k in routes}
    kind = "static" if "static" in kinds else sorted(kinds)[0]
    return {"kind": kind, "routes": [{"route": r, "kind": k} for r, k in routes], "_pages": behind}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app-root", required=True, help="folder with package.json and app/")
    ap.add_argument("--base", default="origin/dev", help="branch the work started from")
    ap.add_argument("--port", type=int, default=3000)
    ap.add_argument("--test-route", help="repo test page for CMS sections, from targets/repos.md")
    args = ap.parse_args()

    app_root = os.path.realpath(args.app_root)
    merge_base, files = changed_files(app_root, args.base)
    resolver = Resolver(app_root)
    app_dir, reverse, forward = build_reverse_graph(app_root, resolver)

    results, behind, reach = [], {}, {}
    for name in files:
        info = classify(Path(app_root, name).resolve(), app_dir, reverse)
        for route, found in info.pop("_pages").items():
            behind.setdefault(route, set()).update(found)
        if is_locale(name):
            info["changedKeys"] = changed_keys(app_root, merge_base, name)
        for r in info["routes"]:
            reach.setdefault(r["route"], set()).add(name)
        results.append({"file": name, **info})

    by_name = {r["file"]: r for r in results}
    shared_only, cache = set(), {}
    for route, names in reach.items():
        if not all(is_locale(n) and by_name[n].get("changedKeys") is not None for n in names):
            continue
        starts = set()
        for f in behind.get(route, ()):
            starts.add(f)
            starts.update(ancestor_layouts(f, app_dir))
        if not starts:
            continue
        locales = {Path(app_root, n).resolve(): by_name[n]["changedKeys"] for n in names}
        if not uses_changed_keys(starts, locales, forward, resolver, cache):
            shared_only.add(route)

    urls = []
    for info in results:
        for r in info["routes"]:
            if r["route"] in shared_only:
                r["sharedStringsOnly"] = True
            elif r["kind"] in ("static", "all-pages") and "[" not in r["route"]:
                urls.append(r["route"])
        if info["kind"] in ("section", "wordpress") and args.test_route:
            urls.append(args.test_route)

    base = f"http://localhost:{args.port}"
    print(json.dumps({
        "ok": True,
        "appRoot": app_root,
        "mergeBase": merge_base,
        "changed": len(files),
        "files": results,
        "urls": [base + u for u in dict.fromkeys(urls)],
        "sharedStringsOnly": sorted(shared_only),
        "needsAnswer": sorted({r["file"] for r in results if r["kind"] in ("dynamic", "wordpress", "section", "template", "unmapped")}),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
