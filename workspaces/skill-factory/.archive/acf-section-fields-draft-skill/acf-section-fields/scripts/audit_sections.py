#!/usr/bin/env python3
"""Compare section files with the Jaecoo / luxury-trade ACF frontend contract.

Prints a JSON report. With --md, also writes the production audit.
Field groups are not in these repos. A matching .gql file means the frontend
expects the layout; it does not mean a WordPress environment already has it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


IGNORED_PROPS = {"order", "rootData", "className", "children", "key", "style", "index"}
REUSE_FRAGMENTS = {
    "Layout",
    "ButtonItem",
    "MediaItem",
    "ResponsiveMediaItem",
    "ResponsiveFullMediaItem",
}


def pascal(value: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", value)
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


def label_from(name: str) -> str:
    chars = []
    for index, char in enumerate(name):
        if char in {"_", "-"}:
            chars.append(" ")
        elif char.isupper() and index:
            chars.append(" ")
            chars.append(char)
        else:
            chars.append(char)
    return " ".join("".join(chars).split()).title()


def extract_brace(text: str, start: int) -> str:
    depth = 0
    i = start
    in_string = None
    while i < len(text):
        char = text[i]
        if in_string:
            if char == "\\":
                i += 2
                continue
            if char == in_string:
                in_string = None
        elif char in {'"', "'"}:
            in_string = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i]
        i += 1
    raise ValueError("Unclosed brace")


class SelectionParser:
    def __init__(self, text: str):
        self.text = text
        self.n = len(text)
        self.i = 0

    def skip(self) -> None:
        while self.i < self.n:
            if self.text[self.i].isspace():
                self.i += 1
                continue
            if self.text.startswith("#", self.i):
                self.i = self.text.find("\n", self.i)
                if self.i < 0:
                    self.i = self.n
                continue
            break

    def peek(self) -> str:
        self.skip()
        return self.text[self.i] if self.i < self.n else ""

    def ident(self) -> str:
        self.skip()
        start = self.i
        while self.i < self.n and (self.text[self.i].isalnum() or self.text[self.i] == "_"):
            self.i += 1
        if start == self.i:
            raise ValueError(f"Expected a name at {self.i}")
        return self.text[start:self.i]

    def skip_parens(self) -> None:
        depth = 0
        in_string = None
        while self.i < self.n:
            char = self.text[self.i]
            if in_string:
                if char == "\\":
                    self.i += 2
                    continue
                if char == in_string:
                    in_string = None
            elif char in {'"', "'"}:
                in_string = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    self.i += 1
                    return
            self.i += 1

    def parse_fields(self) -> list:
        fields = []
        while True:
            self.skip()
            if self.i >= self.n or self.peek() == "}":
                break
            if self.text.startswith("...", self.i):
                self.i += 3
                self.skip()
                if self.text.startswith("on", self.i) and not (
                    self.i + 2 < self.n and (self.text[self.i + 2].isalnum() or self.text[self.i + 2] == "_")
                ):
                    self.ident()
                    self.ident()
                    if self.peek() == "{":
                        self.i += 1
                        fields.extend(self.parse_fields())
                        if self.peek() == "}":
                            self.i += 1
                    continue
                fields.append({"spread": self.ident()})
                continue
            name = self.ident()
            alias = None
            if self.peek() == ":":
                self.i += 1
                alias = name
                name = self.ident()
            if self.peek() == "(":
                self.skip_parens()
            children = None
            if self.peek() == "{":
                self.i += 1
                children = self.parse_fields()
                if self.peek() == "}":
                    self.i += 1
            fields.append({"name": alias or name, "graphql_name": name, "children": children})
        return fields


def fragments_in(text: str) -> dict[str, list]:
    found = {}
    for match in re.finditer(r"fragment\s+(\w+)\s+on\s+(\w+)\s*\{", text):
        body = extract_brace(text, match.end() - 1)
        found[match.group(1)] = SelectionParser(body).parse_fields()
    return found


def load_fragment_index(repo: Path) -> dict[str, list]:
    index = {}
    roots = [repo / "app" / "fragments", repo / "fragments"]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.gql"):
            try:
                index.update(fragments_in(path.read_text(errors="replace")))
            except ValueError:
                continue
    return index


def resolve(fields: list, index: dict[str, list], stack: set[str] | None = None) -> list:
    stack = stack or set()
    resolved = []
    for field in fields:
        if "spread" in field:
            name = field["spread"]
            if name in stack or name not in index:
                resolved.append({"name": f"...{name}", "unresolved_fragment": name, "children": None})
                continue
            resolved.extend(resolve(index[name], index, stack | {name}))
            continue
        children = field.get("children")
        item = {
            "name": field["name"],
            "graphql_name": field.get("graphql_name") or field["name"],
            "children": resolve(children, index, stack) if children else None,
        }
        resolved.append(item)
    return resolved


def annotate_reuse(fields: list) -> None:
    for field in fields:
        if "spread" in field:
            continue
        children = field.get("children") or []
        spreads = [child["spread"] for child in children if "spread" in child]
        own = [child for child in children if "spread" not in child]
        if field["name"] in {"layout", "buttonFields"} or (spreads and not own and set(spreads) <= REUSE_FRAGMENTS):
            field["reuse"] = True
            field["reuse_fragment"] = spreads[0] if spreads else ("Layout" if field["name"] == "layout" else "ButtonItem")
        if own:
            annotate_reuse(own)


def flatten(fields: list, prefix: str = "") -> list[str]:
    paths = []
    for field in fields:
        if "spread" in field or "unresolved_fragment" in field:
            continue
        path = f"{prefix}.{field['name']}" if prefix else field["name"]
        paths.append(path)
        if field.get("children"):
            paths.extend(flatten(field["children"], path))
    return paths


def section_name_from_path(path: Path) -> str | None:
    parts = path.parts
    if "Sections" in parts:
        index = parts.index("Sections")
        if index + 1 < len(parts) - 1 or (index + 1 < len(parts) and path.suffix):
            if index + 1 < len(parts):
                return parts[index + 1]
    stem = path.stem
    for prefix in ("Client", "Server", "Styled"):
        if stem.startswith(prefix) and stem != prefix:
            return stem[len(prefix) :]
    if path.suffix == ".gql":
        return stem
    return None


def destructured_props(text: str) -> list[str]:
    match = re.search(r"(?:function\s+\w+|=)\s*\(\s*\{([^{}]+)\}\s*(?:,|\))", text)
    if not match:
        match = re.search(r"\(\s*\{([^{}]+)\}\s*\)\s*=>", text)
    if not match:
        return []
    names = []
    for part in match.group(1).split(","):
        name = part.strip().split("=")[0].strip().split(":")[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            names.append(name)
    return names


def prop_type_fields(text: str) -> dict[str, str]:
    found = {}
    for match in re.finditer(
        r"(\w+)\s*:\s*(propTypes\.\w+|PropTypes\.\w+|buttonItemProps|layoutPropTypes|mediaItemPropTypes)",
        text,
    ):
        found[match.group(1)] = match.group(2)
    return found


def uses_html(text: str, name: str) -> bool:
    return re.search(rf"__html:\s*{re.escape(name)}\b", text) is not None


def read_flexible(repo: Path) -> dict:
    config = repo / "app" / "core.config.js"
    if not config.exists():
        return {"group": "fields", "field": "flexible", "post_types": []}
    text = config.read_text(errors="replace")
    group = "fields"
    field = "flexible"
    match = re.search(r"flexiblePath:\s*\{[^}]*group:\s*'([^']+)'[^}]*field:\s*'([^']+)'", text)
    if match:
        group, field = match.group(1), match.group(2)
    post_types = []
    for block in re.split(r"\}\s*,\s*\{", text):
        if "flexiblePath" not in block:
            continue
        name = re.search(r"singularName:\s*'([^']+)'", block)
        if name and name.group(1) != "*":
            post_types.append(name.group(1))
    return {"group": group, "field": field, "post_types": post_types}


def sibling_repos(repo: Path) -> list[Path]:
    known = [Path("/home/dev/jaecoo-next/code"), Path("/home/dev/colmobil-luxury-trade/code")]
    return [path for path in known if path.exists() and path.resolve() != repo.resolve()]


def find_gql(repo: Path, name: str) -> Path | None:
    candidate = repo / "app" / "components" / "Sections" / name / f"{name}.gql"
    if candidate.exists():
        return candidate
    return None


class MarkupExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.in_li = 0
        self.headings = []
        self.paragraphs = 0
        self.images = 0
        self.images_in_repeat = 0
        self.buttons = 0
        self.repeat_items = 0

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        classes = attr.get("class", "")
        self.stack.append(tag)
        if tag in {"li", "article"}:
            self.in_li += 1
            self.repeat_items += 1
        if tag in {"h1", "h2", "h3"} and not self.in_li:
            self.headings.append(tag)
        if tag == "img":
            if self.in_li:
                self.images_in_repeat += 1
            else:
                self.images += 1
        if tag == "button" or (tag == "a" and "button" in classes):
            self.buttons += 1

    def handle_endtag(self, tag):
        if tag in {"li", "article"} and self.in_li:
            self.in_li -= 1
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if data.strip() and self.stack and self.stack[-1] == "p":
            self.paragraphs += 1


def infer_html(html: str) -> list[dict]:
    parser = MarkupExtractor()
    parser.feed(html)
    fields = [{"name": "layout", "label": "Layout", "type": "group", "reuse": True, "reuse_fragment": "Layout", "inferred": True}]
    if "h1" in parser.headings or "h2" in parser.headings:
        fields.append({"name": "title", "label": "Title", "type": "text", "reuse": False, "inferred": True})
    if "h3" in parser.headings:
        fields.append({"name": "subtitle", "label": "Subtitle", "type": "text", "reuse": False, "inferred": True})
    if parser.paragraphs:
        fields.append({"name": "description", "label": "Description", "type": "wysiwyg", "reuse": False, "inferred": True})
    if parser.images:
        fields.append(
            {
                "name": "imageFields",
                "label": "Image Fields",
                "type": "group",
                "reuse": True,
                "reuse_fragment": "ResponsiveMediaItem",
                "inferred": True,
            }
        )
    if parser.buttons:
        fields.append(
            {
                "name": "buttonFields",
                "label": "Button Fields",
                "type": "group",
                "reuse": True,
                "reuse_fragment": "ButtonItem",
                "inferred": True,
            }
        )
    if parser.repeat_items >= 2:
        item_fields = [{"name": "title", "label": "Title", "type": "text", "reuse": False, "inferred": True}]
        if parser.images_in_repeat:
            item_fields.append(
                {
                    "name": "icon",
                    "label": "Icon",
                    "type": "image",
                    "reuse": False,
                    "reuse_fragment": "MediaItem",
                    "inferred": True,
                }
            )
        fields.append(
            {
                "name": "items",
                "label": "Items",
                "type": "repeater",
                "reuse": False,
                "inferred": True,
                "sub_fields": item_fields,
            }
        )
    return fields


def split_html_sections(html: str) -> list[tuple[str | None, str]]:
    sections = []
    for match in re.finditer(r"<section\b([^>]*)>", html, flags=re.I):
        attrs = match.group(1)
        name = None
        named = re.search(r'data-section\s*=\s*["\']([^"\']+)["\']', attrs)
        if named:
            name = named.group(1)
        elif re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs):
            name = pascal(re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs).group(1))
        start = match.end()
        depth = 1
        cursor = start
        while depth and cursor < len(html):
            next_open = re.search(r"<section\b", html[cursor:], flags=re.I)
            next_close = re.search(r"</section\s*>", html[cursor:], flags=re.I)
            open_at = cursor + next_open.start() if next_open else None
            close_at = cursor + next_close.start() if next_close else None
            if close_at is None:
                break
            if open_at is not None and open_at < close_at:
                depth += 1
                cursor = open_at + 8
            else:
                depth -= 1
                if depth == 0:
                    sections.append((name, html[match.start() : close_at]))
                cursor = close_at + len(next_close.group(0))
    return sections


def spec_from_resolved(fields: list, js_text: str) -> list[dict]:
    specs = []
    for field in fields:
        if field["name"] in IGNORED_PROPS or "unresolved_fragment" in field:
            continue
        children = field.get("children") or []
        item = {
            "name": field["name"],
            "label": label_from(field["name"]),
            "reuse": bool(field.get("reuse")),
        }
        if field.get("reuse_fragment"):
            item["reuse_fragment"] = field["reuse_fragment"]
        if field.get("reuse"):
            item["type"] = "clone"
        elif children:
            item["type"] = "repeater" if field["name"].lower().endswith("list") or field["name"].endswith("s") else "group"
            item["sub_fields"] = spec_from_resolved(children, js_text)
        else:
            item["type"] = "wysiwyg or text" if uses_html(js_text, field["name"]) else "text"
        specs.append(item)
    return specs


def graphql_fragment(name: str, fields: list[dict], indent: int = 2) -> str:
    lines = [f"fragment {name} on FieldsFlexible{name}Layout {{"]

    def emit(items: list[dict], level: int) -> None:
        for field in items:
            prefix = " " * level
            fragment = field.get("reuse_fragment")
            if fragment == "Layout" and field["name"] == "layout":
                lines.append(f"{prefix}...Layout")
                continue
            if fragment and (field.get("reuse") or fragment in REUSE_FRAGMENTS):
                lines.append(f"{prefix}{field['name']} {{")
                lines.append(f"{prefix}  ...{fragment}")
                lines.append(f"{prefix}}}")
                continue
            children = field.get("sub_fields") or []
            if children:
                lines.append(f"{prefix}{field['name']} {{")
                emit(children, level + 2)
                lines.append(f"{prefix}}}")
            else:
                lines.append(f"{prefix}{field['name']}")

    emit(fields, indent)
    lines.append("}")
    return "\n".join(lines)


def field_rows(fields: list[dict], prefix: str = "") -> list[str]:
    rows = []
    for field in fields:
        path = f"{prefix}{field['name']}"
        kind = "clone of " + field["reuse_fragment"] if field.get("reuse") and field.get("reuse_fragment") else field.get("type", "text")
        inferred = " (inferred)" if field.get("inferred") else ""
        rows.append(f"| `{path}` | {kind}{inferred} |")
        rows.extend(field_rows(field.get("sub_fields") or [], prefix + field["name"] + "."))
    return rows


def render_markdown(report: dict) -> str:
    lines = [
        f"# ACF audit: {report['section']}",
        "",
        f"- Repo: `{report['repo']}`",
        f"- Frontend contract: **{report['frontend_contract']}**",
        f"- GraphQL type the app expects: `FieldsFlexible{report['section']}Layout`",
        f"- Parent: field group GraphQL name `{report['flexible']['group']}`, flexible field `{report['flexible']['field']}`",
        f"- Location post types: {', '.join(report['flexible']['post_types']) or 'see core.config.js'}",
        f"- WordPress: {report['wp_status']}",
        "",
        "Do not create a new field group for this section. Add a layout to the existing flexible field.",
        "Repeat this on each environment from that environment's own export. Do not import a dev file into production.",
        "",
    ]
    if report.get("gql_file"):
        lines.append(f"Frontend fragment: `{report['gql_file']}`")
        lines.append("")
    if report.get("sibling_warning"):
        lines.append(f"Other site: {report['sibling_warning']}")
        lines.append("")
    lines.extend(["## Fields", "", "| Field | Type |", "| --- | --- |"])
    lines.extend(field_rows(report.get("spec_fields") or []))
    lines.append("")
    if report.get("props_not_in_contract"):
        lines.append("Component props with no matching fragment field: " + ", ".join(f"`{name}`" for name in report["props_not_in_contract"]))
        lines.append("")
    if report.get("ignored_props"):
        lines.append("Renderer props, not ACF fields: " + ", ".join(f"`{name}`" for name in report["ignored_props"]))
        lines.append("")
    lines.extend(
        [
            "## Apply on one environment",
            "",
            "1. In that environment, export the field group whose GraphQL field name is `fields` (Custom Fields → Tools → Export).",
            "2. From the skill folder, run `scripts/patch_acf_export.py --export <that-file> --spec <section.spec.json>`.",
            "3. If the script writes a patched file, import it on the **same** environment (Tools → Import). If it reports missing clone fields, add those by cloning the sibling layout's field in the admin instead of importing a partial file.",
            "4. Confirm the layout name and that Show in GraphQL is on. The layout `__typename` must be `FieldsFlexible"
            + report["section"]
            + "Layout`.",
            "5. Open a page that uses the section, or run the site's `npm run gql` against this environment, and confirm the fragment validates.",
            "",
            "Without an export, create the layout by hand from the table above. Copy `layout`, `buttonFields`, and responsive image fields from an existing layout (clone, seamless) so the shared fragments keep resolving.",
            "",
            "## Frontend fragment",
            "",
            "```graphql",
            report.get("fragment_snippet") or "",
            "```",
            "",
        ]
    )
    if report.get("inferred"):
        lines.append("Fields marked inferred came from markup or component props. Review names and types before importing.")
        lines.append("")
    return "\n".join(lines)


def mark_known(fields: list) -> None:
    for field in fields:
        if field.get("name") == "layout":
            field["reuse"] = True
            field["reuse_fragment"] = "Layout"
        elif field.get("name") == "buttonFields":
            field["reuse"] = True
            field["reuse_fragment"] = "ButtonItem"
        if field.get("children"):
            mark_known(field["children"])


def top_level_names(fields: list) -> list[str]:
    return [field["name"] for field in fields if "name" in field]


def build_section(repo: Path, name: str, files: list[Path], html_chunks: list[str], index: dict) -> dict:
    flexible = read_flexible(repo)
    gql_path = find_gql(repo, name)
    js_text = "\n".join(
        path.read_text(errors="replace") for path in files if path.suffix in {".js", ".jsx", ".tsx"} and path.exists()
    )
    props = []
    types = {}
    for path in files:
        if path.suffix not in {".js", ".jsx", ".tsx"} or not path.exists():
            continue
        text = path.read_text(errors="replace")
        props.extend(destructured_props(text))
        types.update(prop_type_fields(text))
    props = list(dict.fromkeys(props))
    contract_fields = []
    if gql_path:
        own = fragments_in(gql_path.read_text(errors="replace"))
        merged = dict(index)
        merged.update(own)
        raw = own.get(name) or next(iter(own.values()), [])
        annotate_reuse(raw)
        contract_fields = resolve(raw, merged)
        # reuse flags were on the raw tree; copy them onto resolved nodes by name at each level
        def carry(raw_fields, resolved_fields):
            raw_by_name = {field["name"]: field for field in raw_fields if "name" in field}
            for field in resolved_fields:
                source = raw_by_name.get(field["name"])
                if source and source.get("reuse"):
                    field["reuse"] = True
                    field["reuse_fragment"] = source.get("reuse_fragment")
                if source and source.get("children") and field.get("children"):
                    carry(source["children"], field["children"])

        carry(raw, contract_fields)
        mark_known(contract_fields)
        spec_fields = spec_from_resolved(contract_fields, js_text)
        action = "confirm"
        frontend = "found"
    else:
        spec_fields = []
        for chunk in html_chunks:
            spec_fields.extend(infer_html(chunk))
        if not spec_fields and props:
            spec_fields.append({"name": "layout", "label": "Layout", "type": "clone", "reuse": True, "reuse_fragment": "Layout", "inferred": True})
            for prop in props:
                if prop in IGNORED_PROPS:
                    continue
                kind = types.get(prop, "")
                if prop in {"layout", "buttonFields"} or "button" in kind or "layout" in kind:
                    spec_fields.append({"name": prop, "label": label_from(prop), "type": "clone", "reuse": True, "reuse_fragment": "ButtonItem" if "button" in prop.lower() or "button" in kind else "Layout", "inferred": True})
                elif "media" in kind or prop.lower().endswith("image") or prop in {"icon", "imageFields"}:
                    spec_fields.append({"name": prop, "label": label_from(prop), "type": "image", "reuse": True, "reuse_fragment": "MediaItem", "inferred": True})
                else:
                    spec_fields.append({"name": prop, "label": label_from(prop), "type": "wysiwyg" if uses_html(js_text, prop) else "text", "reuse": False, "inferred": True})
        action = "create-layout"
        frontend = "missing"
    contract_names = set(top_level_names(contract_fields))
    ignored = [prop for prop in props if prop in IGNORED_PROPS]
    missing_props = [prop for prop in props if prop not in contract_names and prop not in IGNORED_PROPS]
    if frontend == "found" and missing_props:
        action = "add-fields"
        extra = []
        for prop in missing_props:
            extra.append({"name": prop, "label": label_from(prop), "type": "wysiwyg" if uses_html(js_text, prop) else "text", "reuse": False, "inferred": True})
        # spec for add-fields is only the new fields; the audit table should show the full contract plus additions
        add_spec = extra
    else:
        add_spec = None
    sibling_warning = None
    for other in sibling_repos(repo):
        other_gql = find_gql(other, name)
        if not other_gql:
            continue
        other_index = load_fragment_index(other)
        other_own = fragments_in(other_gql.read_text(errors="replace"))
        other_index.update(other_own)
        other_raw = other_own.get(name) or next(iter(other_own.values()), [])
        other_fields = resolve(other_raw, other_index)
        here = set(flatten(contract_fields))
        there = set(flatten(other_fields))
        if here != there:
            sibling_warning = (
                f"`{other}` also has `{name}`, with different fields. "
                f"Only there: {', '.join(sorted(there - here)) or 'none'}. "
                f"Only here: {', '.join(sorted(here - there)) or 'none'}."
            )
    audit_fields = spec_fields if add_spec is None else spec_fields + add_spec
    spec_payload_fields = add_spec if add_spec is not None else spec_fields
    report = {
        "section": name,
        "repo": str(repo),
        "frontend_contract": frontend,
        "gql_file": str(gql_path) if gql_path else None,
        "flexible": flexible,
        "wp_status": "Unknown. Field groups are not in git. Confirm this layout on the target environment.",
        "action": action,
        "component_props": props,
        "ignored_props": ignored,
        "props_not_in_contract": missing_props if frontend == "found" else [],
        "contract_fields": flatten(contract_fields),
        "spec_fields": audit_fields,
        "sibling_warning": sibling_warning,
        "inferred": any(field.get("inferred") for field in audit_fields),
        "fragment_snippet": graphql_fragment(name, audit_fields),
        "spec": {
            "action": action,
            "layout_name": name,
            "layout_label": label_from(name),
            "graphql_group": flexible["group"],
            "flexible_field": flexible["field"],
            "fields": spec_payload_fields if action != "confirm" else spec_fields,
        },
    }
    return report


def gather(files: list[Path], forced_name: str | None) -> dict[str, dict]:
    grouped: dict[str, dict] = {}

    def bucket(name: str) -> dict:
        return grouped.setdefault(name, {"files": [], "html": []})

    for path in files:
        if path.suffix.lower() in {".html", ".htm"}:
            text = path.read_text(errors="replace")
            parts = split_html_sections(text)
            if parts:
                for name, chunk in parts:
                    section = name or forced_name or pascal(path.stem)
                    slot = bucket(section)
                    slot["files"].append(path)
                    slot["html"].append(chunk)
            else:
                section = forced_name or section_name_from_path(path) or pascal(path.stem)
                slot = bucket(section)
                slot["files"].append(path)
                slot["html"].append(text)
            continue
        section = section_name_from_path(path) or forced_name
        if not section:
            raise SystemExit(f"Could not tell which section {path} belongs to. Pass --name.")
        bucket(section)["files"].append(path)
    return grouped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--file", action="append", required=True, type=Path)
    parser.add_argument("--name", help="Section name when the path does not include components/Sections/<Name>")
    parser.add_argument("--md-dir", type=Path)
    parser.add_argument("--spec-dir", type=Path)
    args = parser.parse_args()
    repo = args.repo
    if not (repo / "app" / "components" / "Sections").exists():
        print(f"No sections directory under {repo}", file=sys.stderr)
        return 1
    index = load_fragment_index(repo)
    grouped = gather(args.file, args.name)
    reports = []
    for name, payload in grouped.items():
        report = build_section(repo, name, payload["files"], payload["html"], index)
        reports.append(report)
        if args.md_dir:
            args.md_dir.mkdir(parents=True, exist_ok=True)
            (args.md_dir / f"{name}.md").write_text(render_markdown(report))
        if args.spec_dir and report["action"] != "confirm":
            args.spec_dir.mkdir(parents=True, exist_ok=True)
            (args.spec_dir / f"{name}.spec.json").write_text(json.dumps(report["spec"], indent=2) + "\n")
        elif args.spec_dir and report["action"] == "confirm":
            args.spec_dir.mkdir(parents=True, exist_ok=True)
            (args.spec_dir / f"{name}.spec.json").write_text(json.dumps(report["spec"], indent=2) + "\n")
    json.dump({"sections": reports}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
