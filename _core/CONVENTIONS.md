# MWP Conventions

The rules for building and maintaining MWP workspaces. This is the canonical source. Every workspace follows these patterns.

---

## Five-Layer Routing Architecture

Agents read down the layers. They stop as soon as they have what they need.

```
Layer 0: CLAUDE.md           -> "Where am I?"            (always loaded, ~800 tokens)
Layer 1: CONTEXT.md          -> "Where do I go?"          (read on entry, ~300 tokens)
Layer 2: Stage CONTEXT.md    -> "What do I do?"            (read per-task, ~200-500 tokens)
Layer 3: Reference material  -> "What rules apply?"        (loaded selectively, varies)
Layer 4: Working artifacts   -> "What am I working with?"  (loaded selectively, varies)
```

**Layer 0 -- CLAUDE.md** is auto-loaded by Claude Code into every conversation. It contains the folder map, naming conventions, and a routing table that points to workspace-level files. One per workspace.

**Layer 1 -- Top-level CONTEXT.md** is the first thing an agent reads when entering the workspace. It contains a task routing table that maps task types to specific stage folders. One per workspace.

**Layer 2 -- Stage CONTEXT.md files** live inside each stage folder. They contain the scope definition, what-to-load tables, and step-by-step process. One per stage. Layer 2 is the control point of the system -- its Inputs table determines exactly which files from Layers 3 and 4 the agent loads.

**Layer 3 -- Reference material** is the persistent context: design systems, voice rules, build conventions, style guides, domain knowledge bundled as skill files. These files are configured once during workspace setup and remain stable across every run of the pipeline. They live in `references/` folders within stages, in workspace-level configuration folders (like `brand-vault/` or `design-system/`), in `shared/`, and in `skills/`. Larger reference collections can include their own CONTEXT.md routing files to help agents navigate within the collection.

**Layer 4 -- Working artifacts** are the per-run context: previous stage outputs, user-provided source material, anything specific to this particular run. These files are produced and consumed during execution and change every time the pipeline runs. They live in the run folders in the data root (Pattern 2), never in the repo.

The distinction between Layers 3 and 4 matters because they require different things from the model. Layer 3 material needs to be internalized as constraints and patterns -- write like this, use these colors, follow these conventions. Layer 4 material needs to be processed as input -- transform this research into a script, convert this script into a specification. Layer 3 is the factory. Layer 4 is the product.

A rendering agent might only need Layers 0 through 2. A script-writing agent reads down to Layer 4 to access both voice rules (Layer 3) and source material (Layer 4). No agent reads everything.

Every token of irrelevant context is a token of diluted attention. Workspace CLAUDE.md files should explicitly map each task to its minimal required files. Loading more context does not make output better. It makes it worse.

---

## Pattern 1: Stage Contracts

Every stage CONTEXT.md follows the same three-section shape:

```markdown
## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| ... | ... | ... | ... |

## Process

1. Step one
2. Step two
3. Step three

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| ... | ... | ... |
```

This is the contract. It is simple enough that a non-technical user can read it and understand what is happening. It is structured enough that an agent can follow it reliably. Every stage follows this exact shape. No exceptions.

---

## Pattern 2: Stage Handoffs via Run Folders

Stage outputs are the user's data, so they live in the data root (see Data root), never in the repo. Each run has a key, and each stage writes its artifact into the run's folder for that stage. The next stage reads from there.

The convention:
- `<runs>` is `<data-root>/workspaces/<workspace>/runs`. The workspace CLAUDE.md defines it and says what a run's key is (a Jira key, a Figma node id, a skill slug, a date).
- Stage N produces: `<runs>/<KEY>/0N-name/artifact-name.md` (the subfolder is named after the stage folder)
- Stage N+1's CONTEXT.md says: "Read `<runs>/<KEY>/0N-name/artifact-name.md` as your input"
- Stage folders in the repo hold definitions only (`CONTEXT.md`, `references/`). They have no `output/` folder, and no CONTEXT.md names a repo-relative output path.
- Work that belongs to a run but to no stage (for example WP content for a Figma section) goes into the run folder too, in a named subfolder.

This is the handoff. A human can open the output file, edit it, and the next stage picks up the edited version. No state management. No orchestration layer. Just files in predictable places.

File naming in run folders: `[topic-slug]-[stage-artifact].md`
- Example: `hello-world-script.md`, `hello-world-spec.md`

---

## Pattern 3: One-Way Cross-References

Every folder points outward to what it needs. No folder points back.

If Stage 03 references Stage 02's component registry, Stage 02 does NOT reference anything in Stage 03. If the brand-vault is referenced by multiple stages, the brand-vault does NOT reference any stage.

This prevents reference growth from going N-squared as the system scales. When adding a new reference, check: "Does the target file already reference my folder?" If yes, restructure.

---

## Pattern 4: Selective Section Routing

CONTEXT.md Inputs tables do not just say "read voice-rules.md." They say "read the Voice Rules section of voice-rules.md."

This keeps token cost low. A 150-line file might have only 60 lines of actionable rules for a specific stage. The other 90 lines of strategic rationale stay unloaded.

Format in CONTEXT.md Inputs tables:

```
| File | Section to Load | Why |
|------|----------------|-----|
| voice-rules.md | "Voice Rules" through "What the Voice Is NOT" | Tone guidance |
| identity.md | "One-Sentence Brand" and "Audience" sections | Audience context |
```

When a full file is needed, write "Full file" in the Section/Scope column.

---

## Pattern 5: Canonical Sources

Every piece of information has ONE home. Other files point there. They do not duplicate it.

If you need to update a rule, you update it in one place. Every other file has a pointer. If you find the same information in two files, one of them should be replaced with a reference to the other.

Smell test: search the repo for a specific phrase. If it appears in more than one file and both instances are meant to be authoritative, one needs to become a pointer.

---

## Pattern 6: CONTEXT.md = Routing, Not Content

CONTEXT.md files answer three questions:
1. What is this folder?
2. What do I load?
3. What is the process?

They never contain the actual reference material. No definitions. No rules. No extended examples. No voice guidelines. This keeps them small (25-80 lines) and prevents them from going stale when the content they would otherwise duplicate gets updated.

If you find yourself writing more than a one-sentence description in a CONTEXT.md, that content belongs in a separate file that the CONTEXT.md points to.

---

## Pattern 7: Tool Prerequisites

Some stages require external tools (Node.js, LibreOffice, ffmpeg, etc.). Setup guides for these tools live in the `references/` folder of the stage that uses them (e.g., `stages/03-build/references/remotion-setup.md`).

Setup guides are written for someone who has never installed the tool: what it is (one sentence), installation steps, how to verify it works, and how the workspace uses it.

If a tool is needed by multiple stages, it can live in `shared/` instead. The `setup` onboarding process should check which tools are needed based on the user's answers and point them to the right setup guide.

Note: When a workspace bundles skills (Pattern 9), many tools that would have needed separate prerequisites (scripts, libraries, utilities) come bundled inside the skill folder. Only tools that require system-level installation (Node.js, Python, LibreOffice) still need setup guides.

---

## Data root

The repo holds definitions only: rules, workflows, skills, tools and templates. Everything a user produces or keeps while using it (repo tables, login steps, logs, session briefs, stage outputs, run records) is that user's data. It lives in the **data root**, a local git repo of its own, outside the repo tree. A `.gitignore` entry in the repo is a backstop only, never the place where data is kept.

**One definition.** The data root is the first of:

1. the path in `.data-root` at the top of the ai-system checkout (one line, starting with `~` or `/`; git-ignored, never committed)
2. the `AI_SYSTEM_HOME` environment variable
3. `~/.config/ai-system`

Tools never type the path. They ask the helper, `_core/data-root/data_root.py` (Python 3 standard library only):

| Command | What it does |
|---|---|
| `resolve` | Prints the data checkout this ai-system checkout uses: the main checkout uses the data root, a worktree on branch X uses data worktree X. Stops when there is none. |
| `checkout` | Prints the top folder of the ai-system checkout the helper is in: a main checkout, another clone, or a maintenance worktree each print their own. |
| `init` | Creates the data root when it is missing and seeds what is missing. Never overwrites. `setup` runs it. |
| `commit -m MSG [PATH...]` | Commits in the data checkout. Stages named paths (all changes when none are given), refuses secret-looking files, and holds a short lock so commits into one checkout never overlap. |
| `add <branch> [--from REF]` | Maintenance only: an ai-system worktree (default `<checkout>.worktrees/<branch>` next to the main checkout, started at `REF` or the main checkout's HEAD) and a data worktree at `<data root>/.worktrees/<branch>`, on the same branch name. |
| `merge <branch>` | Commits the data worktree, merges data into the main data checkout, then merges code. Stops before the code merge if the data merge conflicts. |
| `remove <branch>` | Removes both worktrees and both branches after a confirmation. Uncommitted or unmerged work is dropped only with `--discard`. |

From a shell: `"$(python3 _core/data-root/data_root.py resolve)"`.

**In docs** a path inside the data root is written `<data-root>/<path>`, for example `<data-root>/workspaces/ticket-execution/repos.md` or `<data-root>/log/browser-cdp/LOG.md`. `<data-root>` is the folder `resolve` prints for the checkout you are working in. Resolve it once, then use the real path in commands and briefs. Never type `~/.config/ai-system` or a `/home/<user>/` path in its place, and never write a log, brief or table into the repo instead (a skill never keeps its log in its own folder).

**Tool paths in docs** are relative to the ai-system checkout the run is in, never to one machine's folder. A doc that needs an absolute tool path writes `<checkout>/<path>` (for example `<checkout>/_core/skills/browser-cdp`), where `<checkout>` is the folder `data_root.py checkout` prints. Resolve it once per run, with `<data-root>`, and copy the real path into commands and briefs. A run from a main checkout, another clone or a maintenance worktree then uses its own tools and its own data checkout. Never type `/home/<user>/...` for a tool.

**Layout** (version 1, named in the data root's `LAYOUT` file):

| Folder | Holds |
|---|---|
| `workspaces/<ws>/` | One workspace's settings (repo tables, login steps) |
| `workspaces/<ws>/runs/<KEY>/` | Run records and produced artifacts, per run key: one subfolder per stage (`<KEY>/0N-name/`) |
| `workspaces/<ws>/flowchart/` | A generated diagram of the workspace |
| `log/<skill>/LOG.md` | One append-only log per skill |
| `log/briefs/` | Session briefs, handoffs and debriefs |
| `archive/` | Kept history (`archive/<ws>/` per workspace) |
| `.worktrees/<branch>/` | Paired data worktrees (ignored) |
| `workspaces/<ws>/runs/<KEY>/claim.lock`, `claims/` | Run claims (ignored, never committed; see Run claims) |

A layout change raises the `LAYOUT` version and ships with a migration step that runs on merge.

**Data repo rules** (seeded from `_core/data-root/seed/`): `.gitignore` keeps env and secret files, caches and claim files (`*.lock`) out; `.gitattributes` sets `LOG.md` and `log/briefs/` to `merge=union`, so two branches that both append never conflict.

**Seeding.** A tracked `workspaces/<ws>/targets/<path>.example.<ext>` seeds `workspaces/<ws>/<path>.<ext>` in the data root, once. Example files show every column with `<...>` placeholders, never a user's data.

**Project practices are rows.** How a target project works (root, branch and commit patterns, base branch, PR target and PR link, main tree or worktree and where, lint command, test route, test logins, form submits, and any rule that holds for that project only) is that project's row in its workspace's repo table in the data root. The repo keeps only the generic rule for reading a row (for example `workspaces/ticket-execution/shared/repo-rows.md`), so adding or changing a project never needs an edit in the repo. ai-system's own maintenance worktrees and their paired data worktrees ("Two modes" below) are ai-system's own mechanism, not a project row. A ticket on ai-system itself is the one row whose worktree is made with `add` (its row's note says so), so that branch gets its paired data worktree; a run on any other repo never creates an ai-system worktree.

**Run folders** (`workspaces/<ws>/runs/<KEY>/<stage>/`) hold every stage output and run record (Pattern 2). Tools that write a record resolve the data root themselves (for example `workspaces/ticket-execution/tools/write_record.py`). A generated diagram of a workspace goes to `workspaces/<ws>/flowchart/`. Kept history that belongs to no run goes to `archive/<ws>/`. A session's throwaway files go to its own temp folder, never into the repo; anything worth keeping goes to the data root.

**Large outputs** (screenshots, exports) are committed to the data repo like everything else, so discarding a worktree never loses them. Env and secret files are never committed in either repo.

**Run claims.** Runs on different keys run at the same time. Instead of one lock file per workspace, a run claims only what runs really share, with `_core/data-root/run_claim.py` (every command prints one JSON object; exit 3 names the live run that holds what was asked for):

| Command | What it does |
|---|---|
| `claim --ws <ws> --key <KEY>` | Before a run's first stage. Writes `workspaces/<ws>/runs/<KEY>/claim.lock` in the data checkout `resolve` prints: start time, the ai-system checkout, the PID of the agent session that runs it, and a token. A live claim on the key stops the second run and names the first. A stale claim (its process gone or replaced, its checkout gone, or untouched for 2 hours) is replaced and reported, so the next run continues from the records. `--takeover` replaces a live-looking claim only when the user says that run is not running. |
| `target --path <work tree> --root <root> --branch <b>` | Claims the target-repo work tree and branch a run edits. Another live run on the same work tree or branch gets exit 3. Whether a run uses a worktree comes from the repo's row. |
| `port --kind dev\|cdp` | The run's own dev-server or browser (CDP) port: free, not claimed by a live run, and the same on every call of that run. Each run also starts its own browser profile, so sign-ins and screenshots never mix. |
| `commit [--stage S]` | Commits only `workspaces/<ws>/runs/<KEY>/` through `data_root.py commit` (serialized, named paths only). Workflows run it after each stage's record. |
| `release --token T` | When the run stops: drops its claims, then commits its run folder. |
| `list [--ws <ws>]` | Every claim, `live` or `stale`. `status` shows the live ones. |

Port and work-tree claims are machine-wide, so they live in the main data checkout's `claims/` folder, also for test runs from a maintenance worktree; key claims live in the run's own data checkout. Claim files end in `.lock`, which the data repo ignores. Stages within one run still run in order. Log writes stay single small appends.

**Two modes.** Normal work runs on the main ai-system checkout and writes to the main data checkout; a run never gets its own ai-system worktree. Changing ai-system itself happens in a worktree from `add`, whose test runs write to its paired data worktree; finish with `merge` (data first, then code) or `remove --discard`.

---

## Trigger Keywords

Every workspace recognizes these triggers:

**`setup`** -- Starts the onboarding questionnaire. The agent first runs `python3 _core/data-root/data_root.py init` from the ai-system checkout, which creates the data root when it is missing (see Data root) and changes nothing when it is complete. Then it reads `setup/questionnaire.md`, asks the questions conversationally, collects answers, replaces placeholders across the workspace, and verifies no placeholders remain.

**`status`** -- Shows pipeline completion. The agent lists each run key under `<runs>/` and renders an ASCII pipeline diagram per key:

```
Pipeline Status: [workspace-name]

  [01-stage-name]  ------>  [02-stage-name]  ------>  [03-stage-name]
     COMPLETE                  PENDING                  PENDING
  (artifact.md)              (empty)                  (empty)
```

For each stage: if `<runs>/<KEY>/<stage>/` contains files, the stage is COMPLETE and the filenames are listed. If it is missing or empty, the stage is PENDING.

Then it lists the runs that hold a claim now (`python3 _core/data-root/run_claim.py list --ws <ws>`): each live run's key, start time and ports, and each stale claim as stopped without release.

Workspaces can define additional trigger keywords in their own CLAUDE.md.

---

## Naming Conventions

- Folders and files: `lowercase-with-hyphens`
- Stage folders: zero-padded numbers prefix: `01-`, `02-`, `03-`
- Placeholders: `{{SCREAMING_SNAKE_CASE}}`
- Output artifacts: `[topic-slug]-[artifact-type].md`
- No spaces in file or folder names

---

## Pattern 8: Questionnaire Design

Onboarding questionnaires configure the production system, not a specific run. They follow these rules:

1. **Flat structure.** No category groupings. Just a numbered list of questions.
2. **All at once.** Every question appears in one pass. The user should be able to answer everything in a single message.
3. **System-level only.** Questions configure things that stay the same across runs: identity, brand, design, tool preferences, default workflow. Per-run details (project name, topic, audience, scope) are collected conversationally at the start of each pipeline run by the entry stage.
4. **Derive, do not ask.** If a field can be inferred from another answer, the agent fills it in. List derived fields under the question they depend on. Do not add a separate question.
5. **Sensible defaults.** Every question should have a default or example so the user can skip what they do not care about.
6. **Ask once, never again.** After setup, the user should never see these questions again. The answers are baked into the workspace files permanently.

The questionnaire template at `_core/templates/questionnaire-template.md` encodes these rules.

---

## Pattern 9: Bundled Skills

Workspaces can bundle Claude Code skills directly into a `skills/` folder. This gives agents domain-specific knowledge (APIs, best practices, code examples) without requiring the user to have the skills installed globally.

```
workspace/
├── skills/
│   ├── [skill-name]/          (copied from ~/.claude/skills/ or cloned from GitHub)
│   │   ├── SKILL.md           (skill entry point)
│   │   ├── rules/             (detailed rule files, if any)
│   │   └── scripts/           (utility scripts, if any)
│   └── [another-skill]/
│       └── SKILL.md
```

**Discovery:** During workspace building (Stage 01), the builder identifies relevant skills by:
1. Scanning `~/.claude/skills/` and `~/.agents/skills/` for locally installed skills
2. Searching GitHub for skill repos matching the workspace domain (e.g., "remotion skill", "pptx skill")
3. Presenting candidates to the user for selection

**Bundling:** Selected skills are copied (local) or cloned (GitHub) into the workspace's `skills/` folder during scaffolding (Stage 03). This makes the workspace self-contained.

**Referencing:** Stage CONTEXT.md files reference skills in their Inputs table:

```
| Skill | `../../skills/[name]/SKILL.md` | Index, then load rules as needed | [What it provides] |
```

Skills replace custom reference docs when an official skill covers the same ground. Keep workspace-specific files (design systems, brand config, build conventions) alongside skills, not inside them.

**When NOT to bundle:** Do not bundle skills that are purely about Claude Code itself (e.g., skill-creator, mcp-builder). Only bundle skills that provide domain knowledge the workspace's agents need at runtime.

### Shared Skills (Core)

A skill used by more than one workspace does not get copied into each workspace's `skills/` folder. It lives once in `_core/skills/` and every workspace that needs it references it by pointer.

```
_core/
├── CONVENTIONS.md
├── placeholder-syntax.md
├── templates/
└── skills/
    └── [skill-name]/
        ├── SKILL.md
        ├── rules/
        └── scripts/
```

This is Pattern 5 (Canonical Sources) applied to skills: one home, update once, every workspace picks up the change.

**Referencing:** Stage CONTEXT.md files point into `_core/skills/` the same way they reference a bundled skill, just with a longer relative path:

```
| Skill | `../../../_core/skills/[name]/SKILL.md` | Index, then load rules as needed | [What it provides] |
```

This does not violate Pattern 3 (One-Way Cross-References). Workspaces may reference `_core/`, since `_core/` never references a workspace. Workspaces must still not reference each other's `skills/` folders directly.

**Bundled vs. shared -- which to use:**

| | Bundled (`workspace/skills/`) | Shared (`_core/skills/`) |
|---|---|---|
| Used by | One workspace | Two or more workspaces |
| Copy | Duplicated per workspace | One canonical copy |
| Updates | Drift independently, update per workspace | Update once, applies everywhere |
| Self-contained | Yes | No, workspace depends on `_core/` |

Default to bundling when a skill is specific to one workspace's domain. Move a skill to `_core/skills/` as soon as a second workspace needs the same one.

---

## Pattern 10: Specs Are Contracts

Specification stages define WHAT the output should achieve and WHEN things happen. They do not prescribe HOW to implement. The build stage has creative freedom within the quality floor defined by the design system.

A spec contains:
- **Beat map** with approximate durations, narration, and mood
- **Visual philosophy** describing what a muted viewer should understand
- **Key moments** that MUST land, and why each matters
- **Audio sync points** mapping narration words to visual events
- **Color flow** with per-scene dominant color and mood

A spec does NOT contain: frame numbers, component names, pixel positions, spring configs, or prop definitions. These are implementation decisions that belong to the build stage.

---

## Pattern 11: Checkpoints

Creative stages should include at least one checkpoint where the agent pauses and the human steers. The agent completes a full unit of work, presents options or a draft, and the human redirects before the next unit begins. Checkpoints go between process steps, not within them.

Not every stage needs checkpoints. Linear stages (extract, render, validate) often run straight through. Creative stages (writing, design, ideation) benefit from at least one.

The Checkpoints section in a stage CONTEXT.md is a table:

```
| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| [step #] | [what to show] | [what to choose] |
```

---

## Pattern 12: Stage Audits

Creative and build stages should include an Audit section: a checklist the agent runs after completing the process but before writing its output. Audits catch quality issues before they propagate downstream. Each check should be specific enough that pass/fail is unambiguous.

Not every stage needs an audit. Data extraction or file conversion stages may not benefit. Creative and build stages almost always do.

The Audit section in a stage CONTEXT.md is a table:

```
| Check | Pass Condition |
|-------|---------------|
| [Check name] | [What "passing" looks like] |
```

If any check fails, the agent revises before saving its output.

---

## Pattern 13: Value Validation

Content-producing stages should define what types of value their output can deliver. Before the main creative work begins (ideally at a checkpoint), the agent and human should agree on which value types this specific piece will hit. This prevents "interesting but doesn't DO anything" output.

Value types are workspace-specific. A content workspace might use NOVEL, USABLE, QUESTION-GENERATING, INTERESTING. A course workspace might use TEACHES, PRACTICES, CHALLENGES. The framework is defined once in a reference file and used at every checkpoint.

---

## Pattern 14: Docs Over Outputs

Reference docs (design system, build conventions, skill rules) are the authoritative source for how to build. Previous stage outputs in run folders are artifacts, not templates. Agents should not read other outputs to learn patterns.

This prevents copying from older, lower-quality work and ensures docs remain the single source of truth for quality standards. Early outputs are the worst outputs. If future agents learn from them, quality never improves.

---

## Pattern 15: Shared Constants

Workspaces that produce code should define a constants pattern. Configurable values (colors, fonts, timing, layout) live in shared files that all build outputs import from. The questionnaire populates these files once during onboarding. Change a value once, it updates everywhere.

This is Pattern 5 (Canonical Sources) applied to code values. Without shared constants, the same hex code or font name is hardcoded in every output file. Changing the brand color means a find-and-replace across every file ever built.

For non-code workspaces (content writing, course design), this pattern does not apply. Shared values live in reference docs instead.

---

## Quality Guardrails

- CONTEXT.md files: under 80 lines
- Reference files: under 200 lines (if longer, split into multiple files)
- Use plain English. Avoid jargon. If a term needs explaining, it is too specialized.
- No em dashes anywhere in the repo
- Every folder that should persist but starts empty gets a `.gitkeep` file
- Every markdown file should be readable by someone who understands markdown and git basics but does not have a deep engineering background
