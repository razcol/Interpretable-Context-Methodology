# Session types

Pick the closest type. It decides what the debrief leads with. A session can mix types; lead with the one the user's question belongs to.

| Type | Looks like | Lead `## How it works` with | Decisions usually are | Must also cover |
|------|------------|-----------------------------|----------------------|-----------------|
| Build or fix | Agent edited files to deliver a feature or fix | The behaviour now, one real example, before vs after | Merge, ship, fix leftovers first or later | Required vs extra changes; what was run vs reported |
| Review | PR comments, reviewer bot (Rovo), audit list | Each comment split into separate claims, one verdict each. Bottom line is Yes or No per claim | Follow, skip, or optional, per claim that this branch introduced. A pre-existing claim is one line, not a card | Introduced vs already there; one existing file:line that already follows the pattern; which values to add and which to leave; a reply to paste |
| Design question | User asked why it works this way, or whether an approach is right | The mechanism: request or data flow, the constraint that forces it, the failing step | Keep the design, switch to an alternative | Was it needed before; the alternatives including the simplest one; lifecycle (when it is written and read, whether a restart is needed); user-visible side effects (status codes, what happens when it fails, caching, SEO, security) |
| Investigation | Something fails and the agent looked for the cause | Cause known or unknown, and the evidence | Which next check or fix to try | Symptom vs cause, kept apart; what was ruled out |
| Orchestration | Many subagents, plan todos, auto notifications | The pipeline: what each part produced and where it stopped | Accept, rerun, or split follow-ups | Every hand edit a subagent listed, even when the close skips it, with that subagent's own reason; a "not a gap" line for each item the agent refused; instructions that may have been broken |
| Short Q&A | Under 5 user turns of explanation | The answer itself | Often none | Keep the whole debrief near 400 words |
