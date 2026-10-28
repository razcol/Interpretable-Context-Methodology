# Project Profile Format

The shape of `output/project-profile.md`. Later stages load named sections, so keep the headings exact.

## Sections

### `## Run`

| Field | Content |
|-------|---------|
| Target repo path | The path the user gave |
| App root | The folder with `package.json` and `next` |
| Git top level | From git |
| HEAD sha | Full sha. Later stages compare against this. |
| Branch | Current branch name |
| Tree state | `clean`, or `dirty` plus the changed paths |
| Shallow clone | yes or no |
| Last commit date | ISO date |
| Profile date | ISO timestamp |
| Stack | The Primary Stack from preferences |

### `## Repo`

Layout facts: top-level folders, router folders found, workspace or monorepo layout, file counts by extension (top 8).

### `## Stack`

Framework and library versions, language, package manager, Node pin, styling and data libraries found in dependencies.

### `## Tooling`

Lint config and what it extends, formatter, type-check settings, build flags that matter, test runner, local hooks, CI system and its definition file, CODEOWNERS presence, and the scripts for build, lint, typecheck, and test.

### `## Not Applicable Probes`

A table of probe ids that will not run and the reason.

### `## Unknowns`

Every fact that could not be determined, with what was tried. Never fill a gap with a guess.

## Rules

- Each fact names its source: a command or a file path.
- Values that may be secret (tokens in config, env values) are never copied. Note only that the file exists.
- Keep the profile under 150 lines. Link to files instead of pasting them.
