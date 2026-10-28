# Candidates Format

How to turn probe reports into convention candidates. The block fields are defined in `../../../shared/rules-manifest-schema.md`, section "Candidate Block". This file covers only the method.

## Reading The Reports

Read every report in `../02-measure/output/reports/`. Do not open the evidence folder, and do not open source files. If a claim needs more detail, use a drill-down task: name one evidence file, read a slice of at most 50 lines, and write down at most 10 lines of what you found.

## From Facts To Candidates

1. Group reports by dimension: naming, layout, imports, styling, data access, boundaries, environment, tests, suppressions.
2. For each dimension, state the dominant variant from Distribution.
3. Read Trend. If `divergent: yes`, the newest code disagrees with the majority. Record `trend: migration` and make the candidate rule follow the direction of the new code, not the majority. Say so in the candidate.
4. If additions are too few to judge, record `trend: stable` only when the script says the window held at least 5 additions. Otherwise write "too few additions to judge".
5. Write `risk_if_wrong` in concrete terms: what breaks, or what good code becomes forbidden.
6. One candidate states one rule. Split compound rules.

## Corroboration

A candidate that would be enforced at error level needs a second, independent report that agrees. Independent means a different method:

| First evidence | Acceptable second evidence |
|----------------|----------------------------|
| A content pattern count | The dependency list in the project profile, or a path-based report |
| A path pattern count | A content report or git-history trend |
| A dependency list | A content pattern count |

Write the second report's name and its number. If none exists, write `corroboration: none`. The ratifier may accept a single probe by adding a `ratifier_note`.

## What Not To Do

- Do not invent a convention the data does not show. A split with no clear majority is a finding, not a rule.
- Do not promote a heuristic (for example Tailwind class detection) without corroboration.
- Do not recommend a mechanism yet. Mechanisms are chosen in the next stage.

## The Ratification Table

Present candidates to the ratifier as one table: id, rule, dominant, trend, corroboration, risk. The ratifier answers per id: ratify, reject, or change (with new wording). Notes from other reviewers, pasted in the conversation, are copied into `ratifier_note`.

## Validation

```
node ../../scripts/probe-runner.mjs validate-candidates output/conventions-candidates.md --final
```

Run it after the decisions are applied. It fails on pending decisions and on ratified candidates with no corroboration and no note.
