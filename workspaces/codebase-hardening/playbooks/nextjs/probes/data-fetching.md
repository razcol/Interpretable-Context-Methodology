# Probe: data-fetching

Question: How does the project fetch and mutate data?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,ts,tsx}"], "exclude": ["**/*.config.*"] },
  "variants": [
    { "name": "fetch-call", "any": ["\\bfetch\\("] },
    { "name": "axios", "any": ["from\\s*['\"]axios['\"]"] },
    { "name": "swr", "any": ["from\\s*['\"]swr"] },
    { "name": "react-query", "any": ["from\\s*['\"]@tanstack/react-query"] },
    { "name": "server-action", "any": ["['\"]use server['\"]"] },
    { "name": "pages-data-functions", "any": ["export\\s+(async\\s+)?function\\s+(getServerSideProps|getStaticProps|getInitialProps)", "export\\s+const\\s+(getServerSideProps|getStaticProps)"] },
    { "name": "prisma-client", "any": ["from\\s*['\"]@prisma/client['\"]", "prismaClient"] }
  ]
}
```

## Interpret

- Decide where data access is allowed to live. A database client imported in many files is a boundary problem; in one file it is a module.
- Several client libraries side by side (axios and fetch) usually means a convention can be enforced for new code only.
- Do not judge caching settings here. This probe only covers which mechanism is used.
