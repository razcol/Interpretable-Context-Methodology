# Probe: escape-hatches

Question: How often does code suppress or bypass type and lint checks?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,mjs,ts,tsx}"] },
  "variants": [
    { "name": "ts-suppression", "any": ["@ts-(ignore|nocheck|expect-error)"] },
    { "name": "eslint-disable", "any": ["eslint-disable"] },
    { "name": "explicit-any", "any": [":\\s*any\\b", "\\bas any\\b", "<any>"] }
  ]
}
```

## Interpret

- Every match here is a future violation if a rule bans it. The count decides whether such a rule is READY or DEFERRED.
- `explicit-any` on a JavaScript project is noise from comments or strings. Say so if there are no TypeScript files.
- A high `eslint-disable` count means lint rules are already being bypassed, which raises the tamper risk for new rules.
