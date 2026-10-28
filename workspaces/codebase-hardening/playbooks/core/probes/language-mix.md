# Probe: language-mix

Question: Is the source TypeScript, JavaScript, or a mix?

## Measure

```json measure
{
  "mode": "path",
  "candidates": { "include": ["**/*.{js,jsx,mjs,cjs,ts,tsx}"], "exclude": ["**/*.config.*", "**/*.d.ts"] },
  "variants": [
    { "name": "typescript", "any": ["\\.(ts|tsx)$"] },
    { "name": "javascript", "any": ["\\.(js|jsx|mjs|cjs)$"] }
  ]
}
```

## Interpret

- The trend table matters most. New files in TypeScript on a JavaScript base means a migration is underway.
- A project with no TypeScript files cannot be given type-based rules. Say so plainly.
