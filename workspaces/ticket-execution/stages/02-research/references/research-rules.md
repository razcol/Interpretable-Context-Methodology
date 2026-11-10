# Research rules

## Where to look

- Routes: `code/app/**/page.*`. Most content pages come from WordPress through `code/app/(pages)/[...pageUri]/page.js`; fixed pages live under `(dynamic-pages)/` and others.
- CMS sections: `code/app/components/Sections/<Name>/` (Server, Client, Styled, `.gql`). The `@colmobil/next` package loads them from the folder, so no page imports them.
- CMS page templates: `code/app/components/Templates/<Name>/`.
- Shared UI: `code/app/components/UIComponents/`, `Core/`, `Layout/`.
- Data: `.gql` fragments next to components and in `code/app/fragments/`, Prisma in `code/prisma/`, server actions in `code/app/actions/`.
- Import aliases: `code/jsconfig.json` (`@/*` is `components/*`, `baseUrl` is `./app`).
- When a ticket image shows a page, find the page first, then the section inside it.

## Siblings

The Colmobil brand sites share one structure, and a feature often exists in one before another: ora-next, jaecoo-next, omoda-next, smart-next, colmobilnext, hyundai. Read the sibling only when it already has the feature. Leave luxury-trade and self-service out of a cross-brand survey unless you name them; they are built differently.

## What not to do

- No edits, no branch, no install, no dev server. Stage 05 runs the app.
- Do not pull in nearby improvements. Note them under "Out of scope" if they matter.
- Do not read workspace records of other keys.

## research.md

```markdown
# <KEY> research

- root: <root>, branch <current branch>, tree <clean or dirty: N files>
- origin/dev: <short hash>

## Per acceptance line
1. <line from intake.md>
   - lives in: `<path>` (<what it does there>)
   - data: `<fragment, field, action or none>`
   - sibling: `<repo>/<path>` does it by <one sentence>, or none

## Earlier decisions
<Commits that matter: hash, subject, why it matters. Or none.>

## Not found
<Acceptance lines with no code yet. Or none.>

## Out of scope
<Things seen that the ticket does not ask for. Or none.>
```
