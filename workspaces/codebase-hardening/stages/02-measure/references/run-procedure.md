# Measure Run Procedure

How to run the probes without overloading any agent.

## Setup

Let `REPO` be the app root from the project profile. Let `OUT` be this stage's `output/` folder.

```
node ../../scripts/probe-runner.mjs list \
  --probes ../../playbooks/core/probes \
  --probes ../../playbooks/<stack>/probes \
  --out output
```

Use the stack folder named in the playbook routing file. Run from this stage folder, or adjust the paths.

## One Probe

1. Run `node ../../scripts/measure.mjs --probe <probe.md> --repo REPO --out output`.
2. Read only the generated `output/reports/<id>.md` and the `## Interpret` notes of the probe file.
3. Fill `## Interpretation` (at most 1200 characters) with what the facts mean. Fill `## Unknowns`. Set `confidence` to high, medium, or low. Set `status` to `complete`.
4. If one fact needs a closer look, open at most 5 files named in Exemplars or Outliers, or read a slice of 50 lines or less of the evidence file. Do not search the repo.
5. Do not read any other report.

## Confidence

| Level | Use when |
|-------|----------|
| high | The population is large, the trend agrees with the distribution, and no script note warns about history. |
| medium | The distribution is clear but the trend is weak or divergent. |
| low | The population is small, the script noted a shallow clone or bulk import, or the pattern is a heuristic. |

## Skipped Probes

Probes the profile marks not applicable are not run. Write them to `output/skipped-probes.md` with the reason, one per line.

## Validate

```
node ../../scripts/probe-runner.mjs validate --out output --repo REPO
```

The stage is done only when this exits 0. It fails on missing sections, TODO text, oversize reports, bad confidence, missing evidence files, and a HEAD that moved since measuring.

## If HEAD Moved

Reports from an older sha are stale. Stop and tell the user. Re-run recon for a new profile, then run the probes again.

## Dirty Working Tree

Content is read from the working tree and history from HEAD. The script notes this in each report. Mention it in Unknowns for probes whose candidate files include a changed path.
