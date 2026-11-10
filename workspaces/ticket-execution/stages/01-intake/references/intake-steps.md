# Intake steps

## Attachment downloads

ACLI lists attachments but cannot download them. `intake.py` downloads them over REST when its env file holds:

```
JIRA_EMAIL=<your Atlassian email>
JIRA_API_TOKEN=<token from https://id.atlassian.com/manage-profile/security/api-tokens>
```

The file is `~/.config/jira/jira.env`. You create it in your own terminal (`chmod 600`). Never paste the token into chat. The agent never prints, opens or copies this file; only `intake.py` reads it.

Without the file, `ticket.md` shows `[image: <name>, not downloaded]` where each image sits, and the attachment table says `no credentials`. The run goes on. Say which images are missing and that you can drop them into `output/<KEY>/attachments/` under their Jira file names and type `start <KEY>` again; the re-run marks them `provided` and links them.

## intake.md

Written by the agent after reading `ticket.md` and the images. English. Hebrew ticket text keeps its original wording in quotes where a word matters (a label, a heading, a button text).

```markdown
# <KEY> intake

- ticket: <browse URL>
- summary: <one English sentence>
- type / status: <type> / <status>
- repo: <repo name from targets/repos.md>
- root: <root>
- app root: <root>/code
- linked: <keys and one line each, or none>

## What is asked
<3 to 8 sentences in English: the change, where it shows, for whom.>

## Repro
<Steps from the ticket, or "none in the ticket". For a bug with no steps, write the steps the description implies and mark them "inferred".>

## Acceptance
<Numbered list. Every concrete requirement from the description, the images and the comments, one per line, each tagged with its source: (description), (image <file>), (comment <author> <date>). Later comments win over earlier text; say so on the line when they conflict.>

## Images
<One line per image: file, what it shows (desktop or mobile, which part), then either the Acceptance line numbers that cite it or 'carries no requirement: <why>'.>

## Gaps
<Missing images, truncated comments, unclear requirements, questions for the reporter. Or "none".>
```

## Re-runs

A second `start` on the same key (QA returned it, new comments, a new image) reruns intake into the same folder. Before overwriting, read the old `intake.md` "Acceptance" list. In the new one, mark each line `new`, `changed` or `same`. Stage 03 plans only the `new` and `changed` lines, on the existing branch.
