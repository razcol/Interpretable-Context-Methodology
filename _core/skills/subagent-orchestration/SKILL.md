---
name: subagent-orchestration
description: "How to run work as an orchestrator with subagents in Cursor or Claude Code: when to split, how to cut units, how to brief and spawn workers (one or many similar), which model and effort to set (light, mid, or strong tier), how to check returns, retry and report. Use for ad-hoc tasks and for workspaces that delegate units or stages."
---

# Subagent Orchestration

Applies to any task that might be split across subagents, in a workspace or not. A workspace that uses this skill keeps only its own stage order, gates, unit table rows and record formats.

## 1. Decide whether to orchestrate

Split the work only when at least one holds:
- The pieces are independent and each needs real reading or work (parallel saves time).
- A piece would flood your context with file dumps you only need the conclusion of.
- You need a review that has not seen your reasoning (an independent verifier).
- A workspace tells you to spawn a worker per stage or unit.

Do it yourself when the work is a handful of tool calls, when the pieces depend tightly on each other, or when writing the brief would take longer than the work. When the harness cannot spawn subagents, run the units yourself, one at a time, in the order of section 3. The result must be the same.

## 2. The orchestrator role

Once you split, you plan, spawn, check returns and report. You do not:
- do a unit's work yourself, or redo a worker's work after it returns;
- carry one worker's content into another worker's brief (pass the output **path**);
- write a worker's record for it. A return that pastes the record text instead of writing the file counts as a missing file.

A workspace may let the orchestrator keep its run claim (claim, commit, end with the workspace's claim helper). Nothing else.

## 3. Cut the work into units

Output paths: inside a workspace, the run folder its CLAUDE.md names (`<runs>/<KEY>/...`). Work that belongs to a workspace run but to no stage, such as WP content for a Figma section, goes into that run's folder (the workspace's run-records file says where). Other results worth keeping go to `<data-root>/archive/<topic>/`; throwaway files go to the session's temp folder. Never into the ai-system repo. `<data-root>` is the path `python3 ../../data-root/data_root.py resolve` prints from this skill folder.

For each unit write one row: name, inputs (paths), output (path or short value), depends on, tier. Use the format in [references/unit-table.md](references/unit-table.md).
- A unit is one thing a worker can finish and you can check: one file, one probe, one stage, one module.
- Units with no `depends on` may run in parallel. Units that read another unit's output run after it.
- Running the units in parallel must give the same result as running them one by one. Units never write the same file. If two would, merge them or give each its own output and merge after.
- "Same result" applies to what can be checked: facts, counts, paths, pass/fail rows. Judgment text (findings, wording) differs between any two runs, parallel or not. Give each unit's output fixed fields for the checkable part and a separate field for judgment, and compare only the fixed fields.
- If a finished unit's checked output already answers a unit that has not started, drop that unit and log it as dropped with the reason (section 7).

## 4. Brief and spawn

Use the template in [references/brief-template.md](references/brief-template.md). Every brief has: goal, inputs as paths, write scope, what is already ruled out, return shape. Never paste file contents the worker can read. Never put a credential, OTP, password or token in a brief. Name the secrets file and the key names.

Fresh worker or fork: start a fresh worker by default. Fork (Claude Code) only when the unit needs this conversation's context and the parent's model is acceptable for it, because a fork ignores `model` and `effort`.

Several workers on similar units: write one brief template with `{placeholders}` and fill it per unit. Launch independent units in the same turn, in batches no larger than the harness allows (see the harness file). Collect every return before merging. Merge from the output files, not from memory.

## 5. Model and effort

Every spawn sets the model explicitly. There are three tiers. **No `*-fast` speed modes, no `auto`, no `inherit`, no unset model, in any harness.**

| Tier | Use when | Never use for |
|------|----------|---------------|
| `light` | Bounded, checkable, low-ambiguity work (est. 1–3 steps): read-only codebase/doc lookups, structured extraction, summarizing existing records, deterministic wrapper commands (intake, handoff formatting, git release) | Editing application code, code review, verification/auditing, multi-step debugging, ambiguous synthesis |
| `mid` | Default for real work: scoped code implementation, multi-file research, browser/test verification, screenshots, routine change passes | Architectural planning, unclear-root-cause debugging, security/auth/payment changes |
| `strong` | Planning and design decisions, unclear-root-cause debugging, changes to shared interfaces, auth, payments, security review, cross-cutting synthesis, or a `mid` retry | — |

Rules:
- **Availability fallback vs. quality escalation:**
  - *Availability fallback* (harness has not enabled the primary or rejects it): walk the slot's ranked top 3 in order (`primary -> fallback 1 -> fallback 2`). Never skip ahead, never leave the slot, never use a banned slug. If none of the 3 is accepted, stop and report the unit with the 3 slugs tried.
  - *Quality escalation* (the unit ran and failed its check): retry once, one tier up (`light -> mid -> strong -> strong/hardest`). Never retry past `strong/hardest` (`models.py pick --tier strong --hardest --retry` exits 2).
- **Verifier integrity:** Verification, audit, and code-review units are at least `mid` (and at least the implementer's tier). Never downgrade a verifier to `light`.
- A workspace may set a base tier per unit and list file-checkable conditions to step up. It fills the rows; this skill owns the format and rules.

Get the exact call fields from `scripts/models.py` (backed by [references/tiers.json](references/tiers.json), the single source of truth). Resolve all tiers once at run start with `table`, or query one slot with `pick`. Do not type a slug from memory:

```bash
python3 scripts/models.py table --harness cursor --available <enabled,slugs>
python3 scripts/models.py pick --harness claude-code --tier light --readonly
python3 scripts/models.py pick --harness cursor --tier mid --retry --available <enabled,slugs>
python3 scripts/models.py check --harness cursor   # every primary and fallback still exists and none is banned
```

`pick` prints the call fields and a `fallbacks:` line (add `--json` for one JSON object, `--readonly` for `explore`/`Explore`). `table` resolves all four slots (`light`, `mid`, `strong`, `strong/hardest`) in one call. With `--available`, both pick the first enabled entry in each slot and exit 2 when none is. `check` prints `SKIP: cursor-agent models unavailable (...)` when offline or sandboxed; that is "not verified", not a failure.

If the script cannot run, read [references/tiers.json](references/tiers.json) and the harness notes: [Claude Code](references/harness-claude-code.md), [Cursor](references/harness-cursor.md).

## 6. Check each return

A unit passes only when all hold:
1. The output exists at the agreed path (open it; do not trust the return text).
2. The return has the agreed shape. Extra prose after the agreed lines is not a failure; ignore it and read the file.
3. Its audit or acceptance rows pass.

On a failure, spawn the same unit once more, one tier up (`--retry`), with the failed rows in the brief. A second failure (or hitting the `strong/hardest` ceiling): stop and report the unit, the failed rows and both models. Do not do the unit yourself.

Blocked is not failed. When the output says a rule, permission or missing access stopped the unit (not a weak result), do not retry: a stronger model meets the same wall. Log it as blocked, keep the other units going, and ask the user for the one decision that would unblock it, unless later returns make the unit unnecessary (section 3). Never brief a worker to get around the rule.

A notice that a background job finished is not a result. Check the output.

## 7. Report progress

One line per finished unit:

```text
<unit> -> <model passed> (<tier>; <why: base | step-up reason | retry>) -> <output path or value>
<unit> -> <model passed> (<tier>; base) -> blocked: <rule or access that stopped it>
<unit> -> dropped: <which return already answered it>
```

## 8. Optional pieces

- **Run claim** (keyed workflows): before the first spawn, claim the run key (`python3 ../../data-root/run_claim.py claim --ws <ws> --key <KEY>` from this skill folder; "Run claims" in `_core/CONVENTIONS.md`) and keep the `claimId` it prints. A live claim on the same key stops the run: report the claim it names. A stale one (its process or checkout is gone) is replaced and reported, and the run continues from its records. Runs on other keys go on at the same time; never a workspace-wide lock file. After each unit passes its check, commit the run folder (`run_claim.py commit`). When the run ends or is stopped, end the claim in a separate shell call (`run_claim.py end --ws <ws> --key <KEY> --claim-id <claimId>`), never chained after `commit` with `&&`. `release --token` is the deprecated name of `end --claim-id`.

  When a workflow supports multiple runs per ticket (`ticket-execution`), `claim` passes `--base <base>` and, when the user named an approach, `--label <label>`. Every later `port`, `target`, `commit`, and `end` uses the `runId` that `claim` printed as `--key <runId>`. The slug and slot rules live in `_core/CONVENTIONS.md`.
- **Independent verifier**: a fresh worker that gets only the change summary and the paths to check, never the implementer's brief or return. Tier at least `mid` and at least the implementer's tier.
