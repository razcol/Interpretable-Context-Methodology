# Probe: import-style

Question: Do files import through an alias, through short relative paths, or through deep relative paths?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,mjs,ts,tsx}"] },
  "variants": [
    { "name": "alias-import", "any": ["(from|import)\\s*['\"](@|~)/"] },
    { "name": "deep-relative", "any": ["(from|import)\\s*['\"](\\.\\./){3,}"] },
    { "name": "relative", "any": ["(from|import)\\s*['\"]\\.{1,2}/"] }
  ]
}
```

## Interpret

- Files can match more than one variant, shown as `a+b`. A high share of mixed files means the convention is not settled.
- An alias is only real if the project config defines it. Check the recon profile for `paths` in tsconfig or jsconfig.
- Deep relative imports (three or more levels) usually mark a missing alias or a layering problem.
