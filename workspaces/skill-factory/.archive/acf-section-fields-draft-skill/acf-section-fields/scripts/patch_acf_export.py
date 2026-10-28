#!/usr/bin/env python3
"""Insert a layout into an ACF JSON export of the existing fields group.

Does not create a field group. Does not change an existing field's key.
Keys for the new layout are minted into this copy only. Import the result
on the same environment the export came from.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from pathlib import Path


class PatchError(Exception):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def mint(prefix: str, used: set[str]) -> str:
    while True:
        key = prefix + secrets.token_hex(6)
        if key not in used:
            used.add(key)
            return key


def collect_keys(node, found: set[str]) -> None:
    if isinstance(node, dict):
        key = node.get("key")
        if isinstance(key, str):
            found.add(key)
        for value in node.values():
            collect_keys(value, found)
    elif isinstance(node, list):
        for item in node:
            collect_keys(item, found)


def walk_strings(node, mapping: dict[str, str]):
    if isinstance(node, dict):
        return {key: walk_strings(value, mapping) for key, value in node.items()}
    if isinstance(node, list):
        return [walk_strings(item, mapping) for item in node]
    if isinstance(node, str) and node in mapping:
        return mapping[node]
    return node


def iter_layouts(layouts):
    if isinstance(layouts, dict):
        for key, layout in layouts.items():
            yield key, layout
    elif isinstance(layouts, list):
        for layout in layouts:
            if isinstance(layout, dict):
                yield layout.get("key"), layout


def find_flexible(fields, field_name: str):
    found = []

    def walk(items):
        if not isinstance(items, list):
            return
        for field in items:
            if not isinstance(field, dict):
                continue
            if field.get("type") == "flexible_content" and field.get("name") == field_name:
                found.append(field)
            walk(field.get("sub_fields") or [])

    walk(fields)
    return found


def choose_group(groups: list, graphql_name: str, flexible_name: str) -> dict:
    if not groups:
        raise PatchError("Export contains no field group.")
    named = [group for group in groups if group.get("graphql_field_name") == graphql_name]
    pool = named or groups
    matches = []
    for group in pool:
        flex = find_flexible(group.get("fields") or [], flexible_name)
        if len(flex) == 1:
            matches.append((group, flex[0]))
        elif len(flex) > 1:
            raise PatchError(
                f"Group {group.get('key')} ({group.get('title')}) has more than one "
                f"flexible field named {flexible_name!r}."
            )
    if len(matches) != 1:
        titles = ", ".join(
            f"{group.get('title')} ({group.get('key')})" for group in pool
        ) or "none"
        raise PatchError(
            f"Expected one field group with GraphQL name {graphql_name!r} and a "
            f"flexible field {flexible_name!r}. Candidates: {titles}."
        )
    if not named:
        group, _flex = matches[0]
        print(
            f"warning: group {group.get('key')} has no graphql_field_name "
            f"{graphql_name!r}; matched the only flexible field named {flexible_name!r}.",
            file=sys.stderr,
        )
    return matches[0]


def layout_name_for(folder: str, existing: list[str]) -> tuple[str, str | None]:
    if not existing or any(any(char.isupper() for char in name) for name in existing):
        return folder, None
    snake = []
    for char in folder:
        if char.isupper() and snake:
            snake.append("_")
        snake.append(char.lower())
    applied = "".join(snake)
    warning = (
        f"Existing layout names are snake_case. ACF layout name will be {applied!r}. "
        f"The Next.js fragment type stays FieldsFlexible{folder}Layout. "
        "Confirm the live __typename before importing."
    )
    return applied, warning


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


def base_field(name: str, label: str, field_type: str, key: str) -> dict:
    field = {
        "key": key,
        "label": label,
        "name": name,
        "aria-label": "",
        "type": field_type,
        "instructions": "",
        "required": 0,
        "conditional_logic": 0,
        "wrapper": {"width": "", "class": "", "id": ""},
        "show_in_graphql": 1,
        "default_value": "",
    }
    if field_type == "wysiwyg":
        field.update({"tabs": "all", "toolbar": "full", "media_upload": 1, "delay": 0})
    elif field_type == "textarea":
        field.update({"rows": 4, "new_lines": "wpautop"})
    elif field_type == "image":
        field.update(
            {
                "return_format": "array",
                "library": "all",
                "preview_size": "medium",
                "min_width": "",
                "min_height": "",
                "min_size": "",
                "max_width": "",
                "max_height": "",
                "max_size": "",
                "mime_types": "",
            }
        )
    elif field_type == "true_false":
        field.update({"default_value": 0, "ui": 1, "ui_on_text": "", "ui_off_text": ""})
    elif field_type == "number":
        field.update({"min": "", "max": "", "step": ""})
    elif field_type == "link":
        field.update({"return_format": "array"})
    elif field_type == "repeater":
        field.update(
            {
                "layout": "block",
                "pagination": 0,
                "min": 0,
                "max": 0,
                "collapsed": "",
                "button_label": "Add Row",
                "rows_per_page": 20,
                "sub_fields": [],
            }
        )
    elif field_type == "group":
        field.update({"layout": "block", "sub_fields": []})
    elif field_type == "url":
        field["placeholder"] = ""
    return field


def find_sibling_field(flex: dict, name: str) -> dict | None:
    for _key, layout in iter_layouts(flex.get("layouts") or {}):
        for sub in layout.get("sub_fields") or []:
            if isinstance(sub, dict) and sub.get("name") == name:
                return sub
    return None


def strip_ids(node) -> None:
    if isinstance(node, dict):
        node.pop("ID", None)
        for value in node.values():
            strip_ids(value)
    elif isinstance(node, list):
        for item in node:
            strip_ids(item)


def retarget_parent_layout(node, old_key: str | None, new_key: str) -> None:
    if isinstance(node, dict):
        if old_key and node.get("parent_layout") == old_key:
            node["parent_layout"] = new_key
        for value in node.values():
            retarget_parent_layout(value, old_key, new_key)
    elif isinstance(node, list):
        for item in node:
            retarget_parent_layout(item, old_key, new_key)


def copy_sibling(source: dict, layout_key: str, used: set[str]) -> dict:
    subtree_keys: set[str] = set()
    collect_keys(source, subtree_keys)
    mapping = {key: mint("field_", used) for key in subtree_keys if key.startswith("field_")}
    copied = walk_strings(source, mapping)
    strip_ids(copied)
    retarget_parent_layout(copied, source.get("parent_layout"), layout_key)
    copied["parent_layout"] = layout_key
    return copied


def build_field(spec: dict, layout_key: str, flex: dict, used: set[str], gaps: list[str]) -> dict | None:
    name = spec["name"]
    if spec.get("reuse"):
        sibling = find_sibling_field(flex, name)
        if sibling is None:
            gaps.append(name)
            return None
        return copy_sibling(sibling, layout_key, used)
    field_type = spec.get("type") or "text"
    if field_type not in {
        "text",
        "textarea",
        "wysiwyg",
        "image",
        "true_false",
        "number",
        "link",
        "url",
        "repeater",
        "group",
        "select",
    }:
        field_type = "text"
    field = base_field(name, spec.get("label") or label_from(name), field_type, mint("field_", used))
    field["parent_layout"] = layout_key
    children = spec.get("sub_fields") or []
    if children:
        built = []
        for child in children:
            child_field = build_field(child, layout_key, flex, used, gaps)
            if child_field is not None:
                child_field.pop("parent_layout", None)
                built.append(child_field)
        field["sub_fields"] = built
    return field


def existing_layout(flex: dict, names: set[str]):
    for key, layout in iter_layouts(flex.get("layouts") or {}):
        if layout.get("name") in names or key in names:
            return layout
    return None


def load_groups(path: Path) -> list:
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise PatchError("Export JSON must be a field group object or an array of them.")


def patch(export_path: Path, spec: dict, out_path: Path) -> dict:
    raw = json.loads(export_path.read_text())
    as_list = isinstance(raw, list)
    groups = load_groups(export_path)
    action = spec.get("action") or "create-layout"
    folder = spec["layout_name"]
    graphql_name = spec.get("graphql_group") or "fields"
    flexible_name = spec.get("flexible_field") or "flexible"
    group, flex = choose_group(groups, graphql_name, flexible_name)
    existing_names = [layout.get("name", "") for _key, layout in iter_layouts(flex.get("layouts") or {})]
    applied_name, style_warning = layout_name_for(folder, existing_names)
    report = {
        "group_key": group.get("key"),
        "group_title": group.get("title"),
        "layout_name": applied_name,
        "folder_name": folder,
        "action": action,
        "warning": style_warning,
        "wrote": None,
        "manual_fields": [],
    }
    names = {folder, applied_name}
    current = existing_layout(flex, names)
    if action == "confirm":
        report["status"] = "confirm-only"
        return report
    if action == "create-layout" and current is not None:
        report["status"] = "layout-already-in-export"
        report["existing_subfields"] = [
            sub.get("name") for sub in (current.get("sub_fields") or []) if isinstance(sub, dict)
        ]
        return report
    if action == "add-fields" and current is None:
        raise PatchError(
            f"Layout {folder!r} is not in this export. Use action create-layout, not add-fields.",
            code=3,
        )

    used: set[str] = set()
    collect_keys(groups, used)
    gaps: list[str] = []
    built = []
    present = set()
    if current is not None:
        present = {sub.get("name") for sub in current.get("sub_fields") or [] if isinstance(sub, dict)}
    target_layout_key = current.get("key") if current else None
    if target_layout_key is None:
        target_layout_key = mint("layout_", used)
    for field_spec in spec.get("fields") or []:
        if field_spec.get("name") in present:
            continue
        field = build_field(field_spec, target_layout_key, flex, used, gaps)
        if field is not None:
            built.append(field)
    report["manual_fields"] = gaps
    if gaps:
        report["status"] = "incomplete-not-written"
        report["message"] = (
            "A reused field has no sibling of the same name in this export, "
            "so no import file was written. Add those fields from an existing layout in the admin, "
            "or export a group that already contains them."
        )
        return report
    if not built:
        report["status"] = "nothing-to-add"
        return report

    if current is None:
        layout = {
            "key": target_layout_key,
            "name": applied_name,
            "label": spec.get("layout_label") or label_from(folder),
            "display": "block",
            "sub_fields": built,
            "min": "",
            "max": "",
        }
        layouts = flex.setdefault("layouts", {})
        if isinstance(layouts, list):
            layouts.append(layout)
        else:
            layouts[target_layout_key] = layout
    else:
        current.setdefault("sub_fields", []).extend(built)

    group["modified"] = int(time.time())
    payload = groups if as_list else groups[0]
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    report["wrote"] = str(out_path)
    report["status"] = "patched"
    report["added_fields"] = [field.get("name") for field in built]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    out = args.out or args.export.with_name(args.export.stem + ".patched.json")
    try:
        report = patch(args.export, spec, out)
    except PatchError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    if report.get("status") == "incomplete-not-written":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
