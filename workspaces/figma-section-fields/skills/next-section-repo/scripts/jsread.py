"""Read plain JavaScript object literals as text. Nothing here imports or runs repo code."""

from __future__ import annotations

import re
from pathlib import Path

IDENT = r"[A-Za-z_$][A-Za-z0-9_$]*"


def skip_string(text: str, index: int) -> int:
    """Index just past the string or template literal that starts at `index`."""
    quote = text[index]
    index += 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if quote == "`" and text.startswith("${", index):
            index = match_brace(text, index + 1) + 1
            continue
        if char == quote:
            return index + 1
        index += 1
    return index


def skip_comment(text: str, index: int) -> int:
    if text.startswith("//", index):
        end = text.find("\n", index)
        return len(text) if end == -1 else end
    if text.startswith("/*", index):
        end = text.find("*/", index + 2)
        return len(text) if end == -1 else end + 2
    return index


def match_brace(text: str, index: int) -> int:
    """Index of the bracket that closes the one at `index` ({, [ or ()."""
    pairs = {"{": "}", "[": "]", "(": ")"}
    stack = [pairs[text[index]]]
    index += 1
    while index < len(text) and stack:
        char = text[index]
        if char in "'\"`":
            index = skip_string(text, index)
            continue
        if text.startswith("//", index) or text.startswith("/*", index):
            index = skip_comment(text, index)
            continue
        if char in pairs:
            stack.append(pairs[char])
        elif char == stack[-1]:
            stack.pop()
            if not stack:
                return index
        index += 1
    return len(text) - 1


def split_top(body: str) -> list[str]:
    """Split an object or array body at top-level commas."""
    parts: list[str] = []
    depth = 0
    start = 0
    index = 0
    while index < len(body):
        char = body[index]
        if char in "'\"`":
            index = skip_string(body, index)
            continue
        if body.startswith("//", index) or body.startswith("/*", index):
            index = skip_comment(body, index)
            continue
        if char in "{[(":
            depth += 1
        elif char in "}])":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(body[start:index])
            start = index + 1
        index += 1
    parts.append(body[start:])
    return [part for part in (strip_comments(p).strip() for p in parts) if part]


def strip_comments(text: str) -> str:
    out = []
    index = 0
    while index < len(text):
        if text[index] in "'\"`":
            end = skip_string(text, index)
            out.append(text[index:end])
            index = end
            continue
        if text.startswith("//", index) or text.startswith("/*", index):
            index = skip_comment(text, index)
            continue
        out.append(text[index])
        index += 1
    return "".join(out)


def entries(body: str) -> list[dict]:
    """Top-level entries of an object body: {kind: key|spread|shorthand, key, value}."""
    found = []
    for part in split_top(body):
        if part.startswith("..."):
            found.append({"kind": "spread", "key": part[3:].strip(), "value": None})
            continue
        match = re.match(r"""^(?:(['"])(.*?)\1|(\[?[A-Za-z0-9_$]+\]?))\s*:\s*(.*)$""", part, re.S)
        if match:
            key = match.group(2) if match.group(1) else match.group(3)
            found.append({"kind": "key", "key": key, "value": match.group(4).strip()})
            continue
        method = re.match(rf"^({IDENT})\s*\(", part)
        if method:
            found.append({"kind": "key", "key": method.group(1), "value": None})
            continue
        if re.fullmatch(IDENT, part):
            found.append({"kind": "shorthand", "key": part, "value": part})
    return found


def object_after(text: str, pattern: str) -> str | None:
    """Body of the first object literal after a regex match, or None."""
    match = re.search(pattern, text)
    if not match:
        return None
    start = text.find("{", match.end() - 1)
    if start == -1:
        return None
    return text[start + 1 : match_brace(text, start)]


def default_export_object(text: str) -> str | None:
    direct = object_after(text, r"export\s+default\s*\{")
    if direct is not None:
        return direct
    named = re.search(rf"export\s+default\s+({IDENT})\s*;?", text)
    if named:
        return binding_object(text, named.group(1))
    return None


def binding_object(text: str, name: str) -> str | None:
    return object_after(text, rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*\{{")


def imports(text: str) -> dict[str, tuple[str, str]]:
    """Local name to (module specifier, imported name or 'default' or '*')."""
    found: dict[str, tuple[str, str]] = {}
    for match in re.finditer(r"import\s+([^;]+?)\s+from\s+['\"]([^'\"]+)['\"]", text):
        clause, spec = match.group(1).strip(), match.group(2)
        star = re.match(rf"\*\s+as\s+({IDENT})", clause)
        if star:
            found[star.group(1)] = (spec, "*")
            continue
        default = re.match(rf"({IDENT})\s*(?:,|$)", clause)
        if default:
            found[default.group(1)] = (spec, "default")
        braces = re.search(r"\{([^}]*)\}", clause)
        if braces:
            for item in braces.group(1).split(","):
                item = item.strip()
                if not item:
                    continue
                parts = re.split(r"\s+as\s+", item)
                found[parts[-1].strip()] = (spec, parts[0].strip())
    return found


def resolve_module(base: Path, spec: str) -> Path | None:
    if not spec.startswith("."):
        return None
    target = (base.parent / spec).resolve()
    for candidate in (target, target.with_suffix(".js"), target / "index.js"):
        if candidate.is_file():
            return candidate
    return None


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def resolve_value(path: Path, text: str, value: str, depth: int = 0) -> tuple[Path, str] | None:
    """Object body that `value` stands for: an inline literal, a local binding, or an import."""
    if depth > 4:
        return None
    value = value.strip()
    if value.startswith("{"):
        return path, value[1 : match_brace(value, 0)]
    if not re.fullmatch(IDENT, value):
        return None
    local = binding_object(text, value)
    if local is not None:
        return path, local
    source = imports(text).get(value)
    if not source:
        return None
    module = resolve_module(path, source[0])
    if module is None:
        return None
    module_text = read(module)
    if source[1] == "default":
        body = default_export_object(module_text)
    else:
        body = object_after(module_text, rf"export\s+(?:const|let|var)\s+{re.escape(source[1])}\s*=\s*\{{")
    return (module, body) if body is not None else None


def object_keys(path: Path, text: str, body: str, depth: int = 0) -> list[str]:
    """Keys of an object, following top-level spreads into imported objects."""
    keys: list[str] = []
    for entry in entries(body):
        if entry["kind"] == "spread":
            resolved = resolve_value(path, text, entry["key"], depth + 1)
            if resolved:
                keys.extend(object_keys(resolved[0], read(resolved[0]), resolved[1], depth + 1))
            continue
        if entry["key"] not in keys:
            keys.append(entry["key"])
    return keys
