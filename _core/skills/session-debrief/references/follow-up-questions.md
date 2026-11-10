# Follow-up questions this user asks

The questions this user asked most often after reading an agent's summary, taken from 35 Cursor sessions on this machine (2026-04 to 2026-11). Pick the 4 to 7 that fit the session and answer them in the debrief, so the user does not have to ask.

Each group lists the question as the user tends to phrase it, then what a good answer contains.

## Is it done?

- "Did you complete it successfully?" / "Did you run it yourself?"
  Yes or no, measured against the user's own goal. Say what was run, where (URL, branch, environment), and what was not run.
- "Are you sure?" / "Did you make sure?"
  Say what was checked, how, and what was not checked. Separate *verified* from *reported*.
- "Are there more stages?" / "What about the <X> part? I don't see it."
  List the steps that remain, what each needs from the user, and who runs it.

## Is it mine?

- "Is this introduced by my branch, or was it already there?"
  Say pre-existing or introduced, with the evidence (`git diff` against the base branch is the source of truth).
- "Is this related to my task?" / "Is this required for what I asked?"
  Say required or extra. For an extra, say what happens if it is removed.

## Why?

- "Why did you remove X?" / "What replaced it?"
  Name the replacement, or say nothing replaced it and why that is safe.
- "Why did you choose X?" / "Why does this file exist?"
  Give the reason and where it came from: the design, the code, a reviewer, or the agent's own judgement.
- "So bottom line, what is the issue?"
  Give the cause in one sentence. If the cause is not known, say "cause unknown" and name the missing evidence.
- "Does X cause Y?"
  Yes or no, then the mechanism in one or two sentences.

## Should I?

- "Should I accept the reviewer's suggestion?"
  Split the comment into separate claims. Give one verdict per claim and a reply the user can paste, in the reviewer's language.
- "Why would I, or wouldn't I, want to address it?"
  Give the cost of fixing it and the cost of leaving it, and a "fix it if / leave it if" line.
- "Is this over-engineered?"
  Name the simpler alternative and what it gives up.
- "Is it safe to push / deploy / delete?"
  Give the risk, whether it can be undone, and the exact list of what will be pushed or deleted.

## Is there a better way?

- "Was this needed before, or is it new?"
  Say how it worked before this session and what made the new piece necessary.
- "Is there a better approach, like doing it on demand?"
  Name each alternative, including the simplest one, with what it costs and what it gives up.
- "What are the side effects for users, SEO, performance, or security?"
  List the visible effects: status codes, caching, extra requests, open redirects, data exposure.
- "Does the codebase already do this somewhere?"
  Point to an existing file that follows or breaks the same pattern, as evidence for the verdict.

## For each item left undone

- "What is it, why would I do it, and why wouldn't I?"
  One plain sentence with one example, the cost of leaving it, and the cost of doing it.

## Explain it

- "What is X? In simple terms."
  One sentence, plus the real example from this session.
- "So you are saying <user's restatement>, right?"
  Pre-empt this: restate the conclusion in one sentence the user could say back.
- "What do I tell my team lead?"
  One paragraph the user can repeat.

## Formats that worked for this user

- Verdict or "Yes." / "No." in the first words.
- An option table with the consequence of each option and a recommendation.
- Before and after, side by side.
- ✅ / ❌ tables of where something works now.
- Numbered steps that use exact UI labels or commands, ending with what to reply.
- One analogy, only when the mechanism is abstract.
- A small diagram of the user's own current state.

## Formats that failed

- Long reports with done or not done at the bottom.
- "Bottom line" sections that still use undefined terms.
- Option lists with no recommendation, or "Want me to do option 2?" before the user understands the problem.
- One paragraph holding several claims, or a verdict that changes halfway.
- Coverage statistics and process narration.
- Steps for the wrong environment (PowerShell for a WSL user).
