# Probe Report Schema

The fixed shape of every probe report. `scripts/probe-runner.mjs validate` enforces it. A report that fails validation does not move downstream.

## Principles

- **Scripts measure, agents interpret.** Everything above `## Interpretation` is written by a script and can be rerun. `## Interpretation` and `## Unknowns` are agent judgment.
- **Pointers, not contents.** Reports hold `path:line` pointers. Bulk lists go to `evidence/`. Nobody pastes file contents into a report.
- **Small on purpose.** A report is at most 6000 characters. A reader should never need more than one report at a time.
- **No number without a command.** Every count can be reproduced from the commands in `## Method`.

## Front Matter

| Key | Value |
|-----|-------|
| `probe` | The probe id. Must equal the file name without `.md`. |
| `question` | The one question the probe answers. |
| `status` | `needs-interpretation` from the script. The agent sets `complete` when done. |
| `confidence` | `unset` from the script. The agent sets `high`, `medium`, or `low`. |
| `repo_sha` | HEAD of the target repo when measured. Reports older than HEAD are stale. |
| `generated` | ISO timestamp. |

## Sections, In Order

| Section | Written by | Content |
|---------|-----------|---------|
| `## Method` | script | The exact commands, plus notes such as a dirty tree or shallow clone |
| `## Population` | script | Candidate files, files matching a variant, files matching none |
| `## Distribution` | script | Table of variants with file counts and shares |
| `## Trend` | script | Added and touched counts per variant in the window, dominant overall versus dominant among additions, and a divergence flag |
| `## Exemplars` | script | At most 3 `path:line` pointers per variant |
| `## Outliers` | script | Count of matched files outside the dominant variant, first 10 inline, full list in evidence |
| `## Interpretation` | agent | What the facts mean. At most 1200 characters. No TODO text left. |
| `## Unknowns` | agent | What the probe could not determine, or `None`. |

## Trend Window

The window is N days ending at the latest commit, not at today, so a quiet repository still has a trend. Default is 90 days.

Treat the trend as weak when the script notes a bulk import (90 percent or more of matched files added in the window) or a shallow clone.

## Evidence Files

Written to `evidence/` next to `reports/`:

- `<probe>-files.tsv`: every candidate file with its class, line, and whether it was added or touched in the window.
- `<probe>-outliers.txt`: the full outlier list.

Evidence is pulled only by a drill-down task that names the file and a slice (at most 50 lines) and returns at most 10 lines.

## Drill-Down Rule

An agent may open at most 5 source files per probe, and only files named in that report's Exemplars or Outliers. Anything broader is a new probe, not a drill-down.
