# Enforcement Ladder

Pick the strongest mechanism that is cheap enough. A lower number is stronger. Only level 5 is not enforced.

| Level | Mechanism | What it gives | Cost |
|-------|-----------|---------------|------|
| 1 | By construction | The wrong code cannot be written or does not compile | Highest to set up |
| 2 | Structural rule | A tool rejects the wrong shape (imports, syntax, dependencies) | Low to medium |
| 3 | Layout test | A test asserts the shape of the repository | Low |
| 4 | Custom rule or script | A project-specific check nothing off the shelf covers | Medium |
| 5 | Documentation only | The agent guide states it. Humans review it. | None |

## Level 1: By Construction

- Generators that create files with the right structure, so an agent runs one command instead of inventing a layout.
- Compiler strictness: strict TypeScript flags, typed routes, typed environment access.
- Marker packages that fail the build on a boundary violation (for example `server-only`).
- Wrapper modules that are the only place a risky call lives, with a rule that bans the raw call elsewhere.

## Level 2: Structural Rules

- Import bans and allow-lists (ESLint `no-restricted-imports`, boundaries plugins, dependency-cruiser).
- Syntax bans by selector (ESLint `no-restricted-syntax`, ast-grep rules).
- Dependency allow-lists and deny-lists checked against the manifest file.
- Style tooling (stylelint) for stylesheet rules.

## Level 3: Layout Tests

Small scripts that assert the repository shape: every component folder has its index, test, and style file; no file sits in a forbidden folder; names match the pattern.

## Level 4: Custom Rules

Use only when levels 1 to 3 cannot express the convention. A custom rule needs a should-fail fixture, a should-pass fixture, and a test that the fixture really fails.

## Level 5: Documentation Only

Allowed, but it must be labeled. A convention stays at level 5 when no mechanical check can decide it (naming quality, abstraction choices). It appears in the agent guide under "Review manually". It is never listed as enforced.

## Choosing

1. Can the wrong code be made impossible? Use level 1.
2. Can an existing tool express it in one setting? Use level 2.
3. Is it about where files live or what they are called? Use level 3.
4. Otherwise write a level 4 check, and keep it small.
5. If none apply, record level 5 and say why.

## Every Rule Needs a Message

The text an agent sees when a rule fires is its only teacher. It names the fix: "Use `<Stack>` from `@ui/layout`, not a raw flex container." A message that only says "not allowed" wastes the agent's next attempt.
