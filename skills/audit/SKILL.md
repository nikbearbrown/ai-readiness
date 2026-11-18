---
name: ai-readiness-audit
description: Audit an opened course for AI readiness against the framework's six readiness questions (and an institution's standards profile if one is set), and write audit.md. Part of ai-readiness; read the root SKILL.md first.
---

# Audit a course

You have a work folder from `./arc open`. The automatic check (`arc/check.md`) has found candidate evidence and clear absences for the six readiness questions (and for the institution's standards, if a profile is set). Your job is the part it cannot do: read the course, judge each question, understand what the course teaches and how, and see where AI could do real work in it and where it would only be trivial use.

## 1. Know the course and its students

Read `arc/text/course.md` (the map), `arc/text/syllabus.md`, `arc/check.md` and, if it exists, `arc/text/announcements.md`. Announcements do not count for any Edge standard, but they often hold the course's real AI policy, grading changes, tool access and corrections; quote them as context, never as evidence of MEETS. Then fill in this profile. Infer what you can from the syllabus and say so; ask the instructor for the rest before suggesting anything, because the right suggestions depend on it.

- **Discipline and level:** subject; undergraduate, graduate, professional.
- **Students:** who they are (majors, background, online or in person), roughly how many.
- **What students produce:** problem sets, essays, code, designs, lab reports, presentations.
- **Grading:** what is graded, how much, with what rubrics.
- **Tool access:** what AI tools students can use (an institutional tool, a free chatbot, none). Never assume a paid tool.
- **Goal:** what the course team wants (a proposal to a department, an institution's certification, their own improvement); a target level (literacy or fluency) if they have one; any assignment they already picture as the AI one.

## 2. Judge the six readiness questions (and the institution's standards)

For each of R1–R6 (`docs/framework.md`), read the evidence the check listed, open the files it points to, and decide **MEETS**, **PARTIAL**, **MISSING** or **NOT SUPPLIED** (MEETS: the evidence is in the material and quoted; PARTIAL: something is there but falls short, say what; MISSING: the material was read and it is not there; NOT SUPPLIED: the material that would hold it is not in the export). Quote the evidence (one or two lines) with its location: "syllabus, section *Generative AI Policy*", "module 4, page *2 – Overview*", "assignment *Week 2 Boondoggle Report*". Name any **trivial AI use** you find (AI asked for an answer with no judging step); the check lists candidates under R4.

If the work folder has a standards profile (`check.md` shows its section; profiles live in `docs/standards/`), judge each of its standards the same way, using the test in its `.md` file. For Northeastern's Edge profile, what usually decides the hard cases:

- **E1:** both halves must be in the syllabus text. A linked video or a separate page is PARTIAL. A sentence like "I use generative AI tools in developing this course for…" is the instructor half.
- **E2:** module-level, explicit, AI plus a dimension. A course outcome alone is PARTIAL.
- **E3–E5 are one chain.** Name the designated activity. Students must use an AI tool in it themselves. A named activity that permits but does not require AI is PARTIAL; course-wide permission (a chatbot, a policy) with no such activity is MISSING. If the activity asks students to use AI but never to assess its output, E4 is MISSING. If its rubric (or the grading described in its text, when the export has no rubric) grades only the product, E5 is MISSING; grading described only in prose is PARTIAL.
- When the check says CHECK, the evidence may still fail on reading. When it says MISSING, look once more in the most likely place before you agree.

## 3. Read the course through the framework

Read `docs/framework.md` if you have not. `arc/text/README.md` lists every module file with its word count. If the modules total under about 60,000 words, read them all. Otherwise read, for **every** module, its overview and objectives, its discussion and its graded work; then read in full the modules most likely to get suggestions (the strongest candidate activities, the modules whose content gives AI the most real work). Course notebooks are in `arc/text/notebooks/` (its README says which assignment or page links each one; unlinked ones are usually older copies): read the linked ones for those modules, because the real tasks often live there. Say in the audit what you read in full and what you sampled. For each module, note:

- what it teaches, in a phrase;
- how it ends (an assignment, a quiz, a discussion, nothing);
- whether students attempt anything before help is available;
- where AI could do **real work** here and with what verdict: **deprioritize** (AI may take it), **supervise** (AI drafts, the student checks), **protect** (the student must do it; it is the learning);
- which of the five capacities the module's content could exercise (plausibility auditing, problem formulation, tool orchestration, interpretive judgment, executive integration).

Course-wide, note which framework moves already exist: phase gates, prediction, Frictional logs, Glimmers, sign-offs, disclosure, independent verification, process grading. The check's "Moves found" column comes from keywords and has false positives (the word "predict" in a lesson is not a prediction-lock); confirm each by reading. Note also what the check's course facts say about file types an assignment accepts and rubrics shared across assignments: they decide where additions can go.

## 4. Recommend a level

Literacy or fluency, from the evidence: what students already do with AI, the course type, tool access. Most graduate courses start at literacy. Say why in two sentences. The instructor decides.

## 5. Write `arc/audit.md`

Use exactly this structure. Summary first: the instructor may read nothing else.

```markdown
# AI readiness audit: <course title>

## Summary
<Three to five sentences: how AI ready the course is now (and, with a profile, whether it meets the institution's
standards); what is missing; the recommended level; the two or three changes that would matter most; what you
still need from the course team.>

## Course profile
<The section-1 profile, marking what was inferred and what the instructor told you.>

## Recommended level
<Literacy or fluency, and why, in two sentences. The instructor decides.>

## The six readiness questions
| Question | Verdict | Evidence (quoted, with location) | What is short |
|---|---|---|---|
| R1 Clear rules for AI use and disclosure | … | … | … |
| R2 Students attempt the learning first | … | … | … |
| R3 Hands-on AI work in the discipline | … | … | … |
| R4 Students judge and verify AI output | … | … | … |
| R5 The process is recorded and graded | … | … | … |
| R6 Assessment shows learning AI cannot fake | … | … | … |

The designated AI activity (R3–R5 chain): <name it, or say there is none and which existing activity is the best candidate.>
Trivial AI use found: <where, or "none">.

## <The profile's audit heading, e.g. "Northeastern's Edge standards"> (only if a profile is set)
| Standard | Verdict | Evidence | What is short |
|---|---|---|---|

## Through the framework
<What the course already does well, in the framework's terms. What is missing. Two short paragraphs.>

| Module | Teaches | Ends with | AI could… (verdict) | Capacity |
|---|---|---|---|---|

## Errors found in the course materials
<Optional. Claims in pages, notebooks or keys that are wrong when checked: quote, location, and why. These are
for the instructor to fix or to use as real material for a planted-flaw audit; never fix them silently.>

## Things that will matter when building
<Facts from check.md's "Course facts" that affect the build: assignments outside modules, pages in no
module, rubrics shared across assignments, points that do not match rubrics, duplicate titles, links to
other courses, empty modules.>

## What I did not read or could not judge
<Modules sampled rather than read; quizzes (questions are not extracted); files (PDFs, slides) not opened;
anything outside the export.>
```

Then tell the instructor the summary and ask for the profile facts you are missing. Do not start suggesting until you have them, unless the instructor says to go ahead with your assumptions; then state the assumptions at the top of the plan.
