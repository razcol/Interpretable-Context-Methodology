# Probe: file-naming

Question: Which file naming style do source files use?

## Measure

```json measure
{
  "mode": "path",
  "candidates": { "include": ["**/*.{js,jsx,mjs,ts,tsx}"], "exclude": ["**/*.config.*", "**/*.d.ts"] },
  "variants": [
    { "name": "single-word-lowercase", "any": ["(^|/)[a-z0-9]+\\.(js|jsx|mjs|ts|tsx)$"] },
    { "name": "kebab-case", "any": ["(^|/)[a-z0-9]+(-[a-z0-9]+)+(\\.[a-z0-9]+)*\\.(js|jsx|mjs|ts|tsx)$"] },
    { "name": "PascalCase", "any": ["(^|/)[A-Z][A-Za-z0-9]*(\\.[a-z0-9]+)*\\.(js|jsx|mjs|ts|tsx)$"] },
    { "name": "camelCase", "any": ["(^|/)[a-z][a-z0-9]*[A-Z][A-Za-z0-9]*(\\.[a-z0-9]+)*\\.(js|jsx|mjs|ts|tsx)$"] },
    { "name": "snake_case", "any": ["(^|/)[a-z0-9]+(_[a-z0-9]+)+(\\.[a-z0-9]+)*\\.(js|jsx|mjs|ts|tsx)$"] }
  ]
}
```

## Interpret

- Single-word lowercase names fit every convention, so judge the rest by the other variants.
- Framework-mandated names (for example `page.tsx`, `layout.tsx`) are not a style choice. Say so if they dominate.
- Check whether components and non-components follow different styles. Use the files list in evidence if needed.
