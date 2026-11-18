---
name: ai-readiness-build
description: Implement accepted suggestions: write implement.md for a coding agent, build the Canvas changes into a new .imscc, validate it, and say how to import and check it. Part of ai-readiness.
---

# Implement what was accepted

Start with `./arc implement <work>`. It writes `arc/implement.md`: every accepted suggestion as a brief. Suggestions marked *built by arc* are Canvas changes the steps below make. Suggestions marked *by hand* (a notebook fix, an exam change) are for a coding agent or a person to do from their brief; do them only if you were asked to, check each against its *Done when* list, and report what you could not check. Then, for the Canvas changes:

## Steps

1. `./arc apply <work>`. It applies accepted suggestions only, from the untouched source, into `arc/build/`, and runs the validation. If it stops on an op, it names the suggestion: fix the plan (an id or heading that moved, an ambiguous title), show the instructor if the content changed, and run it again.
2. Read `arc/build-log.md` and every warning. Each warning is a decision for the instructor, not something to silence:
   - *rubric totals differ from points*: ask whether to change the points or scale the criteria; record the answer as a revision.
   - *shared rubric copied*: the edited assignment now has its own rubric; the others keep the old one. Say so.
   - *new assignment group with weight 0*: they must set its weight in Canvas.
3. `./arc validate <work>` must show FAIL 0.
4. `./arc pack <work> <path>`. Default path: next to the original export, named `<original name>-ai-ready.imscc`, unless the instructor names one. Never overwrite the original.
5. `./arc diff <original.imscc> <new.imscc>` and keep the summary for the report.

## Tell the instructor

- The path of the new file and its size.
- What changed, per accepted suggestion, from the build log, in plain words ("a new unpublished module *AI lab* with one assignment and its rubric").
- Every warning and the decision it needs.
- **How to import:** Canvas → the target course → Settings → Import Course Content → *Canvas Course Export Package* → choose the file → *All content*. Import into a **sandbox or a new, empty course shell** first. Re-importing into the course the export came from can duplicate pages and modules that were created there by hand.
- **What to check after import:** the new items appear where the plan said, unpublished; each new assignment has its rubric attached and the right points and group; the syllabus shows the new section; graded discussions are graded; links in new pages work. Then publish what they want students to see.
- **What was not verified:** the toolkit checks the file's internal consistency against real Canvas exports, but whether a particular Canvas instance accepts every detail is only known after the first sandbox import. Ask them to tell you what they see, and record anything that did not come through.

Do not upload the file anywhere, and do not import it yourself.
