# Tone Profile Setup (One-Time)

Derive a voice/tone reference from the user's sent email. Runs once, ahead of the per-run pipeline, not every time.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Outlook (via outlookctl) | Sent folder | Last 50-100 sent emails (default, adjustable) | Raw material to derive voice from |
| Skill | `../skills/outlook-automation/SKILL.md` | Full file, then `reference/cli.md` as needed | outlookctl `search`/`get` against the Sent folder |
| User | (conversation) | Sanity-check edits after first draft | Catch misreads before the profile is finalized |

## Process

1. Pull a batch of sent emails: `outlookctl search --folder sent --count 100 --include-body-snippet`, then `outlookctl get --include-body` on a representative sample.
2. Derive voice patterns: greeting/sign-off style, structure and length tendencies, formality range, common phrasings.
3. Write the derived profile to `../shared/tone-profile.md`, with a trailing Manual Notes section left empty.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 2 | The derived tone profile (all sections) | Whether the patterns are accurate before finalizing; user edits directly |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Section completeness | Every section (Greeting/Sign-off, Structure & Length, Formality, Common Phrasings) has concrete, specific content derived from actual sent emails, not a generic placeholder statement |
| Evidence grounding | Every documented pattern traces back to at least one specific example seen in the sampled sent emails, not a general assumption about how the user "probably" writes |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Tone profile | `../shared/tone-profile.md` | Sectioned markdown: Greeting/Sign-off Patterns, Structure & Length Tendencies, Formality Range, Common Phrasings, Manual Notes |

## Note

Run once. Re-run only if the user explicitly wants to re-derive from scratch. Ongoing refinement happens by editing the Manual Notes section directly in `shared/tone-profile.md` -- not by re-running this setup.
