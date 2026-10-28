# Scripts Reference

Two dependency-free Node scripts in `scripts/`. Run them from the workspace root. They need Node 18 or newer and git.

## measure.mjs

Runs one probe against a git repository and writes a report skeleton plus evidence files. Read-only on the target.

```
node scripts/measure.mjs --probe <probe.md> --repo <dir> --out <dir> [--days 90]
```

| Option | Meaning |
|--------|---------|
| `--probe` | A probe file. It must contain a fenced block tagged `json measure`. |
| `--repo` | The target repo or app folder. Candidate files come from `git ls-files` under it. |
| `--out` | The stage output folder. Writes `reports/<id>.md` and `evidence/<id>-*.{tsv,txt}`. |
| `--days` | Trend window length. Defaults to the probe's `trendDays`, then 90. |

Default exclusions: `node_modules`, `.next`, `dist`, `build`, `coverage`, minified files.

### Measure Block

| Key | Meaning |
|-----|---------|
| `mode` | `content` tests each pattern against file text. `path` tests it against the file path. |
| `candidates.include` | Globs of files to examine. Supports `**`, `*`, `?`, and `{a,b}`. |
| `candidates.exclude` | Globs to skip, added to the defaults. |
| `candidates.noDefaultExcludes` | `true` turns the default exclusions off. |
| `variants[].name` | Label shown in tables. |
| `variants[].any` | List of regular expressions. The variant matches if any one does. |
| `variants[].flags` | Regex flags. Defaults to `m` (multiline). |
| `trendDays` | Optional window length. |

A file matching several variants is classed as `a+b`. A file matching none is `none`. In JSON, write a backslash as `\\`.

### Adding a Probe

Copy an existing probe file, change the title, the `Question:` line, and the variants. Run it against a known repo and check the counts by hand on a few files before trusting it.

## probe-runner.mjs

Bookkeeping and validation. Never reads the target repo except to compare the HEAD sha.

| Command | Use |
|---------|-----|
| `list --probes <dir>... --out <dir>` | Shows each probe as `pending`, `needs-interpretation`, `done`, or `invalid`. |
| `validate --out <dir> [--repo <dir>]` | Checks every report against `shared/probe-report-schema.md`. With `--repo`, also flags stale reports. Exit 1 on any failure. |
| `validate-candidates <file> [--final]` | Checks candidate blocks. `--final` also rejects pending decisions and uncorroborated ratifications without a note. |
| `validate-rules <file>` | Checks rule blocks and the status rules in `shared/rules-manifest-schema.md`. |

## Safety

Neither script writes to the target repository. `measure.mjs` writes only under `--out`.
