# Probe: test-placement

Question: Where do test files live, and how are they named?

## Measure

```json measure
{
  "mode": "path",
  "candidates": { "include": ["**/*.{js,jsx,mjs,ts,tsx}"] },
  "variants": [
    { "name": "suffix-test-or-spec", "any": ["\\.(test|spec)\\.(js|jsx|mjs|ts|tsx)$"] },
    { "name": "dunder-tests-dir", "any": ["(^|/)__tests__/"] },
    { "name": "top-level-test-dir", "any": ["^(tests?|e2e|cypress|playwright)/"] }
  ]
}
```

## Interpret

- Candidates are all source files, so the share of `none` is the share of files without a test marker. Do not read it as coverage.
- If no variant matches, report that the project has no tests. Do not invent a convention.
- Note whether tests sit next to their source (suffix) or in a separate tree.
