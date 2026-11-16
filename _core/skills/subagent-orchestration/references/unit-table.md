# Unit Table Format

Ad-hoc work: write this table in your plan before the first spawn. A workspace keeps its own filled-in copy and points to this skill for the rules.

| Unit | Inputs (paths) | Output | Depends on | Base tier | Leave the base only when |
|------|----------------|--------|------------|-----------|--------------------------|
| `<name>` | `<path>`, ... | `<path or value>` | `<unit>` or `-` | mid / strong | `<concrete condition>`, or `never` / `always strong` |

Rules for the table:
- Base tier is `mid` or `strong`. No other value.
- "Leave the base" names a condition you can check from files (for example "the plan touches `auth/`"), not a feeling.
- A condition may only raise the tier. Nothing lowers a unit below its base, and nothing goes below mid.
- Units with `-` in "Depends on" may run together. Two units never share an output path.
- Optional column `Family` (Cursor only): `claude` (default) or `grok`.
