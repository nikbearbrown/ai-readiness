---
name: ai-readiness-decide
description: Record the instructor's decisions on a change plan, revise suggestions they want changed, and draft their own ideas as new suggestions. Part of ai-readiness.
---

# The course team decides

The course team reads `arc/suggestions.md` (from `./arc report`) and answers under each suggestion: **yes**, **change** or **no**, with comments. When they send the file back, run `./arc feedback <work> <their-file>`: it records each decision and keeps their comments verbatim, and lists anything left undecided. When they answer in conversation or email instead, turn their words into `./arc` commands, one suggestion at a time, and show them what you recorded.

## Their words to commands

| They say | You run |
|---|---|
| "Yes to 1, 3 and 5" | `./arc accept <work> S01 S03 S05` |
| "Not 2, we already do that in lab" | `./arc reject <work> S02 --note "we already do that in lab"` |
| "4, but as a discussion, not an assignment" | `./arc revise <work> S04 --note "as a discussion, not an assignment"`, then revise (below) |
| "All of the certification ones" | Name the ids you take that to mean and confirm before accepting |
| "Looks good" | Ask which ones. General approval is not a decision on specific items |

Keep their words in `--note` verbatim. Never accept or reject anything they did not name. Rejected suggestions stay in the plan with their note; they are a record, not clutter.

## Revising

1. Read the note. If it is ambiguous, ask one question.
2. Change the drafts and ops. Keep the same id.
3. `./arc reset <work> S04` (back to proposed) and `./arc plan <work>`.
4. Show the instructor what changed in two or three lines, and ask again. A revision is never built unseen.

## Their own ideas

When the instructor proposes something ("add a reflection after the midterm about how they used AI to study"):

1. Add a suggestion with the next unused id, `origin: "instructor"`, `status: "proposed"`.
2. Draft it exactly as you would your own (`skills/suggest/SKILL.md`, sections 2–4), using the framework where it fits their idea and their words where it does not. Their idea wins over the framework.
3. If it conflicts with a rule (for example, it would replace text they wrote elsewhere, or invent a statistic), say so plainly and offer the nearest version that does not.
4. Show it and let them accept it like any other.

## When to build

After a round of revisions, run `./arc report` again and send the new `suggestions.md`: earlier decisions and comments are shown in it. When the team says to implement, follow `skills/build/SKILL.md`. Proposed and revise items are never implemented.
