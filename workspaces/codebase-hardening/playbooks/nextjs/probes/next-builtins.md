# Probe: next-builtins

Question: Do files use the Next.js image and link components, or raw HTML elements?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,ts,tsx}"], "exclude": ["**/*.config.*"] },
  "variants": [
    { "name": "raw-img", "any": ["<img\\s"] },
    { "name": "next-image", "any": ["from\\s*['\"]next/image['\"]"] },
    { "name": "raw-anchor-internal", "any": ["<a\\s[^>]*href=[\"']/"] },
    { "name": "next-link", "any": ["from\\s*['\"]next/link['\"]"] }
  ]
}
```

## Interpret

- `raw-img` beside `next-image` is a candidate rule for new code. A few raw `<img>` tags for SVG or email templates can be legitimate; list them as exceptions.
- Internal raw anchors skip client-side navigation. External links (`https://`) are not counted here.
