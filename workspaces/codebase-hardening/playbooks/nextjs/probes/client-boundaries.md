# Probe: client-boundaries

Question: Where do files declare `use client` or `use server`?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,ts,tsx}"], "exclude": ["**/*.config.*"] },
  "variants": [
    { "name": "use-client", "any": ["^\\s*['\"]use client['\"]"] },
    { "name": "use-server", "any": ["^\\s*['\"]use server['\"]"] }
  ]
}
```

## Interpret

- A directive counts only at the top of a file. The pattern also matches inline `use server` inside a function, which is a server action. Check one exemplar if the distinction matters.
- Compare the files list in evidence with the router-type report. `use client` in a Pages Router project has no effect.
- Look for client files that sit high in the tree, such as layouts, which pull everything below them to the client.
