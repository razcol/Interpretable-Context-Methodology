# Probe: server-boundaries

Question: Does the project mark and protect server-only and client-only code?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,ts,tsx}"], "exclude": ["**/*.config.*"] },
  "variants": [
    { "name": "server-only-marker", "any": ["import\\s*['\"]server-only['\"]"] },
    { "name": "client-only-marker", "any": ["import\\s*['\"]client-only['\"]"] },
    { "name": "next-headers", "any": ["from\\s*['\"]next/headers['\"]"] },
    { "name": "node-builtin", "any": ["from\\s*['\"](node:)?(fs|path|child_process|crypto)['\"]", "require\\(['\"](node:)?(fs|path|child_process)['\"]\\)"] }
  ]
}
```

## Interpret

- Zero `server-only-marker` files with many `node-builtin` or `next-headers` files means nothing stops a client file from importing server code. That is a strong candidate rule.
- Node built-ins in a file that is also `use client` (see the client-boundaries report) is a real defect. Report it as a fact, not a rule.
