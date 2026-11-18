---
name: ai-readiness
description: Audits a university course and writes concrete, reviewable suggestions for making it AI ready (more hands-on, more AI literate or fluent, with honest process records and assessment of real learning and critical thinking instead of trivial AI use), then turns the suggestions the course team accepts into briefs a coding agent can implement and, for Canvas, a new course export. Use when someone asks to make a course AI ready, audit a course, syllabus, Canvas export (.imscc) or folder of materials for AI readiness, prepare suggestions for a course team or department, check a course against an institution's AI-ready standards (such as Northeastern's Edge certification), add AI exercises, AI assessments, an AI use policy, Frictional logs or Glimmers to a course, or implement accepted AI-readiness suggestions. Works from Nik Bear Brown's Conducting AI framework.
---

# ai-readiness

Universities are starting to require that courses be "AI ready". This skill does two jobs for two audiences:

1. **Suggestions for people.** It audits a course and writes concrete suggestions, drafted in the course's own content, that the course team reads, decides on and comments on (`arc/suggestions.md`).
2. **Briefs for coding agents.** It turns the suggestions they accept into precise implementation briefs (`arc/implement.md`), and for Canvas builds the accepted changes into a new course export with `./arc apply` and `./arc pack`.

The framework is `docs/framework.md`. Students **conduct** AI in the discipline's own work: they attempt the learning first, frame before prompting, delegate bounded work, judge and verify what comes back against independent evidence, add what only they can, and keep an honest Frictional record. Its **six readiness questions** are the lens for every audit and suggestion. An institution's own standards (for example Northeastern's Edge five, `docs/standards/`) are an optional profile on top. Read the framework before your first audit.

## The loop and who does what

```
course export or folder ->  ./arc open <course> <work> [--standards <profile>]   (tool: unpack, text, automatic check)
                        ->  audit      skills/audit/SKILL.md      (you: judge, write audit.md, ask what you need)
                        ->  suggest    skills/suggest/SKILL.md    (you: plan.json + drafts/, ./arc plan --try)
                        ->  ./arc report <work>                    (tool: suggestions.md for the course team)
course team reads it, decides, comments
                        ->  decide     skills/decide/SKILL.md     (you: ./arc feedback, revise, add their ideas)
                        ->  implement  skills/build/SKILL.md      (./arc implement -> implement.md for a coding agent;
                                                                   ./arc apply / validate / pack for Canvas changes)
```

| The person wants | Read |
|---|---|
| To know how AI ready a course is | `skills/audit/SKILL.md` |
| Suggestions for making it AI ready | `skills/audit/SKILL.md`, then `skills/suggest/SKILL.md` |
| To record the course team's decisions, revise, or add their ideas | `skills/decide/SKILL.md` |
| To implement accepted suggestions, or get the new course file | `skills/build/SKILL.md` |
| Many courses at once | `./arc batch <exports> <runs> [--standards …]`, then the audit for each course separately (one agent per course if you have them); suggest for a course only after its team answers the audit's questions |

Formats: the plan `docs/plan-format.md`; Canvas files `docs/imscc.md`; institutional profiles `docs/standards/`. Drafting starts from `templates/`.

## The rules that do not bend

1. **People decide.** You propose. Only the course team's own words accept, reject or revise a suggestion. Never accept on their behalf, and never treat "looks good overall" as a decision on specific items.
2. **Nothing invented.** No made-up statistics, quotes, student work, research findings or course facts. Examples in drafts are labelled as constructed. The instructor's own use of AI is never drafted by you.
3. **Evidence or it did not happen.** Every audit verdict quotes the course with its location.
4. **Real work, not trivial use.** Every suggestion uses this course's content, data and tasks, and asks students to think: attempt, judge, verify, explain. "Use ChatGPT to summarize the reading" is not a suggestion.
5. **Concrete enough for both audiences.** A person can decide from the suggestion's title, why and draft; a coding agent can implement it from the ops or the brief without guessing.
6. **Add, don't take away.** Prefer `append` and `insert_after`. Replace text the instructor wrote only when they ask by name. Never remove content.
7. **Small and reviewable.** Twelve good suggestions beat forty.
8. **New things arrive unpublished; nothing is uploaded or imported by you.** The original export is never touched.
9. **Course exports are private.** They contain names, email addresses and account ids. Keep work folders out of git and out of anything you publish.

## Commands

```
./arc open <course.imscc | folder> <work> [--standards <id>]    ./arc check <work>    ./arc map <work>    ./arc text <work>
./arc new-plan <work>    ./arc plan <work> [--try]    ./arc report <work>    ./arc feedback <work> <their-copy.md>
./arc accept|reject|revise|reset <work> S01 …    ./arc implement <work>
./arc apply <work>       ./arc validate <work>       ./arc pack <work> <new.imscc>
./arc status <work>      ./arc diff <a.imscc> <b.imscc>      ./arc batch <exports> <runs> [--standards <id>]
./arc install      ./arc help
```

Python 3.9 or newer, standard library only. Work folders go wherever the person likes, never inside this repository or any other git repository.

## What to tell the person at each stop

- After the audit: the summary, the six readiness questions in one line each (and the institution's standards if a profile is set), the level you recommend, and the facts you still need.
- After suggesting: the path to `suggestions.md` (run `./arc report`), the shortest path that answers every readiness question in one line, and how the course team responds.
- After implementing: what was built or briefed (from `build-log.md` and `implement.md`), every warning, what to import where, and what was not verified.
