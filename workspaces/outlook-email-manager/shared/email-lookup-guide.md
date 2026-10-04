# Email Lookup Guide (ad-hoc "find me the email with X")

How to find a specific piece of information (an ID number, a link, a name, a value) in the mailbox when the user asks. This is separate from the triage/draft pipeline. It is read-only and never changes mail.

All commands go through `skills/outlook-automation/outlookctl-bridge.sh` (see `skills/outlook-automation/SKILL.md`).

## Procedure

1. **Search the user's literal term first.** Use the exact string the user gave, character for character, including punctuation and the language it was written in. Do not start from the topic.

   ```bash
   ./outlookctl-bridge.sh search --folder inbox --query "ת.ז" --count 10 --include-body-snippet
   ```

   Example: for "find the ID (ת.ז) someone sent me about the personal area", run `--query "ת.ז"` before anything about "איזור אישי" or "self service".

2. **Treat punctuation and spelling as part of the term.** These are different searches and return different results:
   - `"ת.ז"` finds the emails that write it with the dot (the right ones in the verified case).
   - `"תז"` (no dot) returned a different set that missed the target.
   - `"תעודת זהות"` (full phrase) returned nothing, because the sender never wrote it.

   If the literal term returns too little, try the variants the sender might have used: with and without dots or quotes (`ת.ז`, `ת"ז`, `תז`), the full phrase, and the English form. Run each as its own search and compare.

3. **Search by term, then narrow by topic.** Topic words ("איזור אישי", "self service") are a filter for picking among the hits. The email holding the value may not contain the topic words at all, and spelling varies (`איזור` vs `אזור`), so do not use topic words as the only query.

4. **Read the top hits' full bodies.** `--include-body-snippet` only shows about the first 200 characters, so a value further down the email will not appear in it. Open the most likely hits with `get`:

   ```bash
   ./outlookctl-bridge.sh get --id "<entry_id>" --store "<store_id>" --include-body
   ```

   Open the best candidate by subject, sender and date first. Do not open every result.

5. **Extract only what was asked for.** Bodies can contain credentials (passwords, API tokens). Filter the body for the relevant lines (for example with a regex for the term or a digit pattern) rather than printing it whole, and never repeat credentials back to the user.

6. **Check for more than one value.** An email can list several people's values (one line per person). Report the one that belongs to the user, and say which line it came from.

7. **Report the source.** Give the value plus the email's subject, sender and date, so the user can confirm it.

## Other folders

`search` defaults to `--folder inbox`. If the term finds nothing useful in the inbox, repeat the search with other folders via `--folder`. Not yet verified: folder names other than `inbox`. Check the accepted names in `skills/outlook-automation/reference/cli.md` or with `list`.

## Running commands reliably from this workspace

- Run bridge commands one at a time, redirecting output to a file.
- The agent terminal often returns empty or delayed output. Read the result through the file tools instead of the terminal, e.g. a file written to `/tmp/x.out` is readable at `\\wsl.localhost\Ubuntu\tmp\x.out`.
- Parse JSON output with a short Python script instead of eyeballing it. A file read too early can be empty or incomplete, so re-read if parsing fails.
- Delete any temporary files created under `/tmp` when done.
