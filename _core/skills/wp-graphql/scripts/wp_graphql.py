#!/usr/bin/env python3
"""Fixed WordPress GraphQL commands for ACF section work.

The agent passes a repo, a section name, or a fragment file.
This script builds the request, caches the schema, and prints one JSON object.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


CACHE_DIR = Path.home() / ".cache" / "wp-graphql"
CACHE_VERSION = 2
SCHEMA_TTL_SECONDS = 15 * 60
TOKEN_FALLBACK_SECONDS = 8 * 60
CONTENT_TYPES = ("Page", "Post", "Model", "Article")
LAYOUT_PREFIXES = ("EnFieldsEnFlexible", "FieldsFlexible")
KNOWN_SPREAD_SHAPES = {
    "MediaItem": "mediaItem",
    "MediaItemNew": "mediaItem",
    "ResponsiveMediaItem": "responsiveMedia",
    "ResponsiveMediaItemNew": "responsiveMedia",
    "Button": "button",
    "ButtonItem": "button",
    "BackgroundFields": "responsiveFull",
}
LEAF_SHAPES = {"mediaItem"}
MEDIA_LEAF_NAMES = {"mediaItemId"}
ACF_TYPE_NAMES = {
    "text", "textarea", "number", "range", "email", "url", "password", "image", "file",
    "wysiwyg", "oembed", "gallery", "select", "checkbox", "radio", "button_group",
    "true_false", "link", "post_object", "page_link", "relationship", "taxonomy", "user",
    "google_map", "date_picker", "date_time_picker", "time_picker", "color_picker",
    "message", "accordion", "tab", "group", "repeater", "flexible_content", "clone",
}
INTROSPECTION = """
{
  __schema {
    types {
      name
      kind
      description
      possibleTypes { name }
      interfaces { name }
      enumValues(includeDeprecated: false) { name }
      fields(includeDeprecated: false) {
        name
        description
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType { kind name ofType { kind name } }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


class CommandError(Exception):
    def __init__(self, code: str, message: str, exit_code: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


class UsageError(CommandError):
    def __init__(self, message: str):
        super().__init__("USAGE", message, 1)


class AuthError(CommandError):
    def __init__(self):
        super().__init__("AUTH_FAILED", "Could not sign in to the GraphQL endpoint.", 2)


class HttpError(CommandError):
    def __init__(self):
        super().__init__("HTTP_FAILED", "The GraphQL endpoint did not respond.", 3)


class SchemaError(CommandError):
    def __init__(self, message: str):
        super().__init__("SCHEMA", message, 3)


class ChoicesUnavailable(CommandError):
    def __init__(self, message: str):
        super().__init__("CHOICES_UNAVAILABLE", message, 5)


def redact(text: str) -> str:
    cleaned = re.sub(r"(?i)(username|password|authorization|token)=([^&\s]+)", r"\1=***", text)
    cleaned = re.sub(r"(?i)bearer\s+\S+", "Bearer ***", cleaned)
    return cleaned[:400]


def emit(payload: dict, exit_code: int = 0) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    raise SystemExit(exit_code)


def fail(err: CommandError) -> None:
    emit({"ok": False, "error": {"code": err.code, "message": err.message}}, err.exit_code)


def cache_key(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode()).hexdigest()[:24]


def write_private(path: Path, text: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(text)
        os.chmod(temporary, 0o600)
        temporary.replace(path)
        return True
    except OSError:
        return False


def read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def app_roots(repo: Path) -> list[Path]:
    roots = []
    for candidate in (repo / "app", repo / "code" / "app"):
        if (candidate / "components").is_dir():
            roots.append(candidate)
    return roots


def iter_gql_files(repo: Path) -> list[Path]:
    paths: list[Path] = []
    for root in app_roots(repo):
        for folder_name in ("fragments", "components"):
            folder = root / folder_name
            if folder.is_dir():
                paths.extend(folder.rglob("*.gql"))
    paths.sort(key=lambda path: (0 if "fragments" in path.parts else 1, str(path)))
    return paths


def store_path(repo: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    for candidate in (
        repo / "dist" / "dev" / "cache" / "store.json",
        repo / "code" / "dist" / "dev" / "cache" / "store.json",
    ):
        if candidate.is_file():
            return candidate
    raise AuthError()


def load_store(path: Path) -> dict:
    try:
        raw = path.read_text().strip()
        if raw.startswith("{"):
            data = json.loads(raw)
        else:
            parts = raw.split(".")
            if len(parts) < 2:
                raise AuthError()
            padded = parts[1] + "=" * (-len(parts[1]) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded))
    except CommandError:
        raise
    except (OSError, json.JSONDecodeError, ValueError):
        raise AuthError()
    if not isinstance(data, dict):
        raise AuthError()
    merged: dict = {}
    private = data.get("private")
    public = data.get("public")
    if isinstance(private, dict):
        merged.update(private)
    if isinstance(public, dict):
        merged.update(public)
    if not merged:
        merged = data
    return merged


def graphql_url(endpoint: str) -> str:
    url = endpoint.strip().rstrip("/")
    if not url.endswith("graphql"):
        url = url + "/graphql"
    return url


def connection_settings(repo: Path, explicit_store: str | None) -> dict:
    endpoint = os.environ.get("WP_GQL_ENDPOINT", "").strip()
    token = os.environ.get("WP_GQL_TOKEN", "").strip()
    header = os.environ.get("WP_GQL_DEV_HEADER", "").strip()
    if endpoint and token:
        return {
            "endpoint": graphql_url(endpoint),
            "token": token,
            "dev_header": header,
            "from_env": True,
        }
    merged = load_store(store_path(repo, explicit_store))
    keys = (
        "ENDPOINT_URL",
        "ENVIRONMENT",
        "SITE",
        "DEV_HEADER_KEY",
        "BASE_AUTH_USERNAME_SUBSCRIBER",
        "BASE_AUTH_PASSWORD_SUBSCRIBER",
    )
    if any(not merged.get(key) for key in keys):
        raise AuthError()
    return {
        "endpoint": graphql_url(str(merged["ENDPOINT_URL"])),
        "environment": str(merged["ENVIRONMENT"]),
        "site": str(merged["SITE"]),
        "dev_header": str(merged["DEV_HEADER_KEY"]),
        "user": str(merged["BASE_AUTH_USERNAME_SUBSCRIBER"]),
        "secret": str(merged["BASE_AUTH_PASSWORD_SUBSCRIBER"]),
        "from_env": False,
    }


def token_expiry(token: str) -> int:
    parts = token.split(".")
    if len(parts) != 3:
        return int(time.time()) + TOKEN_FALLBACK_SECONDS
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (json.JSONDecodeError, ValueError):
        return int(time.time()) + TOKEN_FALLBACK_SECONDS
    exp = payload.get("exp") if isinstance(payload, dict) else None
    if isinstance(exp, int):
        return exp - 30
    return int(time.time()) + TOKEN_FALLBACK_SECONDS


def fetch_token(settings: dict) -> str:
    query = urllib.parse.urlencode(
        {
            "username": settings["user"],
            "password": settings["secret"],
            "site": settings["site"],
        }
    )
    url = (
        "https://gw.colmobil.co.il/"
        + settings["environment"].upper()
        + "/api-colmobil-jwt?"
        + query
    )
    request = urllib.request.Request(
        url,
        headers={"x-dev-environment": settings["dev_header"]},
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            token = response.read().decode().strip().strip('"')
    except Exception:
        raise AuthError()
    if not token or token.startswith("{") or token.startswith("<"):
        raise AuthError()
    return token


def cached_token(settings: dict, refresh: bool) -> str:
    if settings.get("from_env"):
        return settings["token"]
    path = CACHE_DIR / f"token-{cache_key(settings['endpoint'])}.json"
    if not refresh:
        saved = read_json(path)
        if saved and saved.get("token") and int(saved.get("exp") or 0) > time.time():
            return str(saved["token"])
    token = fetch_token(settings)
    write_private(path, json.dumps({"token": token, "exp": token_expiry(token)}))
    return token


def post_graphql(settings: dict, token: str, query: str) -> dict:
    body = json.dumps({"query": query}).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
    }
    if settings.get("dev_header"):
        headers["x-dev-environment"] = settings["dev_header"]
    request = urllib.request.Request(settings["endpoint"], data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as err:
        if err.code in (401, 403):
            raise AuthError()
        raise HttpError()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise HttpError()
    if not isinstance(payload, dict):
        raise SchemaError("The GraphQL response was empty.")
    errors = payload.get("errors")
    data = payload.get("data")
    if errors and not data:
        message = "GraphQL returned an error."
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            message = redact(str(errors[0].get("message") or message))
        raise SchemaError(message)
    return payload


def acf_type(description: str | None) -> str | None:
    if not description:
        return None
    text = description.replace("&quot;", '"').replace("&#039;", "'")
    patterns = (
        r'(?i)set to\s+"([A-Za-z0-9_-]+)"',
        r"(?i)Field Type[:\s]+([A-Za-z0-9_-]+)",
        r'"([^"]+)"\s+Field Type',
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match and match.group(1).lower() in ACF_TYPE_NAMES:
            return match.group(1).lower()
    return None


def parse_choices(description: str | None) -> list[str]:
    if not description:
        return []
    text = description.replace("&quot;", '"').replace("&#039;", "'")
    found: list[str] = []
    for match in re.finditer(r"(?i)choices?\s*[:=]\s*(\[[^\]]+\]|[^\n.]+)", text):
        chunk = match.group(1).strip()
        quoted = re.findall(r'"([^"]+)"', chunk)
        if quoted:
            found.extend(item.strip() for item in quoted if item.strip())
            continue
        chunk = chunk.strip("[]")
        for part in re.split(r"\s*[|,]\s*", chunk):
            cleaned = part.strip().strip("\"'").strip()
            if cleaned and cleaned.lower() not in {"and", "or"}:
                found.append(cleaned)
    unique: list[str] = []
    for item in found:
        if item not in unique:
            unique.append(item)
    return unique


def type_ref(node: dict | None) -> tuple[str, str | None]:
    if not node:
        return "", None
    kind = node.get("kind")
    if kind == "NON_NULL":
        inner, named = type_ref(node.get("ofType"))
        return inner + "!", named
    if kind == "LIST":
        inner, named = type_ref(node.get("ofType"))
        return "[" + inner + "]", named
    name = node.get("name")
    return (name or kind or ""), name


def compact_schema(payload: dict) -> dict:
    types = ((payload.get("data") or {}).get("__schema") or {}).get("types") or []
    compact: dict = {}
    for item in types:
        name = item.get("name")
        if not name or name.startswith("__"):
            continue
        fields = []
        for field in item.get("fields") or []:
            field_name = field.get("name") or ""
            if field_name.startswith("__"):
                continue
            description = field.get("description")
            rendered, named = type_ref(field.get("type"))
            fields.append(
                {
                    "name": field_name,
                    "gqlType": rendered,
                    "named": named,
                    "acfType": acf_type(description),
                    "choices": parse_choices(description),
                }
            )
        enum_values = [entry.get("name") for entry in (item.get("enumValues") or []) if entry.get("name")]
        compact[name] = {
            "name": name,
            "kind": item.get("kind"),
            "possibleTypes": [entry.get("name") for entry in (item.get("possibleTypes") or []) if entry.get("name")],
            "interfaces": [entry.get("name") for entry in (item.get("interfaces") or []) if entry.get("name")],
            "enumValues": enum_values,
            "fields": fields,
        }
    if not compact:
        raise SchemaError("The schema response did not include types.")
    return compact


def cache_is_fresh(saved: dict | None) -> bool:
    if not saved or saved.get("version") != CACHE_VERSION:
        return False
    schema = saved.get("schema")
    if not isinstance(schema, dict):
        return False
    return time.time() - int(saved.get("fetchedAt") or 0) < SCHEMA_TTL_SECONDS


def load_schema(settings: dict, refresh: bool) -> tuple[dict, bool]:
    path = CACHE_DIR / f"schema-{cache_key(settings['endpoint'])}.json"
    if not refresh:
        saved = read_json(path)
        schema = (saved or {}).get("schema")
        if cache_is_fresh(saved) and isinstance(schema, dict):
            return schema, True
    token = cached_token(settings, refresh)
    try:
        payload = post_graphql(settings, token, INTROSPECTION)
    except AuthError:
        if settings.get("from_env"):
            raise
        token = cached_token(settings, True)
        payload = post_graphql(settings, token, INTROSPECTION)
    schema = compact_schema(payload)
    write_private(path, json.dumps({"version": CACHE_VERSION, "fetchedAt": int(time.time()), "schema": schema}))
    return schema, False


def is_media_edge(type_name: str | None) -> bool:
    if not type_name:
        return False
    if type_name in ("AcfMediaItemConnection", "AcfMediaItemConnectionEdge"):
        return True
    return type_name.endswith("AcfMediaItemConnection") or type_name.endswith("AcfMediaItemConnectionEdge")


def is_media_item(type_name: str | None) -> bool:
    return type_name in ("MediaItem", "MediaItemNew")


def classify(schema: dict, type_name: str | None) -> str | None:
    if not type_name:
        return None
    if is_media_edge(type_name) or is_media_item(type_name):
        return "mediaItem"
    item = schema.get(type_name)
    if not item:
        return None
    names = {field["name"] for field in item["fields"]}
    if {"type", "imageFields", "videoFields"} <= names:
        return "responsiveFull"
    if "desktop" in names and "mobile" in names and "videoFields" not in names and "imageFields" not in names:
        return "responsiveMedia"
    if "marginBottom" in names:
        return "spacing"
    if {"actionType", "text"} <= names:
        return "button"
    return None


def layout_language(member: str) -> str:
    if member.startswith("EnFieldsEnFlexible"):
        return "en"
    return "he"


def find_flexibles(schema: dict) -> list[dict]:
    found = []
    for name, item in schema.items():
        if item.get("kind") not in ("UNION", "INTERFACE"):
            continue
        possible = item.get("possibleTypes") or []
        members = [
            member
            for member in possible
            if member.endswith("Layout") and member.startswith(LAYOUT_PREFIXES)
        ]
        if len(members) < 2 or len(members) != len(possible):
            continue
        languages = {layout_language(member) for member in members}
        language = next(iter(languages)) if len(languages) == 1 else "mixed"
        found.append({"union": name, "members": members, "language": language})
    found.sort(key=lambda entry: (0 if entry["language"] == "he" else 1, entry["union"]))
    return found


def layout_members(schema: dict) -> list[str]:
    members = []
    for entry in find_flexibles(schema):
        members.extend(entry["members"])
    return members


def find_flexible_field(schema: dict) -> dict | None:
    """The fields.flexible field, even when its union has fewer than two layouts."""
    index = reverse_fields(schema)
    candidates = []
    for type_name, item in schema.items():
        if item.get("kind") != "OBJECT" or type_name.startswith("WithAcf"):
            continue
        reachers = []
        for owner, owner_field in index.get(type_name, []):
            if owner_field not in ("fields", "enFields"):
                continue
            owner_item = schema.get(owner) or {}
            if owner_item.get("kind") != "OBJECT" or owner.startswith("WithAcf"):
                continue
            reachers.append(owner_field)
        if not reachers:
            continue
        for field in item["fields"]:
            name = field["name"]
            named_flexible = name in ("flexible", "enFlexible")
            acf_flexible = field.get("acfType") == "flexible_content"
            if not named_flexible and not acf_flexible:
                continue
            if name == "enFlexible" and "enFields" in reachers:
                parent_field = "enFields"
            elif "fields" in reachers:
                parent_field = "fields"
            else:
                parent_field = reachers[0]
            language = "en" if parent_field == "enFields" or name == "enFlexible" else "he"
            candidates.append(
                {
                    "parentType": type_name,
                    "parentField": parent_field,
                    "field": name,
                    "gqlType": field.get("gqlType") or field.get("named"),
                    "language": language,
                }
            )
    if not candidates:
        return None
    candidates.sort(key=lambda item: (0 if item["language"] == "he" else 1, item["parentType"], item["field"]))
    chosen = candidates[0]
    return {key: chosen[key] for key in ("parentType", "parentField", "field", "gqlType")}


def flexible_field_paths(schema: dict, union_name: str) -> tuple[list[str], list[str]]:
    index = reverse_fields(schema)
    paths = []
    owners = []
    for parent, field in index.get(union_name, []):
        if field not in ("flexible", "enFlexible"):
            continue
        for owner, owner_field in index.get(parent, []):
            if owner_field not in ("fields", "enFields"):
                continue
            if (schema.get(owner) or {}).get("kind") != "OBJECT":
                continue
            if owner.startswith("WithAcf"):
                continue
            owners.append(owner)
            paths.append(f"{owner}.{owner_field}.{field}")
    order = {"Page": 0, "Post": 1, "Model": 2, "Article": 3}
    paired = sorted(zip(owners, paths), key=lambda item: (order.get(item[0], 9), item[0]))
    if not paired:
        return [], []
    ordered_owners, ordered_paths = zip(*paired)
    return list(ordered_paths), list(ordered_owners)


def reverse_fields(schema: dict) -> dict[str, list[tuple[str, str]]]:
    index: dict[str, list[tuple[str, str]]] = {}
    for name, item in schema.items():
        for field in item["fields"]:
            named = field.get("named")
            if named:
                index.setdefault(named, []).append((name, field["name"]))
    return index


def section_from_layout(type_name: str) -> str:
    for prefix in LAYOUT_PREFIXES:
        if type_name.startswith(prefix) and type_name.endswith("Layout"):
            return type_name[len(prefix) : -len("Layout")]
    return type_name


def walk_shapes(schema: dict, type_name: str, prefix: str, depth: int, seen: set[str], found: dict[str, str]) -> None:
    if depth > 3 or type_name in seen:
        return
    item = schema.get(type_name)
    if not item:
        return
    for field in item["fields"]:
        path = field["name"] if not prefix else prefix + "." + field["name"]
        shape = classify(schema, field.get("named"))
        if shape and (shape not in found or _example_rank(shape, path) < _example_rank(shape, found[shape])):
            found[shape] = path
        named = field.get("named")
        child = schema.get(named or "")
        if child and child.get("kind") == "OBJECT" and shape != "mediaItem":
            walk_shapes(schema, named, path, depth + 1, seen | {type_name}, found)


def expands(named: str | None, shape: str | None) -> bool:
    if not named:
        return False
    if is_media_edge(named):
        return True
    if shape == "mediaItem":
        return False
    if named.endswith("Connection") or named.endswith("ConnectionEdge") or named.endswith("PageInfo"):
        return False
    return True


def field_tree(schema: dict, type_name: str, depth: int, seen: set[str]) -> list[dict]:
    item = schema.get(type_name)
    if not item or depth < 0:
        return []
    nodes = []
    for field in item["fields"]:
        named = field.get("named")
        shape = classify(schema, named)
        node = {
            "name": field["name"],
            "gqlType": field["gqlType"],
            "namedType": named,
            "acfType": field.get("acfType"),
            "shape": shape,
            "children": [],
        }
        if shape == "mediaItem":
            node["imageOn"] = "edge" if is_media_edge(named) else "mediaItem"
        if field.get("choices"):
            node["choices"] = field["choices"]
        child = schema.get(named or "")
        if child and child.get("kind") == "OBJECT" and expands(named, shape) and named not in seen and depth > 0:
            node["children"] = field_tree(schema, named, depth - 1, seen | {type_name})
        nodes.append(node)
    return nodes


def strip_comments(source: str) -> str:
    lines = []
    for line in source.splitlines():
        in_string = False
        kept = []
        for char in line:
            if char == '"':
                in_string = not in_string
            if char == "#" and not in_string:
                break
            kept.append(char)
        lines.append("".join(kept))
    return "\n".join(lines)


class Parser:
    def __init__(self, source: str):
        self.source = source
        self.index = 0

    def peek(self) -> str:
        self.skip()
        if self.index >= len(self.source):
            return ""
        return self.source[self.index]

    def skip(self) -> None:
        while self.index < len(self.source) and self.source[self.index].isspace():
            self.index += 1

    def expect(self, char: str) -> None:
        if self.peek() != char:
            raise UsageError("Could not parse the fragment.")
        self.index += 1

    def ident(self) -> str:
        self.skip()
        start = self.index
        while self.index < len(self.source) and (self.source[self.index].isalnum() or self.source[self.index] == "_"):
            self.index += 1
        if start == self.index:
            raise UsageError("Could not parse the fragment.")
        return self.source[start : self.index]

    def skip_parens(self) -> None:
        depth = 0
        in_string = False
        while self.index < len(self.source):
            char = self.source[self.index]
            self.index += 1
            if char == '"':
                in_string = not in_string
            elif not in_string and char == "(":
                depth += 1
            elif not in_string and char == ")":
                depth -= 1
                if depth == 0:
                    return
        raise UsageError("Could not parse the fragment.")

    def parse_selection(self) -> list[dict]:
        self.expect("{")
        items = []
        while self.peek() and self.peek() != "}":
            if self.peek() == ".":
                items.append(self.parse_spread())
            else:
                items.append(self.parse_field())
        self.expect("}")
        return items

    def parse_spread(self) -> dict:
        for _ in range(3):
            self.expect(".")
        name = self.ident()
        if name == "on":
            return {"kind": "inline", "on": self.ident(), "selection": self.parse_selection()}
        return {"kind": "spread", "name": name}

    def parse_field(self) -> dict:
        name = self.ident()
        if self.peek() == ":":
            self.index += 1
            name = self.ident()
        if self.peek() == "(":
            self.skip_parens()
        selection = self.parse_selection() if self.peek() == "{" else None
        return {"kind": "field", "name": name, "selection": selection}


def parse_document(source: str) -> list[dict]:
    parser = Parser(strip_comments(source))
    fragments = []
    while parser.peek():
        if parser.ident() != "fragment":
            raise UsageError("The file must contain GraphQL fragments.")
        name = parser.ident()
        if parser.ident() != "on":
            raise UsageError("Could not parse the fragment.")
        fragments.append({"name": name, "on": parser.ident(), "selection": parser.parse_selection()})
    if not fragments:
        raise UsageError("The file has no fragment.")
    return fragments


def load_fragments(repo: Path) -> dict[str, dict]:
    loaded: dict[str, dict] = {}
    for path in iter_gql_files(repo):
        try:
            text = path.read_text()
        except OSError:
            continue
        try:
            fragments = parse_document(text)
        except UsageError:
            continue
        for fragment in fragments:
            loaded.setdefault(fragment["name"], fragment)
    return loaded


def find_section_file(repo: Path, section: str) -> Path | None:
    for root in app_roots(repo):
        sections = root / "components" / "Sections"
        direct = sections / section / f"{section}.gql"
        if direct.is_file():
            return direct
        if not sections.is_dir():
            continue
        for folder in sections.iterdir():
            if folder.name.lower() == section.lower():
                candidate = folder / f"{folder.name}.gql"
                if candidate.is_file():
                    return candidate
    return None


def find_fragment_file(repo: Path, name: str, type_name: str | None) -> Path | None:
    section_file = find_section_file(repo, name)
    if section_file:
        return section_file
    name_match = None
    type_match = None
    for path in iter_gql_files(repo):
        try:
            fragments = parse_document(path.read_text())
        except (OSError, UsageError):
            continue
        for fragment in fragments:
            if fragment["name"].lower() == name.lower() and name_match is None:
                name_match = path
            if type_name and fragment["on"].lower() == type_name.lower() and type_match is None:
                type_match = path
    return name_match or type_match


def is_media_connection_edge(type_name: str | None) -> bool:
    return bool(type_name) and type_name.endswith("AcfMediaItemConnectionEdge")


def spread_fits_edge(fragments: dict[str, dict], name: str) -> bool:
    """True when the fragment's whole selection is one `node { ... }` field, so it fits a connection edge."""
    fragment = fragments.get(name)
    if not fragment:
        return False
    selection = fragment["selection"]
    return len(selection) == 1 and selection[0]["kind"] == "field" and selection[0]["name"] == "node"


def media_edge_mismatch(path: str, schema_type: str | None) -> dict:
    return {
        "path": path,
        "fragmentShape": "mediaItem",
        "schemaShape": "mediaEdge",
        "schemaType": schema_type,
    }


def compare_selection(
    selection: list[dict],
    type_name: str | None,
    schema: dict,
    fragments: dict[str, dict],
    prefix: str,
    missing: list[str],
    mismatches: list[dict],
    active: tuple[str, ...] = (),
) -> None:
    item = schema.get(type_name or "")
    fields = {field["name"]: field for field in (item["fields"] if item else [])}
    for node in selection:
        if node["kind"] == "spread":
            compare_spread(node, type_name, schema, fragments, prefix, missing, mismatches, active)
            continue
        if node["kind"] == "inline":
            target = node.get("on") if node.get("on") in schema else type_name
            compare_selection(node["selection"], target, schema, fragments, prefix, missing, mismatches, active)
            continue
        path = node["name"] if not prefix else prefix + "." + node["name"]
        if node["name"] not in fields:
            if node["name"] in MEDIA_LEAF_NAMES and is_media_item(type_name):
                continue
            missing.append(path)
            continue
        if not node["selection"]:
            continue
        child = fields[node["name"]].get("named")
        spreads = [entry for entry in node["selection"] if entry["kind"] == "spread"]
        if len(node["selection"]) == 1 and spreads:
            expected = KNOWN_SPREAD_SHAPES.get(spreads[0]["name"])
            actual = classify(schema, child)
            if expected == "mediaItem" and is_media_edge(child):
                fits = is_media_connection_edge(child) and spread_fits_edge(fragments, spreads[0]["name"])
                if not fits:
                    mismatches.append(media_edge_mismatch(path, child))
                    continue
            elif expected and actual and expected != actual:
                mismatches.append(
                    {
                        "path": path,
                        "fragmentShape": expected,
                        "schemaShape": actual,
                        "schemaType": child,
                    }
                )
                continue
        compare_selection(node["selection"], child, schema, fragments, path, missing, mismatches, active)


def compare_spread(
    node: dict,
    type_name: str | None,
    schema: dict,
    fragments: dict[str, dict],
    prefix: str,
    missing: list[str],
    mismatches: list[dict],
    active: tuple[str, ...] = (),
) -> None:
    label = (prefix + "." if prefix else "") + "..." + node["name"]
    if node["name"] in active:
        return
    nested = active + (node["name"],)
    expected = KNOWN_SPREAD_SHAPES.get(node["name"])
    fragment = fragments.get(node["name"])
    if expected == "mediaItem" and is_media_edge(type_name):
        if is_media_connection_edge(type_name) and spread_fits_edge(fragments, node["name"]):
            compare_selection(fragment["selection"], type_name, schema, fragments, label, missing, mismatches, nested)
            return
        mismatches.append(media_edge_mismatch(label, type_name))
        return
    if fragment is None:
        if expected in LEAF_SHAPES:
            return
        missing.append(label)
        return
    if expected in LEAF_SHAPES:
        target = fragment["on"] if fragment["on"] in schema else type_name
        compare_selection(fragment["selection"], target, schema, fragments, label, missing, mismatches, nested)
        return
    compare_selection(fragment["selection"], type_name, schema, fragments, prefix, missing, mismatches, nested)


def top_level_names(selection: list[dict], fragments: dict[str, dict], active: tuple[str, ...] = ()) -> list[str]:
    names = []
    for node in selection:
        if node["kind"] == "field":
            names.append(node["name"])
        elif node["kind"] == "spread" and node["name"] not in active:
            fragment = fragments.get(node["name"])
            if fragment:
                names.extend(top_level_names(fragment["selection"], fragments, active + (node["name"],)))
    return names


def clone_from(schema: dict, layouts: list[str], wanted: list[str]) -> dict | None:
    best: tuple[int, str, list[str]] | None = None
    for layout in layouts:
        nested = {field["name"] for field in schema[layout]["fields"]}
        for field in schema[layout]["fields"]:
            child = schema.get(field.get("named") or "")
            if child:
                nested.update(entry["name"] for entry in child["fields"])
        matched = [name for name in wanted if name in nested]
        score = len(matched)
        if score > (best[0] if best else 1):
            best = (score, layout, matched)
    if best is None:
        return None
    return {
        "section": section_from_layout(best[1]),
        "layout": best[1],
        "matchedFields": best[2],
    }


def resolve_section_types(schema: dict, section: str, members: list[str]) -> dict:
    candidates = [prefix + section + "Layout" for prefix in ("FieldsFlexible", "EnFieldsEnFlexible")]
    layout_match = None
    for candidate in candidates:
        for member in members:
            if member.lower() == candidate.lower():
                layout_match = member
                break
        if layout_match:
            break
    if layout_match is None:
        for candidate in candidates:
            if candidate in schema:
                layout_match = candidate
                break
    group = None
    for name in schema:
        if name.lower() == section.lower() and schema[name].get("kind") == "OBJECT":
            group = name
            break
    return {"layout": layout_match, "group": group}


def attachments(schema: dict, type_name: str | None) -> list[dict]:
    if not type_name:
        return []
    found = []
    interface_name = "WithAcf" + type_name
    for name, item in schema.items():
        if interface_name in (item.get("interfaces") or []):
            found.append({"kind": "implements", "parent": name, "field": None})
        for field in item["fields"]:
            if field.get("named") == type_name:
                found.append({"kind": "field", "parent": name, "field": field["name"]})
    # Prefer content types over the field group types themselves.
    fields = []
    for item in found:
        if item["kind"] != "field" or item["parent"] == type_name:
            continue
        parent = schema.get(item["parent"]) or {}
        if parent.get("kind") != "OBJECT":
            continue
        if item["parent"].startswith("WithAcf"):
            continue
        fields.append(item)
    return fields[:20]


def omitted_fields(schema: dict, type_name: str | None, selection: list[dict], fragments: dict[str, dict]) -> list[str]:
    item = schema.get(type_name or "")
    if not item:
        return []
    selected = set(top_level_names(selection, fragments))
    return [field["name"] for field in item["fields"] if field["name"] not in selected]


def fragment_report(schema: dict, fragments: dict[str, dict], fragment: dict) -> dict:
    target = fragment["on"]
    target_exists = target in schema
    compared = target if target_exists else None
    if (
        is_media_item(target)
        and "AcfMediaItemConnectionEdge" in schema
        and spread_fits_edge({fragment["name"]: fragment}, fragment["name"])
    ):
        # A shared media fragment whose body is node { ... } is written for a connection edge.
        compared = "AcfMediaItemConnectionEdge"
    missing: list[str] = []
    mismatches: list[dict] = []
    if compared:
        compare_selection(fragment["selection"], compared, schema, fragments, "", missing, mismatches)
    return {
        "name": fragment["name"],
        "on": target,
        "onExists": target_exists,
        "comparedTo": compared,
        "compared": compared is not None,
        "missingOnSchema": missing,
        "notSelected": omitted_fields(schema, compared, fragment["selection"], fragments),
        "shapeMismatches": mismatches,
    }


def command_status(settings: dict, refresh: bool) -> dict:
    token = cached_token(settings, refresh)
    try:
        post_graphql(settings, token, "{ __typename }")
    except AuthError:
        if settings.get("from_env"):
            raise
        token = cached_token(settings, True)
        post_graphql(settings, token, "{ __typename }")
    host = urllib.parse.urlparse(settings["endpoint"]).hostname
    schema_file = CACHE_DIR / f"schema-{cache_key(settings['endpoint'])}.json"
    cached = cache_is_fresh(read_json(schema_file))
    return {
        "ok": True,
        "command": "status",
        "endpointHost": host,
        "authenticated": True,
        "schemaCached": cached,
    }


def _example_rank(shape: str, path: str) -> int:
    leaf = path.rsplit(".", 1)[-1]
    rank = path.count(".")
    if shape == "mediaItem" and leaf in ("desktop", "mobile"):
        rank += 5
    elif shape == "mediaItem" and leaf != "image":
        rank += 2
    if shape == "responsiveMedia" and leaf not in ("imageFields", "hoverImageFields", "backgroundImageFields"):
        rank += 3
    if shape == "button" and leaf not in ("buttonsList", "buttonFields", "button", "buttonsFields", "secondaryButton"):
        rank += 3
    return rank


def pascal_name(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(part[:1].upper() + part[1:] for part in parts)


def is_cloned_type(field_name: str, named: str | None, shape: str | None) -> bool:
    if not named or not shape:
        return False
    if is_media_edge(named) or is_media_item(named):
        return False
    expected = pascal_name(field_name)
    if named in {expected, expected + "Fields"}:
        return False
    return named.endswith(expected) or named.endswith(expected + "Fields")


def field_summary_label(node: dict) -> str:
    if node.get("imageOn") == "edge":
        label = "mediaItem on a connection edge"
    elif node.get("shape"):
        label = node["shape"]
    elif node.get("acfType"):
        label = node["acfType"]
    else:
        label = node.get("gqlType") or "field"
    if node.get("acfType") == "select" and not node.get("choices"):
        label += ", choices not in the schema"
    elif node.get("acfType") is None and node.get("gqlType") in {"String", "String!", "[String]", "[String]!"} and not node.get("shape"):
        label += ", acf type unknown"
    named = node.get("namedType")
    if is_cloned_type(node["name"], named, node.get("shape")):
        label += f", clone of {named}"
    return f"{node['name']} ({label})"


def mismatch_lines(mismatches: list[dict]) -> list[str]:
    lines = []
    for mismatch in mismatches:
        if mismatch.get("schemaShape") == "mediaEdge":
            if is_media_connection_edge(mismatch.get("schemaType")):
                lines.append(
                    f"{mismatch['path']} spreads a media fragment on {mismatch.get('schemaType')}, but that fragment's body is not node {{ ... }}. Use a shared fragment whose body is node {{ ... }}, or select node, then the media fields."
                )
            else:
                lines.append(
                    f"{mismatch['path']} is the gallery connection {mismatch.get('schemaType')}. Select nodes, then the media fields."
                )
            continue
        lines.append(
            f"{mismatch['path']} is {mismatch['fragmentShape']} in the fragment and {mismatch['schemaShape']} on the schema."
        )
    return lines


def content_paths(field_paths: list[str]) -> list[str]:
    return [path for path in field_paths if path.split(".", 1)[0] in CONTENT_TYPES]


def path_summary(field_paths: list[str], owners: list[str]) -> str:
    preferred = [name for name in CONTENT_TYPES if name in owners]
    if preferred:
        extra = len(owners) - len(preferred)
        where = ", ".join(preferred)
        if extra:
            where += f" and {extra} other types"
        sample = content_paths(field_paths)
        if sample and ".enFields.enFlexible" in sample[0]:
            return f"Flexible field is enFields.enFlexible on {where}."
        return f"Flexible field is fields.flexible on {where}."
    if field_paths:
        return "Flexible field path: " + ", ".join(field_paths[:4]) + "."
    return "Flexible field path was not found."


def options_roots(schema: dict) -> list[dict]:
    found = []
    seen = set()
    for type_name, item in schema.items():
        if item.get("kind") != "OBJECT" or type_name.startswith("WithAcf"):
            continue
        for field in item["fields"]:
            named = field.get("named")
            child = schema.get(named or "") or {}
            interfaces = child.get("interfaces") or []
            if "AcfOptionsPage" not in interfaces and not any(str(entry).startswith("WithAcfOptionsPage") for entry in interfaces):
                continue
            key = (type_name, field["name"])
            if key in seen:
                continue
            seen.add(key)
            found.append({"parent": type_name, "field": field["name"], "type": named})
    found.sort(key=lambda entry: (0 if entry["parent"] in ("RootQuery", "Query") else 1, entry["field"]))
    return found


def template_groups(schema: dict) -> list[dict]:
    found = []
    for name, item in schema.items():
        if item.get("kind") != "OBJECT" or not name.startswith("Template_"):
            continue
        fields = []
        for field in item["fields"]:
            named = field.get("named") or ""
            child = schema.get(named) or {}
            interfaces = child.get("interfaces") or []
            if child.get("kind") == "OBJECT" and (named.endswith("Fields") or any(str(entry).startswith("WithAcf") for entry in interfaces)):
                fields.append(field["name"])
        if fields:
            found.append({"type": name, "fields": fields[:8]})
    return found


def summarize_union(schema: dict, entry: dict) -> dict:
    union = entry["union"]
    members = entry["members"]
    field_paths, owners = flexible_field_paths(schema, union)
    counts = {"layouts": len(members), "spacing": 0, "mediaItem": 0, "responsiveMedia": 0, "responsiveFull": 0, "button": 0}
    examples: dict[str, dict] = {}
    layouts = []
    for member in sorted(members):
        shapes: dict[str, str] = {}
        walk_shapes(schema, member, "", 0, set(), shapes)
        for shape in counts:
            if shape == "layouts":
                continue
            if shape not in shapes:
                continue
            counts[shape] += 1
            candidate = {"section": section_from_layout(member), "field": shapes[shape]}
            current = examples.get(shape)
            if current is None or _example_rank(shape, candidate["field"]) < _example_rank(shape, current["field"]):
                examples[shape] = candidate
        item = schema.get(member) or {"fields": []}
        layouts.append(
            {
                "layout": member,
                "section": section_from_layout(member),
                "language": layout_language(member),
                "fields": [field["name"] for field in item["fields"]],
                "shapes": sorted(shapes),
            }
        )
    language = entry["language"]
    summary = [
        f"{counts['layouts']} flexible layouts are in {union} ({language}).",
        path_summary(field_paths, owners),
    ]
    return {
        "union": union,
        "language": language,
        "paths": content_paths(field_paths),
        "counts": counts,
        "examples": examples,
        "layouts": layouts,
        "summary": summary,
    }


def command_patterns(schema: dict, schema_cached: bool) -> dict:
    unions = [summarize_union(schema, entry) for entry in find_flexibles(schema)]
    options = options_roots(schema)
    templates = template_groups(schema)
    flexible_field = find_flexible_field(schema)
    if not unions:
        summary = ["No flexible layout union was found in this schema."]
        if flexible_field:
            summary.append(
                "A flexible field exists on {parentType}.{field} ({gqlType}) via {parentField}, with no layout union.".format(
                    **flexible_field
                )
            )
    else:
        summary = []
        for block in unions:
            summary.extend(block["summary"])
            counts = block["counts"]
            summary.append(f"{counts['spacing']} layouts include a spacing group.")
            for shape, label in (
                ("mediaItem", "single image"),
                ("responsiveMedia", "desktop/mobile image group"),
                ("responsiveFull", "image-or-video group"),
                ("button", "button"),
            ):
                example = block["examples"].get(shape)
                if example:
                    summary.append(f"{block['language']} {label}: {example['section']}.{example['field']} ({counts[shape]} layouts).")
                else:
                    summary.append(f"No {block['language']} layout uses a {label}.")
    if options:
        shown = ", ".join(f"{entry['parent']}.{entry['field']} ({entry['type']})" for entry in options[:12])
        summary.append("Options pages: " + shown + ".")
    else:
        summary.append("No ACF options page is on the root query.")
    if templates:
        shown = ", ".join(f"{entry['type']}.{entry['fields'][0]}" for entry in templates[:8])
        summary.append("Template field groups: " + shown + ". Use type for one of these.")
    else:
        summary.append("No template field group was found.")
    primary = unions[0] if unions else None
    return {
        "ok": True,
        "command": "patterns",
        "schemaCached": schema_cached,
        "summary": summary,
        "flexible": None
        if primary is None
        else {
            "union": primary["union"],
            "paths": primary["paths"],
            "unions": [
                {"union": block["union"], "language": block["language"], "paths": block["paths"], "layouts": block["counts"]["layouts"]}
                for block in unions
            ],
        },
        "counts": primary["counts"] if primary else {},
        "examples": primary["examples"] if primary else {},
        "layouts": [layout for block in unions for layout in block["layouts"]],
        "flexibleField": flexible_field,
        "options": options,
        "templates": templates[:40],
    }


def pick_fragment(fragments_in_file: list[dict], section: str) -> dict:
    for fragment in fragments_in_file:
        if fragment["name"].lower() == section.lower():
            return fragment
    return fragments_in_file[0]


def graphql_name(name: str) -> None:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
        raise UsageError("Name must be a GraphQL name.")


def union_name_for(schema: dict, member: str | None) -> str | None:
    if not member:
        return None
    for entry in find_flexibles(schema):
        if member in entry["members"]:
            return entry["union"]
    return None


def resolve_object(schema: dict, name: str) -> str | None:
    for key, item in schema.items():
        if key.lower() == name.lower() and item.get("kind") in ("OBJECT", "INTERFACE", "UNION"):
            return key
    return None


def resolve_query_field(schema: dict, name: str) -> dict | None:
    for parent in ("RootQuery", "Query"):
        item = schema.get(parent) or {}
        for field in item.get("fields") or []:
            if field["name"].lower() != name.lower():
                continue
            named = field.get("named")
            if (schema.get(named or "") or {}).get("kind") == "OBJECT":
                return {"parent": parent, "field": field["name"], "type": named}
    return None


def exposed_names(schema: dict, type_name: str | None) -> list[str]:
    return [f"{item['parent']}.{item['field']}" for item in attachments(schema, type_name) if item.get("field")]


def append_fragment_facts(summary: list[str], report: dict) -> None:
    summary.append(f"Fragment {report['name']} targets {report['on']}.")
    summary.append("That target type is in the schema." if report["onExists"] else "That target type is not in the schema.")
    if not report.get("comparedTo"):
        summary.append("No type was compared. The fragment fields were not checked.")
        return
    if report["comparedTo"] != report["on"]:
        summary.append(f"Field comparison used {report['comparedTo']}.")
    if report["missingOnSchema"]:
        summary.append(f"Fragment fields absent on {report['comparedTo']}: " + ", ".join(report["missingOnSchema"][:12]) + ".")
    elif report["shapeMismatches"]:
        summary.append("Selected field names exist. Shape mismatches follow.")
    else:
        summary.append("Every fragment field exists on the compared type.")
    compared = report.get("comparedTo")
    if compared in {"MediaItem", "MediaItemNew"}:
        summary.append("Core MediaItem fields are not listed.")
    elif report.get("notSelected"):
        summary.append("Live fields not selected: " + ", ".join(report["notSelected"][:12]) + ".")
    summary.extend(mismatch_lines(report["shapeMismatches"]))


def compare_file(schema: dict, repo: Path, file_path: Path, prefer: str | None, fallback_type: str | None) -> dict:
    parsed = pick_fragment(parse_document(file_path.read_text()), prefer or "")
    fragments = load_fragments(repo)
    fragments[parsed["name"]] = parsed
    report = fragment_report(schema, fragments, parsed)
    report["file"] = str(file_path)
    if not report["onExists"] and fallback_type:
        missing: list[str] = []
        mismatches: list[dict] = []
        compare_selection(parsed["selection"], fallback_type, schema, fragments, "", missing, mismatches)
        report["comparedTo"] = fallback_type
        report["compared"] = True
        report["missingOnSchema"] = missing
        report["notSelected"] = omitted_fields(schema, fallback_type, parsed["selection"], fragments)
        report["shapeMismatches"] = mismatches
    return report


def command_section(schema: dict, schema_cached: bool, repo: Path, section: str) -> dict:
    graphql_name(section)
    members = layout_members(schema)
    resolved = resolve_section_types(schema, section, members)
    primary = resolved["layout"] or resolved["group"]
    tree = field_tree(schema, primary, 6, set()) if primary else []
    exposed = exposed_names(schema, resolved["group"] or resolved["layout"])
    summary = []
    if resolved["layout"] and resolved["layout"] in members:
        summary.append(f"{section} is flexible layout {resolved['layout']} on {union_name_for(schema, resolved['layout'])}.")
    elif resolved["layout"]:
        summary.append(
            f"{section} has layout type {resolved['layout']}, but {resolved['layout']} is not on the flexible layout type."
        )
    elif resolved["group"]:
        summary.append(f"{section} is field group {resolved['group']}, not a flexible layout.")
    else:
        summary.append(f"No GraphQL type was found for {section}.")
    summary.append("Exposed as " + ", ".join(exposed[:8]) + "." if exposed else f"No content type field points at {section}.")
    if tree:
        summary.append("Live fields: " + ", ".join(field_summary_label(node) for node in tree) + ".")
    fragment_file = find_section_file(repo, section)
    report = None
    clone = None
    if fragment_file:
        report = compare_file(schema, repo, fragment_file, section, resolved["group"])
        append_fragment_facts(summary, report)
        if members:
            fragment_matches = bool(report["onExists"] and not report["missingOnSchema"] and not report["shapeMismatches"])
            parsed = pick_fragment(parse_document(fragment_file.read_text()), section)
            fragments = load_fragments(repo)
            if fragment_matches:
                wanted = top_level_names(parsed["selection"], fragments)
            else:
                wanted = [node["name"] for node in tree]
            clone = clone_from(schema, members, wanted)
            if clone:
                clone["basedOn"] = "fragment" if fragment_matches else "live"
                summary.append(
                    "Similar layout, not an ACF clone: " + clone["section"] + " (" + ", ".join(clone["matchedFields"]) + ")."
                )
    return {
        "ok": True,
        "command": "section",
        "schemaCached": schema_cached,
        "section": section,
        "summary": summary,
        "layoutType": resolved["layout"],
        "onFlexibleUnion": bool(resolved["layout"] and resolved["layout"] in members),
        "groupType": resolved["group"],
        "exposedAs": exposed,
        "tree": tree,
        "fragment": report,
        "cloneFrom": clone,
        "similarLayout": clone,
    }


def command_type(schema: dict, schema_cached: bool, repo: Path, name: str) -> dict:
    graphql_name(name)
    members = layout_members(schema)
    root = None
    direct = resolve_object(schema, name)
    if direct:
        primary = direct
    else:
        root = resolve_query_field(schema, name)
        primary = root["type"] if root else None
    resolved = resolve_section_types(schema, name, members)
    if primary is None:
        primary = resolved["layout"] or resolved["group"]
    layout = primary if primary in members else None
    stray_layout = (
        primary
        if primary and not layout and primary.endswith("Layout") and primary.startswith(LAYOUT_PREFIXES)
        else None
    )
    group = primary if primary and primary not in members and not stray_layout else None
    tree = field_tree(schema, primary, 6, set()) if primary else []
    exposed = exposed_names(schema, primary)
    summary = []
    if layout:
        summary.append(f"{name} is flexible layout {layout} on {union_name_for(schema, layout)}.")
    elif stray_layout:
        summary.append(f"{name} has layout type {stray_layout}, but {stray_layout} is not on the flexible layout type.")
    elif root:
        summary.append(f"{name} is root field {root['parent']}.{root['field']} of type {root['type']}.")
    elif group:
        summary.append(f"{name} is type {group}, not a flexible layout.")
    else:
        summary.append(f"No GraphQL type was found for {name}.")
    summary.append("Exposed as " + ", ".join(exposed[:8]) + "." if exposed else f"No field points at {name}.")
    if tree:
        summary.append("Live fields: " + ", ".join(field_summary_label(node) for node in tree) + ".")
    fragment_file = find_fragment_file(repo, name, primary)
    report = None
    if fragment_file and primary:
        report = compare_file(schema, repo, fragment_file, name, group)
        append_fragment_facts(summary, report)
    return {
        "ok": True,
        "command": "type",
        "schemaCached": schema_cached,
        "name": name,
        "summary": summary,
        "type": primary,
        "rootField": None if root is None else f"{root['parent']}.{root['field']}",
        "layoutType": layout or stray_layout,
        "onFlexibleUnion": bool(layout),
        "groupType": group,
        "exposedAs": exposed,
        "tree": tree,
        "fragment": report,
    }


def command_choices(schema: dict, schema_cached: bool, spec: str) -> dict:
    if spec.count(".") != 1:
        raise UsageError("choices expects Type.field.")
    type_part, field_part = spec.split(".")
    graphql_name(type_part)
    graphql_name(field_part)
    type_name = resolve_object(schema, type_part)
    if type_name is None:
        root = resolve_query_field(schema, type_part)
        type_name = root["type"] if root else None
    if type_name is None:
        resolved = resolve_section_types(schema, type_part, layout_members(schema))
        type_name = resolved["layout"] or resolved["group"]
    if type_name is None or type_name not in schema:
        raise UsageError(f"No GraphQL type was found for {type_part}.")
    field = next((item for item in schema[type_name]["fields"] if item["name"].lower() == field_part.lower()), None)
    if field is None:
        raise UsageError(f"{type_name} has no field {field_part}.")
    named = schema.get(field.get("named") or "") or {}
    enum_values = list(named.get("enumValues") or []) if named.get("kind") == "ENUM" else []
    parsed = list(field.get("choices") or [])
    choices = parsed or enum_values
    acf = field.get("acfType")
    if not choices:
        if acf:
            detail = f"ACF type is {acf}. The option list is not in the GraphQL schema. Stop. Do not read the store, the cache, REST, or the database."
        else:
            detail = "The schema description has no ACF field type, and the option list is not in the GraphQL schema. Stop. Do not read the store, the cache, REST, or the database."
        raise ChoicesUnavailable(detail)
    source = "description" if parsed else "enum"
    summary = [f"{type_name}.{field['name']} choices come from the {source}.", "Options: " + ", ".join(choices) + "."]
    if acf:
        summary.insert(0, f"ACF type is {acf}.")
    else:
        summary.insert(0, "The schema description has no ACF field type.")
    return {
        "ok": True,
        "command": "choices",
        "schemaCached": schema_cached,
        "summary": summary,
        "type": type_name,
        "field": field["name"],
        "acfType": acf,
        "gqlType": field.get("gqlType"),
        "choices": choices,
    }


def command_check_repo(schema: dict, schema_cached: bool, repo: Path) -> dict:
    fragments = load_fragments(repo)
    problems = []
    not_compared = []
    checked = 0
    for path in iter_gql_files(repo):
        try:
            documents = parse_document(path.read_text())
        except (OSError, UsageError):
            continue
        for fragment in documents:
            checked += 1
            local = dict(fragments)
            local[fragment["name"]] = fragment
            report = fragment_report(schema, local, fragment)
            if not report["compared"]:
                not_compared.append({"file": str(path), "name": report["name"], "on": report["on"]})
                continue
            if report["missingOnSchema"] or report["shapeMismatches"]:
                problems.append(
                    {
                        "file": str(path),
                        "name": report["name"],
                        "on": report["on"],
                        "missingOnSchema": report["missingOnSchema"],
                        "shapeMismatches": report["shapeMismatches"],
                    }
                )
    summary = [f"{checked} fragments checked.", f"{len(problems)} fragments do not match the schema."]
    if not_compared:
        summary.append(
            f"{len(not_compared)} fragments were not compared because their target type is not in the schema."
        )
    if problems:
        for item in problems[:20]:
            if item["missingOnSchema"]:
                summary.append(f"{item['file']} {item['name']}: absent {', '.join(item['missingOnSchema'][:6])}.")
            else:
                summary.append(f"{item['file']} {item['name']}: shape mismatch.")
    elif not not_compared:
        summary.append("Every checked fragment matches.")
    else:
        summary.append("Every compared fragment matches.")
    return {
        "ok": True,
        "command": "check-repo",
        "schemaCached": schema_cached,
        "summary": summary,
        "checked": checked,
        "problems": problems,
        "notCompared": not_compared,
    }


def command_check_fragment(schema: dict, schema_cached: bool, repo: Path, file_path: Path) -> dict:
    if not file_path.is_file():
        raise CommandError("FILE_NOT_FOUND", "Fragment file was not found.", 4)
    members = layout_members(schema)
    parsed = parse_document(file_path.read_text())[0]
    section = section_from_layout(parsed["on"])
    resolved = resolve_section_types(schema, section, members)
    report = compare_file(schema, repo, file_path, parsed["name"], resolved["group"] if not (parsed["on"] in schema) else None)
    summary: list[str] = []
    append_fragment_facts(summary, report)
    return {
        "ok": True,
        "command": "check-fragment",
        "schemaCached": schema_cached,
        "summary": summary,
        "fragment": report,
        "onFlexibleUnion": bool(resolved["layout"] and resolved["layout"] in members),
        "exposedAs": exposed_names(schema, resolved["group"] or resolved["layout"]),
    }


class CommandParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        emit({"ok": False, "error": {"code": "USAGE", "message": message}}, 1)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", required=True, help="Next app root that owns the project store.")
    common.add_argument("--store", help="Store file. Defaults to dist/dev/cache/store.json under --repo.")
    common.add_argument("--refresh", action="store_true", help="Ignore the schema and session cache.")
    parser = CommandParser(description="WordPress GraphQL commands for ACF sections.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=CommandParser)
    sub.add_parser("status", parents=[common])
    sub.add_parser("patterns", parents=[common])
    sub.add_parser("check-repo", parents=[common])
    section = sub.add_parser("section", parents=[common])
    section.add_argument("name")
    named = sub.add_parser("type", parents=[common])
    named.add_argument("name")
    choices = sub.add_parser("choices", parents=[common])
    choices.add_argument("spec", help="Type.field, for example ButtonFields.variant.")
    check = sub.add_parser("check-fragment", parents=[common])
    check.add_argument("file")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    repo = Path(args.repo).expanduser()
    if not repo.is_dir():
        raise UsageError("Repo path is not a directory.")
    settings = connection_settings(repo, args.store)
    if args.command == "status":
        emit(command_status(settings, args.refresh))
    schema, schema_cached = load_schema(settings, args.refresh)
    if args.command == "patterns":
        emit(command_patterns(schema, schema_cached))
    if args.command == "section":
        emit(command_section(schema, schema_cached, repo, args.name))
    if args.command == "type":
        emit(command_type(schema, schema_cached, repo, args.name))
    if args.command == "choices":
        emit(command_choices(schema, schema_cached, args.spec))
    if args.command == "check-fragment":
        emit(command_check_fragment(schema, schema_cached, repo, Path(args.file).expanduser()))
    if args.command == "check-repo":
        emit(command_check_repo(schema, schema_cached, repo))
    raise UsageError("Unknown command.")


if __name__ == "__main__":
    try:
        main()
    except CommandError as err:
        fail(err)
    except SystemExit:
        raise
    except Exception:
        emit({"ok": False, "error": {"code": "INTERNAL", "message": "The command failed."}}, 99)
