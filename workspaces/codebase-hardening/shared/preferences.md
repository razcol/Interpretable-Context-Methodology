# Preferences

Set once during `setup`. Stages load only the section they need.

## Primary Stack

{{PRIMARY_STACK}}

Picks which playbook loads. See `playbooks/CONTEXT.md` for the stacks that exist.

## Ratifier

{{RATIFIER_NAME}}

The person who approves which conventions become rules. Notes from other reviewers are pasted into the conversation at the ratification checkpoint and recorded against the candidate.

## Branch Prefix

{{BRANCH_PREFIX}}

Every branch the implement stage creates in a target repo starts with this prefix. Branches are never pushed or merged by the workspace.

## Check Command

{{CHECK_COMMAND}}

The one command that runs every gate. CI calls this same command. It must fail closed: any gate error, missing tool, or crash is a non-zero exit.

## Allowed Dev Tools

{{ALLOWED_DEV_TOOLS}}

Dev dependencies the implement stage may add to a target repo, pinned to exact versions. Anything not listed needs a new approval. Nothing here may change the application, its runtime dependencies, or its bundle.
