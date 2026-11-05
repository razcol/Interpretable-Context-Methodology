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
IDENT = jsread.IDENT
BPS_DESKTOP = re.compile(r"\bbps\??\.desktop\b")
BPS_MOBILE = re.compile(r"\bbps\??\.mobile\b")
HOVER_MEDIA = re.compile(r"@media[^{]*\(\s*hover\s*:\s*hover\s*\)")
REVEAL_PROPS = {"opacity", "grid-template-rows", "display", "max-height", "visibility"}
CSS_TAG = re.compile(r"(?:\bcss|\bstyled(?:\.\w+|\([^()]*\))(?:\.attrs\((?:[^()]|\([^()]*\))*\))?|\bcreateGlobalStyle|\bkeyframes)\s*$")
CSS_HELPER = re.compile(rf"(?:const|let|var)\s+({IDENT})\s*=\s*(?:(?:\([^()]*\)|{IDENT})\s*=>\s*)?css\s*$")


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


def resolve_spec(root: Path, base: Path, spec: str) -> Path | None:
    """File an import specifier points to: relative, `@/` (app/components) or baseUrl (app/)."""
    if spec.startswith("."):
        return jsread.resolve_module(base, spec)
    app = root / "app"
    target = app / "components" / spec[2:] if spec.startswith("@/") else app / spec
    for candidate in (target.with_name(target.name + ".js"), target / "index.js", target):
        if candidate.is_file():
            return candidate
    return None


def exported_object(path: Path, name: str) -> str | None:
    text = jsread.read(path)
    if name == "default":
        return jsread.default_export_object(text)
    return jsread.object_after(text, rf"export\s+(?:const|let|var)\s+{re.escape(name)}\s*=\s*\{{")


def theme_object(root: Path, sources: list[tuple[Path, str]]) -> tuple[Path, str] | None:
    """(module, object body) of the theme passed to ThemeProvider, else the default export of styles/theme."""
    for path, text in sources:
        match = re.search(rf"<ThemeProvider\b[^>]*?\btheme=\{{\s*({IDENT})\s*\}}", text)
        if not match:
            continue
        local = jsread.binding_object(text, match.group(1))
        if local is not None:
            return path, local
        source = jsread.imports(text).get(match.group(1))
        module = resolve_spec(root, path, source[0]) if source else None
        body = exported_object(module, source[1]) if module else None
        if body is not None:
            return module, body
    path = root / "app" / "styles" / "theme" / "index.js"
    body = jsread.default_export_object(jsread.read(path))
    return (path, body) if body is not None else None


def number_entries(path: Path, text: str, name: str) -> dict:
    resolved = jsread.resolve_value(path, text, name)
    if resolved is None:
        return {}
    numbers = {}
    for entry in jsread.entries(resolved[1]):
        if entry["kind"] == "key" and re.fullmatch(r"-?\d+(?:\.\d+)?", entry["value"] or ""):
            value = float(entry["value"])
            numbers[entry["key"]] = int(value) if value.is_integer() else value
    return numbers


def bps_media(path: Path, text: str, body: str) -> tuple[dict, dict]:
    """(bps key to media string with `${obj.key}` substituted, breakpoint numbers the strings use)."""
    tables: dict[str, dict] = {}

    def lookup(match: re.Match) -> str:
        table = tables.setdefault(match.group(1), number_entries(path, text, match.group(1)))
        value = table.get(match.group(2))
        return str(value) if value is not None else match.group(0)

    media: dict = {}
    for entry in jsread.entries(body):
        if entry["kind"] != "key":
            continue
        value = (entry["value"] or "").strip()
        if len(value) < 2 or value[0] not in "'\"`" or value[-1] != value[0]:
            media[entry["key"]] = None
            continue
        substituted = re.sub(rf"\$\{{\s*({IDENT})\.({IDENT})\s*\}}", lookup, value[1:-1])
        media[entry["key"]] = re.sub(r"\s+", " ", substituted).strip()
    breakpoints: dict = {}
    for table in tables.values():
        breakpoints.update(table)
    return media, breakpoints


def bps_overlap(media: dict) -> str | None:
    """Width range where bps.desktop and bps.mobile both match, for example "1279px", or None."""
    desktop = re.search(r"min-width\s*:\s*(\d+(?:\.\d+)?)px", (media or {}).get("desktop") or "")
    mobile = re.search(r"max-width\s*:\s*(\d+(?:\.\d+)?)px", (media or {}).get("mobile") or "")
    if not desktop or not mobile:
        return None
    low, high = float(desktop.group(1)), float(mobile.group(1))
    if low > high:
        return None
    low_text, high_text = f"{low:g}px", f"{high:g}px"
    return low_text if low == high else f"{low_text}-{high_text}"


def theme_info(root: Path, sources: list[tuple[Path, str]], warnings: list[str]) -> dict:
    info = {"mixins": [], "bps": [], "bpsMedia": {}, "breakpoints": {}, "layoutHeights": [], "colors": {}, "fonts": []}
    found = theme_object(root, sources)
    if found is None:
        warnings.append("No theme object was found for ThemeProvider or in app/styles/theme/index.js.")
        return info
    path, body = found
    text = jsread.read(path)
    for entry in jsread.entries(body):
        if entry["key"] not in ("mixins", "bps", "colors", "layoutHeights"):
            continue
        resolved = jsread.resolve_value(path, text, entry["value"] or entry["key"])
        if resolved is None:
            warnings.append(f"theme.{entry['key']} could not be read.")
            continue
        module, part = resolved
        module_text = jsread.read(module)
        if entry["key"] == "colors":
            flatten_colors(module, module_text, part, "", info["colors"])
            continue
        info[entry["key"]] = jsread.object_keys(module, module_text, part)
        if entry["key"] == "bps":
            info["bpsMedia"], info["breakpoints"] = bps_media(module, module_text, part)
    overlap = bps_overlap(info["bpsMedia"])
    if overlap:
        warnings.append(f"bps.desktop and bps.mobile both match at {overlap}")
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


def css_templates(text: str) -> list[tuple[str | None, str]]:
    """(helper name or None, body) of every top-level css`` / styled.x`` template in a file."""
    found = []
    index = 0
    while index < len(text):
        char = text[index]
        if text.startswith("//", index) or text.startswith("/*", index):
            index = jsread.skip_comment(text, index)
            continue
        if char in "'\"`":
            end = jsread.skip_string(text, index)
            prefix = text[max(0, index - 300) : index]
            if char == "`" and CSS_TAG.search(prefix):
                helper = CSS_HELPER.search(prefix)
                found.append((helper.group(1) if helper else None, text[index + 1 : end - 1]))
            index = end
            continue
        index += 1
    return found


def css_tree(body: str) -> dict:
    """Nested rule blocks of a template body: {header, decls[(prop, value)], mixins[raw ${}], children}.

    A `${...}` on its own line is a mixin. One in a selector or a value stays in that text."""
    root = {"header": "", "decls": [], "mixins": [], "children": [], "parent": None}
    node = root
    buffer = ""
    index = 0

    def flush() -> None:
        part = buffer.strip()
        if ":" in part:
            prop, value = part.split(":", 1)
            node["decls"].append((prop.strip().lower(), value.strip()))

    while index < len(body):
        char = body[index]
        if body.startswith("${", index):
            end = jsread.match_brace(body, index + 1) + 1
            raw = body[index:end]
            after = re.match(r"[ \t]*(;|\n|\}|$)", body[end:])
            if not buffer.strip() and after:
                node["mixins"].append(raw)
                if after.group(1) == ";":
                    end += after.end()
            else:
                buffer += raw
            index = end
            continue
        if body.startswith("/*", index):
            index = jsread.skip_comment(body, index)
            continue
        if char in "'\"":
            end = jsread.skip_string(body, index)
            buffer += body[index:end]
            index = end
            continue
        if char == "{":
            child = {"header": buffer.strip(), "decls": [], "mixins": [], "children": [], "parent": node}
            node["children"].append(child)
            node = child
            buffer = ""
        elif char == ";":
            flush()
            buffer = ""
        elif char == "}":
            flush()
            buffer = ""
            node = node["parent"] or root
        else:
            buffer += char
        index += 1
    return root


def css_walk(node: dict, context: tuple = ()):
    """Each block with the headers of its ancestors and itself."""
    here = context + ((node["header"],) if node["header"] else ())
    yield node, here
    for child in node["children"]:
        yield from css_walk(child, here)


def descendants(node: dict) -> int:
    return sum(1 + descendants(child) for child in node["children"])


def reveal_decl(prop: str, value: str) -> bool:
    """Whether a declaration shows something: opacity 1, display not none, and so on. A dim or a fade-out is not a reveal."""
    value = value.replace("!important", "").strip().lower()
    if prop not in REVEAL_PROPS or "${" in value:
        return False
    if prop == "opacity":
        return value in ("1", "1.0", "100%")
    if prop == "display":
        return value != "none"
    if prop == "visibility":
        return value == "visible"
    if prop == "max-height":
        return value not in ("0", "0px", "none")
    return re.search(r"(?<![\d.])(?!0fr)\d*\.?\d+fr|auto|min-content|max-content|px|%", value) is not None


def reveals(node: dict, helpers: dict) -> bool:
    for block, _ in css_walk(node):
        if any(reveal_decl(prop, value) for prop, value in block["decls"]):
            return True
        for raw in block["mixins"]:
            name = re.match(rf"\$\{{\s*({IDENT})", raw)
            if name and name.group(1) in helpers and helpers[name.group(1)]["reveals"]:
                return True
    return False


def hover_rules(text: str) -> list[dict]:
    """Every :hover rule in a Styled file: {selector, reveals, context (enclosing headers)}.

    Rules inside a named css`` helper count once per place the helper is interpolated."""
    templates = [(name, css_tree(body)) for name, body in css_templates(text)]
    helpers: dict = {}
    for name, tree in templates:
        if name:
            helpers[name] = {"tree": tree, "reveals": False}
    for name in helpers:
        helpers[name]["reveals"] = reveals(helpers[name]["tree"], helpers)
    rules = []
    uses: dict[str, list[tuple]] = {}
    for name, tree in templates:
        for block, context in css_walk(tree):
            if ":hover" in block["header"]:
                rules.append({"selector": block["header"], "reveals": reveals(block, helpers), "context": context, "helper": name})
            for raw in block["mixins"]:
                called = re.match(rf"\$\{{\s*({IDENT})\s*(\()?", raw)
                if not called or called.group(1) not in helpers:
                    continue
                uses.setdefault(called.group(1), []).append(context)
                if called.group(2) and ":hover" in raw:
                    rules.append({"selector": raw, "reveals": helpers[called.group(1)]["reveals"], "context": context, "helper": name})
    expanded = []
    for rule in rules:
        if rule["helper"] is None:
            expanded.append(rule)
            continue
        for use in uses.get(rule["helper"], []):
            expanded.append({**rule, "context": use + rule["context"], "helper": None})
    return expanded


def hover_gated(context: tuple, gate: str | None) -> bool:
    if any(HOVER_MEDIA.search(header) for header in context):
        return True
    return gate != "hover-media" and any(BPS_DESKTOP.search(header) for header in context)


def mobile_info(root: Path, sources: list[tuple[Path, str]], sections: Path) -> dict:
    app = root / "app"
    hooks: dict[str, int] = {}
    responsive = []
    icon_dirs = set()
    for path, text in sources:
        for match in re.finditer(r"import\s+([^;]+?)\s+from\s+['\"]([^'\"]+)['\"]", text):
            if not re.search(r"\buseIsMobile\b", match.group(1)):
                continue
            spec = match.group(2)
            if spec.startswith("."):
                target = jsread.resolve_module(path, spec)
                if target is not None and app in target.parents:
                    spec = re.sub(r"(?:/index)?\.js$", "", str(target.relative_to(app.resolve())))
            hooks[spec] = hooks.get(spec, 0) + 1
        if path.name == "ResponsiveImage.js" or (path.name == "index.js" and path.parent.name == "ResponsiveImage"):
            responsive.append(rel(root, path))
        if "Icon" in path.stem and "<svg" in text:
            icon_dirs.add(rel(root, path.parent))
    styled = [jsread.read(path) for path in sorted(sections.rglob("Styled*.js"))] if sections.is_dir() else []
    gate = None
    if any(HOVER_MEDIA.search(text) for text in styled):
        gate = "hover-media"
    elif any(any(BPS_DESKTOP.search(h) for h in rule["context"]) for text in styled for rule in hover_rules(text)):
        gate = "bps-desktop"
    responsive.sort(key=lambda value: (0 if "/Core/" in value else 1, len(value), value))
    return {
        "hook": [{"import": spec, "count": count} for spec, count in sorted(hooks.items(), key=lambda item: (-item[1], item[0]))],
        "responsiveImage": responsive[0] if responsive else None,
        "hoverGate": gate,
        "icons": {"publicIcons": "public/icons" if (root / "public" / "icons").is_dir() else None, "inline": sorted(icon_dirs)},
    }


def code_facts(root: Path, sources: list[tuple[Path, str]]) -> dict:
    breadcrumbs = None
    uses_wp = False
    direction = None
    for path, text in sources:
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
    sources = [(path, jsread.read(path)) for path in sorted(app_sources(root), key=lambda path: (len(path.parts), str(path)))]
    theme = theme_info(root, sources, warnings)
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
        **code_facts(root, sources),
        "mobile": mobile_info(root, sources, sections),
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
