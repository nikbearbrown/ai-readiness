# ai-readiness

Concrete suggestions for making any university course AI ready, for the people who teach it and for the coding agents that help them change it.

This is a **skill**, not a course. Download it, open it in Claude Code (or another coding agent), and point it at a course you teach.

Universities, Northeastern among them, are beginning to require that courses be AI ready. This toolkit audits a course (a Canvas export or a folder of materials) and writes suggestions that make it more hands-on, more AI literate or fluent, with honest records of the process (the Frictional log) and assessment of real learning and critical thinking, instead of trivial AI use. Every suggestion is drafted in the course's own content.

It writes for **two audiences**:

- **People.** `suggestions.md` is a document for the course team: where the course stands, each suggestion with its reason and its draft, and a place to answer yes, change or no with comments. Their answers come back into the plan with `./arc feedback`.
- **Coding agents.** `implement.md` turns what the team accepted into precise briefs for Claude Code, Codex or Claude Desktop. Canvas changes are built by `./arc apply` into a new `.imscc`; changes the tool cannot make (fixing a notebook, changing an exam) come with a brief saying where, what, and how to know it is done.

```
course  →  ./arc open  →  audit  →  suggestions  →  ./arc report  →  course team decides  →  ./arc feedback
        →  ./arc implement (briefs for agents)  →  ./arc apply / pack (new Canvas export)  →  import into a sandbox
```

## What "AI ready" means here

Students **conduct** AI in the discipline's own work: they frame the problem before prompting, delegate bounded tasks, audit what comes back before checking it, verify it against evidence the model did not produce, add what only they can, sign for the result, and keep an honest record of how it happened. The framework is Nik Bear Brown's, from his courses *Conducting AI*, *Irreducibly Human*, *Computational Skepticism for AI* and *Prompt Engineering for Generative AI*, with the Frictional process log and Glimmer assignments: [docs/framework.md](docs/framework.md).

The framework asks six readiness questions of every course: clear rules for AI use (R1), students attempt the learning first (R2), hands-on AI work in the discipline (R3), students judge and verify AI output (R4), the process is recorded and graded (R5), and assessment shows learning AI cannot fake (R6).

**Institutional standards are optional profiles.** Northeastern's AI readiness definition and Edge's five minimum standards are included ([docs/standards/northeastern-edge.md](docs/standards/northeastern-edge.md)); use them with `--standards northeastern-edge`. Add your institution's in `docs/standards/`. The toolkit certifies nothing; it prepares the course and the conversation.

## What it suggests

Drafted in the course's own content, never generic:

- an AI use policy for the syllabus (your own use of AI in preparing the course stays yours to write);
- module objectives that name AI and a judgment students must make;
- end-of-module **Conduct it** exercises: predict and frame, delegate, audit first, check independently, say what you add, sign off;
- **Glimmers**: open generative assignments graded on process and judgment, with an AI Use Disclosure;
- the **Frictional log** on graded work (10%, five criteria);
- planted-flaw audits for quizzes and exams, which work on paper with no AI in the room;
- rubric criteria that grade how students worked with AI, not only what they handed in;
- phase gates: per module, what AI should do and what the student must.

## Get started

```bash
git clone <this repository>
cd ai-readiness
./arc help
```

Python 3.9 or newer, standard library only. Then, in Claude Code (or another agent) in this folder:

> Here is my course export: ~/Downloads/info6205-export.imscc. Make it AI ready. It's a graduate algorithms course, about 60 students, online; they can use Claude through the university.

The agent reads [SKILL.md](SKILL.md) and works through the loop with you. Files it writes for you to read:

| File | What it is |
|---|---|
| `<work>/arc/check.md` | the automatic check: evidence found and clear absences |
| `<work>/arc/audit.md` | the audit: the six readiness questions (and your institution's standards, if a profile is set) answered with quoted evidence |
| `<work>/arc/suggestions.md` | the suggestions for the course team: reasons, drafts, and a place to answer |
| `<work>/arc/implement.md` | what was accepted, as briefs for a coding agent |
| `<work>/arc/build-log.md` | what was built from what you accepted |

To use it from any project: `./arc install`.

**Many courses at once.** Put the exports in one folder and run `./arc batch <exports-folder> <runs-folder>`. Each course gets its own work folder (named like `info6205-fall-2026`) and the automatic check, and `<runs-folder>/README.md` lists them all with their signals. Keep the runs folder outside any git repository. Then audit each course on its own, and suggest for a course only after its instructor has answered the audit's questions.

## The commands

| Command | Does |
|---|---|
| `./arc open <course.imscc or folder> <work>` | unpack, write the course as text, run the automatic check |
| `./arc map <work>` | modules and items with their identifiers |
| `./arc check <work>` | re-run the automatic check |
| `./arc plan <work> [--try]` | check the plan and write `plan.md`; `--try` builds every suggestion in memory and reports what would happen |
| `./arc report <work>` | write `suggestions.md`, the document for the course team |
| `./arc feedback <work> <their-copy.md>` | read the team's decisions and comments back into the plan |
| `./arc implement <work>` | write `implement.md`, the briefs a coding agent works from |
| `./arc accept / reject / revise / reset <work> S01 …` | record decisions (`--note` keeps your words) |
| `./arc apply <work>` | build the accepted suggestions into `<work>/arc/build/` and validate |
| `./arc validate <work>` | the consistency checks Canvas import depends on |
| `./arc pack <work> <new.imscc>` | write the new export |
| `./arc diff <a.imscc> <b.imscc>` | what changed |
| `./arc batch <exports> <runs>` | open and check every export in a folder; index in `<runs>/README.md` |

## Safety

- The original export is never modified. Changes are built from it into a separate folder and then a new file.
- New pages, assignments, discussions and modules arrive **unpublished**.
- A rubric shared by several assignments is never edited in place; the changed assignment gets its own copy.
- Nothing is uploaded. Import the new file into a **sandbox or new course shell** first: re-importing into the original course can duplicate content that was created there by hand.
- Course exports contain names, email addresses and account ids. Keep work folders private.

## What has been tested

`python3 -m unittest discover tests` (27 tests) runs the tool on a constructed course: every kind of change, rebuild determinism, the original left untouched, shared rubrics, dependencies between suggestions, leftover placeholders, refusals.

The engine was also run on real Canvas exports: a 1 GB course with 140 modules and 1,156 pages, and a course with rubrics shared by 13 assignments, graded discussions and quizzes. An unmodified pack is identical entry for entry; changed packs reopen and validate.

A fresh agent with no other context followed the skills on a real graduate algorithms course export and produced an audit and a ten-suggestion plan (certification path in four suggestions) that built cleanly in a trial; its notes on what was unclear were folded back into the skills and tool.

**Importing a built file into Canvas has not yet been tested.** Do that in a sandbox and report what you see.

## Layout

```
SKILL.md            the agent's entry point; skills/ audit, suggest, decide, build
docs/               framework.md, plan-format.md, imscc.md, standards/ (institutional profiles)
templates/          drafts of every move (policy, objective, phase gate, conduct exercise, glimmer,
                    frictional, planted-flaw audit, sign-off, module assessments) and rubric JSON
scripts/            the arc tool (stdlib Python)
tests/              unit tests and a constructed course
```
