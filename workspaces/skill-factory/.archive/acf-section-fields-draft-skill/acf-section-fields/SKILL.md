---
name: acf-section-fields
description: Reads React, Next.js, or HTML section files and audits them against the Jaecoo and luxury-trade WordPress ACF flexible layouts (field group `fields`, flexible field `flexible`). Use when adding, comparing, or promoting ACF fields for those section components. Writes a production checklist and, given an ACF JSON export from the target environment, a patched field-group file to import on that same environment.
---

# ACF section fields

Use this for Jaecoo and luxury-trade sections. The Next apps do not contain ACF field groups. They read one flexible field over WPGraphQL: group `fields`, field `flexible`, layout type `FieldsFlexible<Folder>Layout`. Details, shared fragments, and the import rules are in [references/field-patterns.md](references/field-patterns.md).

## Process

1. **Pick the repo.** Jaecoo is `/home/dev/jaecoo-next/code`. Luxury trade is `/home/dev/colmobil-luxury-trade/code`. The two sites do not share a field database. If the files are a new design, still pass the repo they will be built in.
2. **Audit the files.** From this skill folder:

```bash
python3 scripts/audit_sections.py \
  --repo /path/to/code \
  --file path/to/component.js \
  --file path/to/section.html \
  --md-dir ./acf-audit \
  --spec-dir ./acf-audit
```

Add `--name FolderName` when the path is not already `components/Sections/<Folder>/`. One HTML file can hold several `<section data-section="FolderName">` blocks.

3. **Read the report before trusting it.** `frontend_contract: found` means a `.gql` fragment exists, not that production has the layout. `inferred` fields are a guess from markup or props. Fix wrong names or types in the spec JSON before patching. `order` is never a field. A sibling warning means the other site's layout is different; do not merge them.
4. **Check the WordPress environment when WP-CLI can see it.** This does not write:

```bash
wp eval-file scripts/inspect_acf_layout.php acf-audit/FolderName.spec.json --url=https://that-environment
```

Exit 0 means the layout and the spec's top-level fields are present. Exit 2 means the layout or some fields are missing. Exit 1 means the `fields` / `flexible` group was not found uniquely. Do not guess which group to edit.
5. **Create fields only from an export of that same environment.** In WP admin: Custom Fields → Tools → Export, and export the group whose GraphQL name is `fields`.

```bash
python3 scripts/patch_acf_export.py \
  --export /path/to/fields-export.json \
  --spec acf-audit/FolderName.spec.json \
  --out /path/to/fields-export.patched.json
```

- `patched`: import `fields-export.patched.json` on that environment (Tools → Import). Or put it in the theme `acf-json` folder and run `wp acf json sync --dry-run`, then sync without `--dry-run` only after the dry run shows an update to the existing group key, not a create.
- `layout-already-in-export` or `nothing-to-add`: do not import.
- Exit 3: a clone (`layout`, `buttonFields`, a media group) has no sibling of the same name. No file is written. Add that field in the admin by cloning it from an existing layout. Then export again.
6. **Promote by repeating steps 4 and 5 on each environment.** There is no dev-to-prod field merge. Never import a file that was exported from another environment.
7. **Stop after the audit and the patched file** unless the user also asked to change the Next app. A new section still needs `components/Sections/<Folder>/<Folder>.gql` on `FieldsFlexible<Folder>Layout`, using the shared fragments. The audit includes that fragment. Do not add a field group, PHP registration, or `acf-json` directory to the Next repo.

## Rules

- Add a layout to the existing flexible field. Do not create a new field group for a section.
- Do not mint `group_` or `field_` keys except inside a patched copy of an export from the target environment.
- Do not change a subfield that is already on the layout. `add-fields` only appends names that are missing.
- Image fields follow `MediaItem` (`node.mediaItemUrl`), not a URL return value. Buttons follow `ButtonItem`, not the ACF link field, unless the fragment already selects `url`, `title`, and `target`.
- Options pages and page-template groups (`contactUsTemplateFields` and similar) are not flexible layouts. Say so and do not patch them into `flexible`.
- If `patch_acf_export.py` rewrites the layout name to snake_case, do not import until the live `__typename` is confirmed.

## Scripts

| Script | Effect |
| --- | --- |
| `scripts/audit_sections.py` | Reads the repo and the given files. Writes the audit and the spec. |
| `scripts/patch_acf_export.py` | Writes a patched export, or refuses. Does not contact WordPress. |
| `scripts/inspect_acf_layout.php` | Reads one environment via WP-CLI. Does not write. |
