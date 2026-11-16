# Worker Brief and Return Shape

## Brief template

Fill every line. Leave a line out only if it truly does not apply (write `none`).

```text
Goal: <one sentence: what this unit must produce>
Inputs (read these yourself): <path>, <path>, ...
Write only: <output path or folder>. Do not edit anything else.
Already ruled out / do not redo: <facts or approaches settled before this unit, or none>
Secrets: <secrets file path + key names, or none>. Never print the values.
Rules: follow <CONTEXT.md / spec path> if one exists.
Return exactly these lines and nothing else:
  output: <path>
  checks: one line per audit row, "<row> PASS|FAIL <evidence>"
  waiting: <checkpoint question, or none>
Do not start the next unit.
```

For a fan-out, keep one template with `{unit}`, `{input_path}`, `{output_path}` placeholders and fill it per unit. Every worker gets the same wording.

## What never goes into a brief

- Contents of files the worker can read (pass the path).
- Another worker's output text (pass its output path).
- This conversation's history, or your own conclusions about the answer (they anchor the worker).
- Credentials, OTPs, passwords, tokens.

## Worker side of the contract

A workspace can point its stage files here instead of repeating it:
- Write your output to the given path. If every write is refused, return the full text and the target path, and say the write failed. The orchestrator reports it; it does not write the file for you.
- Return the shape above and nothing longer.
- Do not open the next unit's or stage's files.
