# Probe: router-type

Question: Does the project use the App Router, the Pages Router, or both?

## Measure

```json measure
{
  "mode": "path",
  "candidates": { "include": ["**/*.{js,jsx,mjs,ts,tsx}"], "exclude": ["**/*.config.*"] },
  "variants": [
    { "name": "app-router", "any": ["(^|/)(src/)?app/(.*/)?(page|layout|route|loading|error|not-found|template|default)\\.(js|jsx|ts|tsx)$"] },
    { "name": "pages-router", "any": ["(^|/)(src/)?pages/(.*/)?[^/]+\\.(js|jsx|ts|tsx)$"] },
    { "name": "middleware", "any": ["(^|/)(src/)?middleware\\.(js|ts)$"] }
  ]
}
```

## Interpret

- Both routers present usually means a migration. Use the trend table to see which one new routes go into.
- Many files are `none` because most source files are not routes. Ignore the `none` row.
- A `pages/api` folder counts as the Pages Router. Note it if API routes live there while pages live in `app/`.
