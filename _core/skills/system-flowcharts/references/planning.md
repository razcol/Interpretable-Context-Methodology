# Planning a flowchart

Write this note before creating the spec. Keep it short enough that a reader can check the chart against it.

1. **Audience and purpose.** One sentence: who reads the chart, and what question it answers.
2. **Start, end, and omissions.** Name the trigger, the successful end, any error end, and two to four details you are leaving out so the chart stays readable.
3. **Direction.** `DOWN` for a decision-heavy flow. `RIGHT` for a pipeline. Do not mix them.
4. **Node inventory.** Every node gets an id, a label of about six words, and one kind: `start`, `end`, `error`, `process`, `decision`, `io`, `storage`, `subprocess`. Process labels are verb phrases. Decision labels are questions and end with `?`.
5. **Branches.** Every decision has at least two outgoing edges. Each edge has a label (`Yes`, `No`, or a short guard). The usual path should be the one a reader meets first going down or to the right.
6. **Groups.** Use groups only when the phases stack without sharing a row with the next phase. Skip groups when the chart has about seven nodes or fewer. A loop back to an earlier step is a separate node, not an arrow from a shape to itself.
7. **Check.** After generation, open the PNG. Every arrow must meet both shapes. Every decision label must sit on its own branch.

This follows ordinary flowchart practice: one start, explicit ends, questions on decisions, and a single reading direction. It is the useful subset of ISO 5807 symbol roles (terminator, process, decision, input/output, stored data), drawn with the shapes Excalidraw actually has.
