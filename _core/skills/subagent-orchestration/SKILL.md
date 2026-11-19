---
name: subagent-orchestration
description: "How to run work as an orchestrator with subagents in Cursor or Claude Code: when to split, how to cut units, how to brief and spawn workers (one or many similar), which model and effort to set (mid or strong tier, never fast), how to check returns, retry and report. Use for ad-hoc tasks and for workspaces that delegate units or stages."
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

A workspace may let the orchestrator keep its run claim (claim, commit, release with the workspace's claim helper). Nothing else.

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

Every spawn sets the model explicitly. There are two tiers. **Mid is the floor. No fast models, no fast modes, no `auto`, no `inherit`, nothing below mid, in any harness.**

| Tier | Use when |
|------|----------|
| mid | Default: scoped implementation, reading and summarizing, lookups, extraction, running known commands, screenshots, routine checks |
| strong | Planning and design decisions, unclear-root-cause debugging, changes to shared interfaces, auth, payments, security review, synthesis across many sources, a unit whose mid attempt failed |

Rules:
- A retry goes one tier above the first attempt (mid -> strong; strong -> the "hardest" row in the harness file). In Cursor, Grok strong escalates to Claude Opus, not to a higher Grok effort.
- A rejected model falls back sideways (the same tier's alternate, for example Grok in Cursor) or up. Never down, never to a fast variant, never to unset.
- A workspace may set a base tier per unit and list when to leave it. It fills the rows. This skill owns the format and these rules.

Get the exact call fields for the current harness from `scripts/models.py`. Copy its output. Do not type a slug from memory:

```bash
python3 scripts/models.py pick --harness claude-code --tier mid
python3 scripts/models.py pick --harness cursor --tier strong --family grok --retry
python3 scripts/models.py check --harness cursor   # mapped slugs still exist and none is fast
```

If the script cannot run, read the harness file: [Claude Code](references/harness-claude-code.md), [Cursor](references/harness-cursor.md). The mapping lives in [references/tiers.json](references/tiers.json).

## 6. Check each return

A unit passes only when all hold:
1. The output exists at the agreed path (open it; do not trust the return text).
2. The return has the agreed shape. Extra prose after the agreed lines is not a failure; ignore it and read the file.
3. Its audit or acceptance rows pass.

On a failure, spawn the same unit once more, one tier up, with the failed rows in the brief. A second failure: stop and report the unit, the rows and both models. Do not do the unit yourself.

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

- **Run claim** (keyed workflows): before the first spawn, claim the run key (`python3 ../../data-root/run_claim.py claim --ws <ws> --key <KEY>` from this skill folder; "Run claims" in `_core/CONVENTIONS.md`) and keep the token it prints. A live claim on the same key stops the run: report the claim it names. A stale one (its process or checkout is gone) is replaced and reported, and the run continues from its records. Runs on other keys go on at the same time; never a workspace-wide lock file. After each unit passes its check, commit the run folder (`run_claim.py commit`). Release it with the token when the run ends or is stopped (`run_claim.py release`).
- **Independent verifier**: a fresh worker that gets only the change summary and the paths to check, never the implementer's brief or return. Tier at least the implementer's.
