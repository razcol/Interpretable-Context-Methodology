---
name: outlook-automation
description: >
  Automates reading, searching, drafting, and sending emails AND calendar events
  in Classic Outlook on Windows using local COM automation. Use this skill when
  the user asks to process Outlook emails, create drafts, send messages, save
  attachments, manage calendar events, create meetings, or respond to invitations
  from the authenticated Outlook session on their Windows Devbox. Requires
  Classic Outlook (not New Outlook) to be running.
---

# Outlook Automation

This skill enables email and calendar automation through Classic Outlook on Windows using the `outlookctl` CLI tool.

## How to Run Commands

`outlookctl` depends on `pywin32`, which talks to Outlook through Windows COM automation, so the process invoking it must ultimately run as a genuine Windows-native process. This workspace lives under WSL, and two approaches that look plausible do **not** work reliably here -- do not use them:

- Running `uv`/python directly from a WSL/Linux shell: `pywin32` has no Linux wheel, so `uv sync` fails immediately (confirmed: "pywin32 (v312) only has wheels for win32/win_amd64/win_arm64").
- Invoking `powershell.exe` from WSL with `--project` pointed at a `\\wsl$\...` or `\\wsl.localhost\...` UNC path: this intermittently fails ("Project directory does not exist", "network name is no longer available") because a `powershell.exe` process spawned via WSL interop runs in its own logon session, and mapped/UNC access to the WSL 9P share is scoped to the interactive desktop session, not that spawned session. A single successful run this way does not mean it is reliable -- it has been observed to fail on a subsequent, otherwise-identical invocation.

**The verified, repeatable pattern:** mirror `outlookctl-src/` to a native Windows path (`%LOCALAPPDATA%\outlookctl-bridge`), then invoke `uv`/python via `powershell.exe` against that native path. This is wrapped in a helper script -- use it instead of hand-rolling the PowerShell call:

```bash
./outlookctl-bridge.sh <command> [options]
```

For example:
```bash
./outlookctl-bridge.sh doctor
./outlookctl-bridge.sh category list
./outlookctl-bridge.sh list --folder inbox --unread-only --count 20
```

The script (`outlookctl-bridge.sh`, next to this file):
1. Syncs `outlookctl-src/` (source + `pyproject.toml`/`uv.lock`, never the WSL-side `.venv`) to `%LOCALAPPDATA%\outlookctl-bridge` on the Windows side.
2. Runs `uv.exe` (by full path -- the `uv` installer does not always put it on Windows `PATH`) from that native path via `powershell.exe`.
3. Decodes PowerShell's redirected output (UTF-16LE with BOM by default) back to UTF-8 and propagates the real exit code.

**Run bridge commands one at a time.** Every call shares a single temp file (`_bridge_out.tmp`) on the Windows side. Two concurrent calls collide ("file is being used by another process"), and one of them fails. Also, when run from an agent shell, redirect output to a file (`> /tmp/x.out 2>&1`) and read that file, because terminal output is often empty or garbled.

This is a locally patched copy of outlookctl (see "Local Patch: Categories" below). The tool source lives at `outlookctl-src/` next to this file, and is mirrored automatically by the bridge script -- you do not need to copy it manually.

## Quick Start

Before using any commands, verify the environment:

```bash
./outlookctl-bridge.sh doctor
```

All four checks (`windows_os`, `pywin32`, `outlook_com`, `outlook_exe`) must show `"passed": true`. If `outlook_com` fails, start Classic Outlook first.

## Available Commands

### Email Commands

| Command | Description |
|---------|-------------|
| `doctor` | Validate environment and prerequisites |
| `list` | List messages from a folder |
| `get` | Get a single message by ID |
| `search` | Search messages with filters |
| `draft` | Create a draft message (supports --reply-all) |
| `send` | Send a draft or new message |
| `move` | Move message to another folder |
| `delete` | Delete a message (soft or permanent) |
| `mark-read` | Mark message as read/unread |
| `forward` | Create a forward draft |
| `attachments save` | Save attachments to disk |
| `category list` | List all categories defined on the mailbox (local patch) |
| `category get` | Get the categories assigned to a message (local patch) |
| `category set` | Assign, add, or remove categories on a message (local patch) |
| `search --category <name>` | Filter search results by category (local patch) |

### Calendar Commands

| Command | Description |
|---------|-------------|
| `calendar calendars` | List all available calendars (including subscribed ICS) |
| `calendar list` | List calendar events (default: next 7 days, use --all for all calendars) |
| `calendar get` | Get event details by ID |
| `calendar create` | Create an event or meeting (draft by default) |
| `calendar send` | Send meeting invitations |
| `calendar respond` | Accept, decline, or tentatively respond to a meeting |
| `calendar update` | Update event subject, time, location, etc. |
| `calendar delete` | Delete/cancel an event (sends cancellations if needed) |

**Tip:** Use `--calendar "Name"` to access non-default calendars (e.g., `--calendar "Family"`).

## Safety Rules

**CRITICAL: Follow these rules when handling email and calendar operations:**

### Email Safety
1. **Never auto-send emails** - Always create drafts first and get explicit user confirmation before sending
2. **Draft-first workflow** - Use `draft` to create drafts, show the user a preview, then send only after approval
3. **Explicit confirmation required** - The send command requires `--confirm-send YES` flag
4. **Metadata by default** - Body content is only retrieved when explicitly requested

### Calendar Safety
1. **Meetings are drafts by default** - When creating a meeting with attendees, invitations are NOT sent automatically
2. **Explicit send required** - Use `calendar send --confirm-send YES` to send meeting invitations
3. **Show preview first** - Always show the user meeting details before sending invitations
4. **Responding is safe** - Accepting/declining meetings does not require extra confirmation

## Workflows

### Reading and Searching Email

To list recent emails:
```bash
./outlookctl-bridge.sh list --count 10
```

To search for specific emails:
```bash
./outlookctl-bridge.sh search --from "sender@example.com" --since 2025-01-01
```

**Looking for a specific value or email?** Search the user's exact term first (same characters and punctuation, e.g. `--query "ת.ז"`), then narrow by topic and open the top hits with `get --include-body`. `--query` matches the body, but `--include-body-snippet` shows only about 200 characters, and `"ת.ז"`, `"תז"` and the full phrase give different results. Full procedure: `shared/email-lookup-guide.md` at the workspace root.

To get full message content (only when user asks):
```bash
./outlookctl-bridge.sh get --id "<entry_id>" --store "<store_id>" --include-body
```

### Creating and Sending Email (Draft-First)

**Step 1: Create a draft**
```bash
./outlookctl-bridge.sh draft --to "recipient@example.com" --subject "Subject" --body-text "Message body"
```

**Step 2: Show user the preview** (subject, recipients, body summary)

**Step 3: Only after user confirms, send the draft**
```bash
./outlookctl-bridge.sh send --draft-id "<entry_id>" --draft-store "<store_id>" --confirm-send YES
```

### Replying to Messages

```bash
# Create reply draft
./outlookctl-bridge.sh draft --to "recipient@example.com" --subject "Re: Original" --body-text "Reply text" --reply-to-id "<entry_id>" --reply-to-store "<store_id>"
```

### Saving Attachments

```bash
./outlookctl-bridge.sh attachments save --id "<entry_id>" --store "<store_id>" --dest "./attachments"
```

## Category Workflows (Local Patch)

These commands are not part of upstream outlookctl -- they were added to this bundled copy to support category-based triage. See `outlookctl-src/` for the patched source (`outlook_com.py`, `cli.py`, `models.py`).

### Listing the Mailbox's Categories

```bash
./outlookctl-bridge.sh category list
```

Returns the mailbox's Category Master List (name + color), not the categories on any one message. Use this before assigning a category, to check whether a matching one already exists.

### Reading Categories on a Message

```bash
./outlookctl-bridge.sh category get --id "<entry_id>" --store "<store_id>"
```

### Assigning Categories

```bash
# Replace all categories on the message (default mode)
./outlookctl-bridge.sh category set --id "<entry_id>" --store "<store_id>" --categories "Follow Up"

# Add to existing categories without removing others
./outlookctl-bridge.sh category set --id "<entry_id>" --store "<store_id>" --categories "Waiting" --mode add

# Remove a specific category, leaving the rest untouched
./outlookctl-bridge.sh category set --id "<entry_id>" --store "<store_id>" --categories "Waiting" --mode remove

# Assigning a brand-new category name: it is auto-registered in the
# mailbox's Category Master List too (not just written onto the message),
# optionally with a color
./outlookctl-bridge.sh category set --id "<entry_id>" --store "<store_id>" --categories "Follow Up" --color blue
```

**New-category registration (fixed 2026-09-23):** `category set` in `replace`/`add` mode now registers any category name that isn't already in the mailbox's Category Master List (`Namespace.Categories`) before applying it, via `ensure_categories_registered` in `outlook_com.py`. Previously it only wrote the name onto the message's `Categories` string, so new names never appeared in `category list` or Outlook's category picker/management dialog, and never got a color -- only names already in the master list (e.g. assigned once via the Outlook UI) showed up there. The response now includes a `newly_registered_categories` field listing any names that were added to the master list as part of that call (empty if all names were already registered, or in `remove` mode). Use `--color` to control the color assigned to newly-registered names (see valid names in `outlook_com.py`'s `_COLOR_NAME_TO_CONST`, e.g. `red`, `blue`, `green`, `yellow`, `steel`, `purple`, etc.) -- omit it to use Outlook's own default.

### Filtering by Category

```bash
./outlookctl-bridge.sh search --category "Follow Up"
```

Substring match against the message's category string. `list` and `search` results also include a `categories` field automatically now, with no extra flag needed.

## Calendar Workflows

### Viewing Calendar Events

To list upcoming events (next 7 days by default):
```bash
./outlookctl-bridge.sh calendar list
```

To list events for a specific date range:
```bash
./outlookctl-bridge.sh calendar list --start "2025-01-20" --days 14
```

To view a shared calendar:
```bash
./outlookctl-bridge.sh calendar list --calendar "colleague@example.com"
```

To get full event details:
```bash
./outlookctl-bridge.sh calendar get --id "<entry_id>" --store "<store_id>" --include-body
```

### Creating Events (Personal Appointments)

For events without attendees (no invitations needed):
```bash
./outlookctl-bridge.sh calendar create --subject "Focus Time" --start "2025-01-20 14:00" --duration 120
```

### Creating Meetings (Draft-First Workflow)

**Step 1: Create the meeting (saved as draft, no invitations sent)**
```bash
./outlookctl-bridge.sh calendar create \
  --subject "Team Sync" \
  --start "2025-01-20 10:00" \
  --duration 60 \
  --location "Conference Room A" \
  --attendees "alice@example.com,bob@example.com" \
  --body "Agenda:\n1. Project updates\n2. Next steps"
```

**Step 2: Show user the meeting preview** (subject, time, attendees, location)

**Step 3: Only after user confirms, send the invitations**
```bash
./outlookctl-bridge.sh calendar send --id "<entry_id>" --store "<store_id>" --confirm-send YES
```

### Creating Meetings with Teams Link

To include a Teams meeting URL in the body:
```bash
./outlookctl-bridge.sh calendar create \
  --subject "Virtual Meeting" \
  --start "2025-01-20 15:00" \
  --duration 30 \
  --attendees "team@example.com" \
  --teams-url "https://teams.microsoft.com/l/meetup-join/..."
```

Note: The Teams URL is embedded in the meeting body. For full Teams integration (automatic link generation), create the meeting in Outlook manually.

### Creating Recurring Events

Weekly standup every Monday and Wednesday:
```bash
./outlookctl-bridge.sh calendar create \
  --subject "Daily Standup" \
  --start "2025-01-20 09:00" \
  --duration 15 \
  --recurrence "weekly:monday,wednesday:until:2025-12-31"
```

### Responding to Meeting Invitations

To accept a meeting:
```bash
./outlookctl-bridge.sh calendar respond --id "<entry_id>" --store "<store_id>" --response accept
```

To decline a meeting:
```bash
./outlookctl-bridge.sh calendar respond --id "<entry_id>" --store "<store_id>" --response decline
```

To tentatively accept:
```bash
./outlookctl-bridge.sh calendar respond --id "<entry_id>" --store "<store_id>" --response tentative
```

To respond without notifying the organizer:
```bash
./outlookctl-bridge.sh calendar respond --id "<entry_id>" --store "<store_id>" --response accept --no-response
```

## Output Format

All commands output JSON with a consistent structure. Key fields:

- `version`: Schema version (currently "1.0")
- `success`: Boolean for operation result
- Message IDs include `entry_id` and `store_id` for stable references

## Reference Documentation

For detailed information, see:
- [CLI Reference](reference/cli.md) - Complete command options
- [JSON Schema](reference/json-schema.md) - Output format details
- [Security](reference/security.md) - Data handling and safety
- [Troubleshooting](reference/troubleshooting.md) - Common issues

## Requirements

- Windows with Classic Outlook running
- uv installed and in PATH
- outlookctl project at: `\\wsl$\Ubuntu\home\dev\ai-system\workspaces\outlook-email-manager\skills\outlook-automation\outlookctl-src`

## Error Handling

If commands fail, check:
1. Classic Outlook is running (not New Outlook)
2. `doctor` command passes all checks
3. Message IDs are valid and not expired
