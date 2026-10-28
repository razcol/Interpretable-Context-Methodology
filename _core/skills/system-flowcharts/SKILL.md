---
name: system-flowcharts
description: "Plan and generate a detailed editable Excalidraw flowchart for an idea or an existing system. Use when the user wants a flowchart, process diagram, decision flow, or a picture of how a system works. Not for wireframes, freeform sketches, or sequence diagrams."
status: active (approved 2026-10-28, tested on the skill-factory pipeline and an order-fulfillment flow)
license: N/A (internal)
---

# System flowcharts

The agent decides what the chart says. A script decides where the shapes go and how arrows attach. The file is an editable `.excalidraw` document.

Excalidraw is the tool. It is MIT-licensed, opens on excalidraw.com and in the VS Code or Cursor extension, and the generator runs in Node without a browser. tldraw's SDK is licensed for development use only and needs a headless browser to build a `.tldr` file, so it is not the generator.

## Setup

Once per machine, from this skill folder:

```bash
npm install
```

Requires Node 22 or newer. The install builds a local bundle of `@excalidraw/excalidraw@0.18.1`. Do not upgrade those packages inside a charting task.

## Before drawing

Read `references/planning.md` and write a short planning note next to the output path. Then write a spec. The schema is `references/spec.md`. A worked example is `references/example-skill-factory.flow.json`.

Do not put coordinates in the spec. Do not draw the chart by hand as Excalidraw JSON.

## Generate

From this skill folder:

```bash
node scripts/build-flowchart.mjs path/to/spec.json --out path/to/name.excalidraw
```

When the user already has a Mermaid `flowchart`, or a spec run left overlapping frames:

```bash
node scripts/build-flowchart.mjs --mermaid path/to/flow.mmd --out path/to/name.excalidraw
```

The script also writes `name.svg` and `name.png` beside the `.excalidraw` file. Read the PNG. If a label sits off its arrow, a frame covers a node from another group, or two arrows cross in a way that hides the story, change the spec (shorter labels, fewer nodes, drop or split `groups`) and run the script again. Never patch `x`, `y`, or `points` in the output.

Stdout is one JSON object. `ok: true` means the file passed the binding and overlap checks.

| Exit | Meaning |
|------|---------|
| 0 | File written and checks passed |
| 1 | Bad arguments |
| 2 | Spec or Mermaid input failed validation |
| 3 | Layout or conversion failed |
| 4 | File was written, then failed the binding or overlap check |

## After drawing

Write a reading guide of a few sentences: where to start, what each group is for, and which path is the usual one. Point the user at the `.excalidraw` file. The PNG is a preview, not the deliverable.

## What the two inputs are for

| Input | Use it when |
|-------|-------------|
| Spec JSON | This is the default. Decisions, start/end, input/output, storage, and errors keep their shapes and colors. |
| Mermaid flowchart | The user already has Mermaid, or grouped phases lay out more clearly as `subgraph` blocks. Cylinders and parallelograms become colored rectangles. Subgraphs become rectangles, not Excalidraw frames. |

## Shape colors

| Kind | Looks like | Fill |
|------|------------|------|
| `start`, `end` | Green ellipse | `#b2f2bb` |
| `error` | Red ellipse | `#ffc9c9` |
| `process` | Blue rounded rectangle | `#a5d8ff` |
| `decision` | Yellow diamond | `#ffec99` |
| `io` | Orange rectangle | `#ffd8a8` |
| `storage` | Purple dashed rounded rectangle | `#d0bfff` |
| `subprocess` | Blue rectangle, thick stroke | `#d0ebff` |

Excalidraw has no cylinder or parallelogram. Storage and input/output use these rectangles on purpose.

## Rules the script already enforces

- One reading direction, `DOWN` (top to bottom) or `RIGHT`.
- Every decision is a question and has at least two labeled branches.
- No self-loops. Add a named step instead.
- At most 36 nodes. Split a larger system into more than one chart.
- Arrow endpoints stay bound to shapes, so a later drag in Excalidraw does not leave a floating arrow.
- The same spec produces the same file bytes.
