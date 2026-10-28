# Probe: styling-approach

Question: Which styling approach do components use?

## Measure

```json measure
{
  "mode": "content",
  "candidates": { "include": ["**/*.{js,jsx,ts,tsx}"], "exclude": ["**/*.config.*"] },
  "variants": [
    { "name": "css-modules", "any": ["from\\s*['\"][^'\"]+\\.module\\.(css|scss|sass)['\"]", "require\\(['\"][^'\"]+\\.module\\.(css|scss|sass)['\"]\\)"] },
    { "name": "styled-components", "any": ["from\\s*['\"]styled-components['\"]"] },
    { "name": "emotion", "any": ["from\\s*['\"]@emotion/"] },
    { "name": "global-css-import", "any": ["^import\\s*['\"][^'\"]+\\.(css|scss|sass)['\"]"] },
    { "name": "tailwind-classes", "any": ["className\\s*=\\s*[{\"'`][^\\n]*\\b(flex|grid|items-center|justify-between|px-\\d+|py-\\d+|mt-\\d+|mb-\\d+|text-(xs|sm|base|lg|xl)|bg-[a-z]+-\\d{2,3})\\b"] },
    { "name": "inline-style", "any": ["style\\s*=\\s*\\{\\{"] },
    { "name": "styled-jsx", "any": ["<style\\s+jsx"] }
  ]
}
```

## Interpret

- The tailwind pattern is a heuristic on class names. Confirm with the dependency list in the recon profile before you call it Tailwind.
- Files often match several variants. Decide which one is the styling system and which are incidental, such as inline styles for dynamic values.
- `styled-components` and `emotion` need a client boundary. If they exist in an App Router project, say so.
