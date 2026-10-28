# Dispatch

The only file that knows about agent harnesses. Everything else in the workspace is plain files, so switching harness means editing this file and nothing else.

## Rule

Running work in parallel is an optimization. The workspace must give the same result when one agent does every task in order.

## Work Units

| Stage | One unit of work | Worker receives | Worker returns |
|-------|------------------|-----------------|----------------|
| 02 measure | One probe | Probe file path, repo path, output folder, path to `shared/probe-report-schema.md` | The path of a valid report |
| 04 enforcement design | One rule's dry run | Rule block, repo path, dry-run technique from the plan format | The integer count and up to 3 examples |
| 06 verify | One rule's violation test | Change log row, worktree path, bypass list | A caught or missed result with the command used |

A worker never receives the whole workspace, other workers' reports, or the conversation. Hand over paths, not pasted content.

## Fallback: One Agent, In Order

1. Take the next pending unit from the listing command.
2. Do the unit. Write its result file.
3. Forget the unit's details. Carry only the result file path forward.
4. Repeat, then run the validator.

Reports are small and live on disk, so nothing piles up in context.

## With Subagents

If the harness can start subagents:

1. List pending units.
2. Start one worker per unit, in batches no larger than the harness allows.
3. Give each worker only what the table above lists.
4. Collect the returned paths. Run the validator. Re-dispatch any unit that fails validation, once. A second failure goes to the user.

Check what the current harness supports before relying on it. Capabilities differ, and the set of worker roles can be limited.

## Independent Verification

Stage 06 must not reuse the context of the agent that implemented the rules. Use a fresh session or a fresh worker that has only the change log and the branch.

## Local Write Blocking

Some harnesses can run a check before a tool call and block it. Use that to stop writes to protected files (see `shared/tamper-protection.md`, B2 and B3). Example for Kiro: a `PreToolUse` hook stored in `.kiro/hooks/` whose command exits with code 2 when the target path matches the protected list. For other harnesses, use their equivalent. This is a convenience on one machine. CI remains the gate.

## Keeping This File Current

When the harness changes, update only this file: the work-unit mechanics, batch limits, and hook examples.
