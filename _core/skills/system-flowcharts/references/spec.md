# Flowchart spec

A spec is JSON. The script lays it out with elkjs and writes Excalidraw elements. See `example-skill-factory.flow.json` and `example-order.flow.json`.

```json
{
  "title": "Short name",
  "direction": "DOWN",
  "nodes": [
    { "id": "start", "label": "Order arrives", "kind": "start" },
    { "id": "stock", "label": "In stock?", "kind": "decision" }
  ],
  "edges": [
    { "from": "start", "to": "stock" },
    { "from": "stock", "to": "pack", "label": "Yes" }
  ],
  "groups": [
    { "id": "scope", "label": "Scope", "nodeIds": ["start", "stock"] }
  ]
}
```

## Fields

| Field | Required | Values |
|-------|----------|--------|
| `direction` | no | `DOWN` or `TB`, `RIGHT` or `LR`. Default `DOWN`. |
| `nodes[].id` | yes | Starts with a letter. Letters, digits, `_`, `-`. At most 41 characters. Unique. |
| `nodes[].label` | yes | Plain text. The script wraps long lines. |
| `nodes[].kind` | yes | `start`, `end`, `error`, `process`, `decision`, `io`, `storage`, `subprocess`. |
| `nodes[].tone` | no | `error` on an `end` node draws it as the red error ellipse. |
| `edges[].from`, `edges[].to` | yes | Node ids. Must differ. |
| `edges[].label` | required on edges that leave a decision | Short branch name. |
| `groups` | no | Each group needs an id, a label, and one or more `nodeIds`. A node belongs to at most one group. Group ids must not match node ids. |

`groups` become Excalidraw frames around those nodes after layout. If a later phase sits inside an earlier frame, remove the groups and run again, or switch that chart to Mermaid subgraphs.

## Mermaid

`flowchart TD` or `flowchart LR` only. Useful shapes:

| Write | Meaning |
|-------|---------|
| `start([Label])` | Start or end ellipse |
| `step[Label]` | Process |
| `ask{Question?}` | Decision |
| `form[/Label/]` | Input or output, drawn as an orange rectangle |
| `db[(Label)]` | Storage, drawn as a purple rectangle |
| `subgraph id [Title]` | A titled box around those nodes |

Edge labels use `-->|Yes|`. The official converter drops some Mermaid shape names to rectangles; the script recolors the ones in this table.
