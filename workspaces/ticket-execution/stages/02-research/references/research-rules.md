# Research rules

## Where to look

- Routes: `code/app/**/page.*`. Most content pages come from WordPress through `code/app/(pages)/[...pageUri]/page.js`; fixed pages live under `(dynamic-pages)/` and others.
- CMS sections: `code/app/components/Sections/<Name>/` (Server, Client, Styled, `.gql`). They load from the folder by name, so no page imports them (the table's "Notes" may name the loader).
- CMS page templates: `code/app/components/Templates/<Name>/`.
- Shared UI: `code/app/components/UIComponents/`, `Core/`, `Layout/`.
- Data: `.gql` fragments next to components and in `code/app/fragments/`, Prisma in `code/prisma/`, server actions in `code/app/actions/`.
- Live WordPress: what ACF has right now comes only from the wp-graphql commands in "Live WordPress" below. A `.gql` file is what the code selects, not what the schema has.
- Import aliases: `code/jsconfig.json` (`@/*` is `components/*`, `baseUrl` is `./app`).
- When a ticket image shows a page, find the page first, then the section inside it.

## Siblings

The siblings are the repos the "Siblings" line in `<data-root>/workspaces/ticket-execution/repos.md` "Notes" names: they share one structure, and a feature often exists in one before another. Read the sibling only when it already has the feature. Leave out of a cross-repo survey the repos that line says are built differently, unless you name them. No "Siblings" line: no sibling survey.

## Live WordPress

### Which lines

`wp: yes` when the line's answer depends on what WordPress has:
- it shows CMS-edited content through a field, group, options page, template or select;
- the change adds or changes a `.gql` selection;
- the line or a ticket comment asks for an editor action, or says a field is missing;
- a sibling reads a field the run's root does not select.

`wp: no` for layout, style, hard-coded copy, Prisma-only data, server actions, and behavior on data the root already selects and renders. Each mark gets one clause of reason. A `wp: no` line runs no command.

### How to run

Working directory is the folder that contains the SKILL.md named in this stage's Inputs (`<checkout>/_core/skills/wp-graphql`, in the ai-system checkout the run is in; the brief gives `<checkout>` as a real path):
`python3 scripts/wp_graphql.py <command> [<arg>] --repo <root>`, with `required_permissions: all` on the first call.

- `--repo` is the root from `intake.md`, or the sibling root cited under "sibling:". Never a stage 04 worktree.
- Run `status` once per repo before its first lookup. If it is not `ok: true`, or `authenticated` is false, run nothing else on that repo: each of its blocks is unconfirmed with that code (or `not authenticated`).
- Read `summary` first. Use `tree` only when the line needs nested names. Do not run a second command to restate `summary`.

| The line's claim | Command | Repo |
|---|---|---|
| A flexible section (`components/Sections/<Name>/`) | `section <Name>` | intake root |
| Any other type: options page, template, or a group such as `finishFields`, `engineFields`, `Template_*` | `type <Name>` | intake root |
| A name you cannot place as a section or a type | `patterns`, then `section` or `type` on the name it shows | intake root |
| The options of one select | `choices Type.field` | intake root |
| A fragment the change edits or relies on, outside `Sections/<Name>/<Name>.gql` | `check-fragment <file>` | the repo that owns the file |
| Every fragment in the repo (only when a line is about that) | `check-repo` | intake root |
| "The sibling has it" | the same `section` or `type` call | the sibling root and the intake root, one block each |
| "Missing", "not there", "add this field", "editors create" | `section` or `type` on the parent | intake root; the claim is allowed only when `ok: true` and the tree does not contain the name |

`diff-group` is not used in this stage.

### When a call fails

| Exit | Code | This stage does |
|---|---|---|
| 0 | `ok: true` | Record `present` and `absent` from `summary` or `tree` |
| 1 | `USAGE` | Fix the arguments once. If the name is the problem, run `patterns` and retry with the name it shows. Then: unconfirmed `USAGE` |
| 2 | `AUTH_FAILED` | If the call ran sandboxed, rerun once with `all`. Otherwise stop every call on that repo: its blocks are unconfirmed `AUTH_FAILED`. No new sign-in, no token, no env file |
| 3 | `HTTP_FAILED` or `SCHEMA` | Retry once with `--refresh` (and `all`). A second failure: unconfirmed with that code |
| 4 | `FILE_NOT_FOUND` | Fix the path once to a file that exists in that tree. Then: unconfirmed `FILE_NOT_FOUND` |
| 5 | `CHOICES_UNAVAILABLE` | Stop for that field: unconfirmed `CHOICES_UNAVAILABLE`. Do not look in another repo, REST or the database |
| 99 | `INTERNAL` | Record the command and the code, stop calls for that line: unconfirmed `INTERNAL` |

`--refresh` is only for that one retry.

### Reading the result

- A `.gql` file is what the code selects, not what the schema has. Never copy a sibling's fragment onto the run's root as a schema fact.
- A name in `summary` or `tree` is `present` even when the fragment does not select it (`fragment.notSelected`). That is a code gap. Record it under `data:` or "Not found in code". It is not `absent`, and it is not a reason to say editors must create it.
- A null `acfType` does not mean "no options". `choices` settles it.
- Deprecated media fields (`fragment.deprecatedSelected`) are not missing.
- `image { ...MediaItem }` matches a connection edge only when the shared fragment's whole body is `node { ... }`, as with the repos' `MediaItem` and `MediaItemNew`. The body is compared on the edge. A body that is not `node { ... }`, a second `node` level (`node { ...MediaItem }`), and a gallery field (`AcfMediaItemConnection`, which has `nodes`, not `node`) are real mismatches. Inline fragments (`... on Model { }`) are compared on their own type.
- `section` on a name that is not a flexible layout is still `ok: true`, and `summary` says so. Run `type` on it.
- A null `flexible` with `flexibleField` set means the `fields` group exists.
- A field label `clone of X` is an ACF clone. `similarLayout` is not a clone.
- `fragment.compared: false` is not a match. That comparison alone is unconfirmed. Names already under `present` or `absent` on an `ok: true` `type` or `section` block for the same repo stay confirmed. Do not put that block under "Unconfirmed live", and do not mark the Live audit `unconfirmed` for it.
- `check-repo` `notCompared` is not "all match".

### Not settled by the skill

The skill never confirms these. Write them under `not settled`, never as schema facts:
- admin titles and labels;
- whether editors filled values, and page content;
- ACF location rules (where `summary` says a GraphQL type is attached is a schema fact; the ACF location rule is not);
- required, Seamless, min and max;
- a choice list after `CHOICES_UNAVAILABLE`.

## What not to do

- No edits, no branch, no install, no dev server. Stage 05 runs the app.
- Do not pull in nearby improvements. Note them under "Out of scope" if they matter.
- Do not read workspace records of other keys.
- Do not open the wp-graphql script, the project store or `~/.cache/wp-graphql/`. Do not request a token, pass `--show`, or write a GraphQL query, introspection or sign-in. Record `endpointHost` only: never a token, store value, cache content, endpoint path or query text.

## research.md

```markdown
# <KEY> research

- root: <root>, branch <current branch>, tree <clean or dirty: N files>
- origin/<base>: <short hash>  (<base> from intake.md)

## Per acceptance line
1. <line from intake.md>
   - lives in: `<path>` (<what it does there>)
   - data: `<fragment, field, action or none>` (what the code selects)
   - wp: <yes | no> (<one clause: why>)
   - live (<repo folder name>): `<command> <arg>`, permissions all, ok <true | false CODE>[, retried with --refresh], host <endpointHost>
     - present: <names the line needs that summary or tree lists, nested as in the tree>
     - absent: <names the line needs that this ok:true result does not list, or none>
     - not settled: <items from "Not settled by the skill" the line needs, or none>
   - sibling: `<repo>/<path>` does it by <one sentence>, or none

## Earlier decisions
<Commits that matter: hash, subject, why it matters. Or none.>

## Not found in code
<Acceptance lines, or the part of one, with no code yet. Or none. This section says nothing about WordPress.>

## Unconfirmed live
<Each wp: yes block that is not ok: true: line number, repo, command, code, and the names that stay unknown. Or none.>

## Out of scope
<Things seen that the ticket does not ask for. Or none.>
```

A `wp: no` line has no `live` lines. When a block has `ok: false`, its `present` and `absent` lines read `unconfirmed`. A line can have several `live` lines, one per repo and command. A name the fragment does not select, while an `ok: true` block lists it under `present`, is a code gap in that line's `data:` bullet or under "Not found in code". Do not repeat the live result in "Not found in code".
