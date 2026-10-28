# Probe: env-access

Question: How do files read environment variables?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,mjs,ts,tsx}"], "exclude": ["**/*.config.*"] },
  "variants": [
    { "name": "public-env", "any": ["process\\.env\\.NEXT_PUBLIC_"] },
    { "name": "server-env", "any": ["process\\.env\\.(?!NEXT_PUBLIC_)[A-Z_]+"] },
    { "name": "validated-env", "any": ["@t3-oss/env-nextjs", "from\\s*['\"](@/|(\\.\\./)+|\\./)env(\\.m?js|\\.ts)?['\"]"] }
  ]
}
```

## Interpret

- Many files reading `process.env` directly means there is no single config module. The convention to enforce may be "read env in one place".
- A `validated-env` match means a typed env module exists. Then direct reads elsewhere are candidate violations.
- Never print values. This probe reads variable names only.
