# Probe: export-style

Question: Do modules use default exports, named exports, or CommonJS exports?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,mjs,cjs,ts,tsx}"], "exclude": ["**/*.config.*"] },
  "variants": [
    { "name": "default-export", "any": ["^export default\\b"] },
    { "name": "named-export", "any": ["^export (const|function|class|let|var|async function|type|interface|enum)\\b", "^export \\{"] },
    { "name": "commonjs", "any": ["\\bmodule\\.exports\\b", "^exports\\."] }
  ]
}
```

## Interpret

- Frameworks require default exports in some files (for example Next.js `page` and `layout`). Separate those from components before calling a style dominant.
- A split by folder (components use named, routes use default) is a convention. A random split is not.
