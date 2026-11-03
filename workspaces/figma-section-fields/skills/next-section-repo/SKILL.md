---
name: next-section-repo
description: "Read the structure of one of your Next.js section repos (ora, smart, jaecoo, luxury-trade, omoda, or a new one of the same family) into a profile JSON, and check a section folder against it. Use when a stage needs the repo's scaffold files, fragment names, theme keys, fonts, line endings or lint command, or needs to know whether a section is finished. Pass the repo path and, for checks, the section folder."
---

# Next section repo

Two commands. Both read repo files as text. They never import, require or run repo code. The only programs they start are `git diff --cached --name-only` and the profile's `lintCommand` (ESLint), always with an argument list.

```bash
python3 scripts/probe_repo.py --repo /home/dev/ora-next [--out /path/profile.json]
python3 scripts/check_section.py --repo /home/dev/ora-next --folder ImageGrid [--profile /path/profile.json] [--no-lint]
```

Run them from this skill folder. `--repo` is the repo root or its `code/` folder.

## probe_repo.py

Prints `{"ok": true, "profile": {...}, "warnings": [...]}`. `--out` also writes the `profile` object to a file, which `figma-cli --scaffold next-section --repo-profile` and `check_section.py --profile` read. The keys are defined in [references/repo-profile.md](references/repo-profile.md).

Read `warnings` before trusting a profile. Examples:

- An installed `next` or `@colmobil/next` that differs from `package.json` (smart today).
- A template that uses `theme.mixins.layout` when the theme has no layout mixin (ora).
- `next lint` on Next 16.

## check_section.py

Prints `{"ok": true, "folder", "checks": [{"id", "status", "detail"}], "summary": {"pass", "fail", "warn"}, "pass"}`. `status` is `pass`, `fail` or `warn`. Each id, and what it enforces, is listed in [references/conformance-checklist.md](references/conformance-checklist.md). [references/section-shape.md](references/section-shape.md) describes the finished section.

A `warn` does not fail the section. An `eslint` warning means ESLint could not run (no `node_modules`, or a config that does not load), so lint is still unverified.

## Exit codes

| Exit | Code | What to do |
|---|---|---|
| 0 | | Success. For `check_section.py`, no check failed |
| 1 | `USAGE` | Fix the arguments |
| 2 | `NOT_A_SECTION_REPO` | The path has no `package.json` with `app/`, directly or under `code/` |
| 3 | `PROFILE` | The `--profile` file is not readable or not schemaVersion 1. Probe again |
| 4 | `FOLDER_NOT_FOUND` | The section folder does not exist |
| 6 | | At least one check failed. Fix the failing rows and run again |
| 99 | `INTERNAL` | Report the command and stop |
