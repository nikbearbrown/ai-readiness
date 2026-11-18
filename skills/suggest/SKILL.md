---
name: ai-readiness-suggest
description: Turn an audit into concrete suggestions (plan.json + drafts/) that the course team can review in suggestions.md and a coding agent can implement. Part of ai-readiness; read the root SKILL.md and the audit first.
---

# Suggest changes

Every suggestion serves two readers. The **course team** must be able to decide from its title, its why and its draft. A **coding agent** must be able to implement it without guessing: from its `ops` (Canvas changes `./arc apply` builds) or, when the tool cannot make the change, from its `advice` and `brief` (`templates/brief.md`). Suggestions the tool cannot build are welcome: fixing a notebook, changing an exam format, adjusting grading weights, a TA practice.

Inputs: `arc/audit.md`, `docs/framework.md`, `docs/plan-format.md`, `templates/`, and `./arc map <work>` for identifiers. Output: `arc/plan.json` and one draft file per piece of content under `arc/drafts/`, checked with `./arc plan <work>` until it reports FAIL 0.

## 1. Choose

Work in this order and stop when the plan is enough. Twelve suggestions is a good first round; more than fifteen is too many to decide.

**A. The core path.** The smallest set that gives every readiness question (R1–R6) a yes, and meets the institution's standards if a profile is set. Usually:

1. the AI use policy in the syllabus (R1);
2. the designated activity, a **Conduct exercise** or a **Glimmer**, in a module whose content gives AI real work, with its judging and verifying step (R3, R4);
3. **process criteria** on that activity's rubric, or the **Frictional log** on graded work (R5);
4. a **phase gate** where the module's skill must be protected (R2);
5. one assessment AI cannot fake: explanation on request, a planted-flaw audit, a prediction-lock (R6);
6. with Northeastern's Edge profile, one module objective that names AI (E2).

If the course already has a strong candidate activity, upgrade it (`edit_assignment` or `edit_discussion` with a critique section and `add_criteria`) instead of adding a new one. Fewer new things is better.

The designated activity must have students **use an AI tool themselves** (E3). At literacy level, give everyone the same fixed, bounded request on this module's task and grade their audit of the result; at fluency level, they frame and delegate their own. A constructed AI output alone meets E4 practice, not E3. If students have no tool access, tell the instructor E3 cannot be met as things stand.

E1 cannot reach MEETS from the plan alone: the instructor's own AI use is theirs to write. Say so in S01's `why`.

**B. Assessment.** Where graded work grades only the product, suggest the **Frictional log** (`edit_assignment`, append the block, add the Frictional rubric criteria). For courses with exams or quizzes, a **planted-flaw audit** (as a discussion, or as a page describing a quiz question the instructor builds; the tool does not edit quizzes). Its key goes in a **separate page** in the same suggestion, titled "Key: …", unpublished; tell the instructor never to publish it.

**D. Corrections.** Errors the audit found in the materials become suggestions too, with the move `correction`: a correction note after the wrong passage on a page, or an advice-only suggestion with a `brief` for files the tool cannot edit (one suggestion per file or per kind of fix, so the team can decide each). Never fix silently.

**C. Deepening, module by module.** For modules where the audit found real AI work: a **phase gate** page (AI should / Human should) and an **end-of-module exercise** (Conduct exercise, or the three ungraded Assessments where modules end with nothing). Skip modules where AI has nothing real to do, and say so in the audit, not in the plan.

Fit everything to the audience in the audit: the discipline's words for the capacities, the students' level (shorter logs and more scaffolding for undergraduates; supercollaborator-level delegation for professionals), and the tools they actually have. With no tool access, choose literacy moves: audits of AI output you supply.

## 2. Draft

Start from the template for the move (`templates/<move>.md` or `.json`) and fill every `{{slot}}` with this course's real content: its topics, data, problems, readings, the module's own terms. Read the module's text in `arc/text/modules/` before drafting for it.

- **No generic prompts.** If the draft would work unchanged in another course, it is not done.
- **Constructed examples are labelled** ("This output was written for this exercise"). For a planted-flaw audit, write the AI output yourself with one flaw a student of this module can find, and put the key in an instructor-only note.
- **The instructor's half of the policy stays as prompts.** Keep the template's bracketed questions; do not answer them.
- **Match the course.** Use the course's voice and terms. Heading levels inside drafts start at `##` (the tool shifts them to match where they land).
- **Dependencies:** when one suggestion only makes sense with another (criteria that grade a section another suggestion adds), list it in `requires`.
- **Rubrics:** start from `templates/*.json`; rewrite descriptions in the course's terms; keep points proportional. If the criteria change an assignment's total, say in `why` how the points should change (for example "Frictional at 10%: raise points from 100 to 110, or scale the new criteria to 10 of the existing 100") and set `points` only if that is the suggestion. `./arc` warns on every mismatch.
- **Grading time.** Each rubric draft says roughly how long it takes per submission.

Drafts are Markdown (`drafts/S03-conduct-exercise.md`, `drafts/S03-rubric.json`). Name them by suggestion id.

## 3. Place

- Use identifiers from `./arc map` for modules, pages and assignments; titles only when unique.
- End-of-module exercises go after the module's last teaching item: `"after": "<last page id>"`, or `"end"`.
- Policy: `edit_syllabus` with `insert_after` the existing academic integrity or AI section, else `append`.
- Objectives: `edit_page` with `insert_after` the module's objectives heading; check the heading text in `arc/text/modules/`.
- New items are unpublished by default; leave them so.
- Assignment groups: use the identifier when two groups share a name (`./arc plan` fails on ambiguity).

## 4. Write the plan

One suggestion per decision the instructor makes. Fill every field (`docs/plan-format.md`): `id` (S01…), `title` (what it does, in the course team's terms), `module`, `why` (the gap, citing the audit), `framework`, `readiness`, `standards` (if a profile is set), `level`, `effort`, `status: "proposed"`, and either `ops` or `advice` (+ `brief`). Order: the core path first, then assessment, then deepening, then corrections.

Put any assumptions you made about the audience in `course.audience` and in the first suggestion's `why`.

Run `./arc plan <work> --try`. Fix every FAIL, and read every WARN: it builds the whole plan in memory and shows what the instructor's build would hit. Read `arc/plan.md` once as the instructor will: if a suggestion's title and why do not tell them what they are deciding, rewrite them.

## 5. Hand it over

Run `./arc report <work>` and tell the person: the path to `suggestions.md` (the document for the course team); the core path in one line ("S01–S05 together answer all six readiness questions"); the count of the rest; and that the team answers under each suggestion (yes, change or no, with comments). Then follow `skills/decide/SKILL.md`.
