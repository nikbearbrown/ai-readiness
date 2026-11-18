# The change plan: `plan.json`

The plan is the hand-off between the parties. The planning agent writes suggestions into it. `./arc report` turns it into `suggestions.md` for the course team, who accept, reject or ask for a revision of each one (`./arc feedback` reads their answers back). `./arc implement` turns what they accepted into `implement.md`, briefs for a coding agent; `./arc apply` builds the Canvas changes mechanically, without any model in the loop, so the same plan always builds the same course.

The plan lives at `<work>/arc/plan.json`. Long content (page bodies, assignment descriptions, rubrics) lives in separate files under `<work>/arc/drafts/` so the instructor can read and edit it as ordinary Markdown. `./arc plan <work>` checks the plan and writes `plan.md`, the instructor's reading copy.

## Shape

```json
{
  "version": 1,
  "course": {
    "title": "INFO 6205 Program Structure and Algorithms",
    "audience": "first-year MS students, mixed programming background",
    "level": "literacy",
    "discipline": "computer science"
  },
  "suggestions": [
    {
      "id": "S01",
      "title": "Say how you used AI to build this course, and how students may use it",
      "origin": "agent",
      "module": null,
      "why": "The syllabus has no AI section. E1 needs both halves in the syllabus itself.",
      "framework": ["policy"],
      "readiness": ["R1"],
      "standards": ["E1"],
      "dimensions": ["D3"],
      "level": "literacy",
      "effort": "small",
      "status": "proposed",
      "note": "",
      "ops": [
        {"op": "edit_syllabus", "mode": "append", "body": "drafts/S01-ai-policy.md"}
      ]
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `id` | `S01`, `S02`, … Never reused, never renumbered. Instructor suggestions continue the sequence |
| `origin` | `agent` or `instructor` |
| `readiness` | Which of the framework's six questions it strengthens (`R1`–`R6`, `framework.md`). Optional: derived from `framework` when absent |
| `standards` | Optional. Which standards of the institution's profile it meets (for Northeastern's Edge: `E1`–`E5`). The older name `edge` is still read |
| `advice` | For a suggestion the tool cannot build (no `ops`): what the course team would do, in one or two sentences for people |
| `brief` | Optional, with `advice`: a draft file (`templates/brief.md`) telling a coding agent exactly where and what to change and how to know it is done |
| `supports` | Optional. Standards of the profile this suggestion strengthens without meeting on its own |
| `module` | The module it belongs to (identifier or exact title), or `null` for course-wide |
| `why` | One or two sentences: the gap, in the course's own terms, citing the finding |
| `framework` | Which moves from `framework.md` section 4 it uses: `policy`, `objective`, `phase-gate`, `conduct`, `glimmer`, `frictional`, `planted-flaw`, `sign-off`, `process-criteria`, `module-assessments`, `relative-quartile`, `confession`, `verb-audit` |
| `edge` | Older name for `standards` (Northeastern's E1–E5) |
| `dimensions` | Which of D1–D4 it develops |
| `level` | `literacy` or `fluency` |
| `effort` | The instructor's review time: `small` (minutes), `medium` (under an hour), `large` |
| `status` | `proposed`, `accepted`, `rejected` or `revise` |
| `note` | The instructor's words when they ask for a revision or reject. Keep them verbatim |
| `requires` | Optional. Ids this suggestion depends on (criteria that grade a section another suggestion adds). `plan` warns and `apply` refuses when a required suggestion is not also accepted |
| `ops` | The Canvas changes, applied in order. Empty or absent for an advice-only suggestion (then `advice` is required) |

## Statuses and who sets them

- The agent writes `proposed`.
- Only the instructor moves a suggestion to `accepted` or `rejected` (`./arc accept S01 S03`, `./arc reject S02 --note "..."`). An agent may run those commands only with the instructor's words for each id in front of it.
- `./arc revise S04 --note "make it a discussion, not an assignment"` sets `revise`. The agent rewrites the ops and drafts, then sets it back to `proposed` with `./arc reset S04`. The instructor sees it again; a revision is never applied unseen.
- An instructor's own idea becomes a new suggestion with `origin: instructor`, drafted by the agent, status `proposed`, so the instructor sees the actual text before it is built.

## Operations

References to existing course objects take the Canvas identifier (from `./arc map`) or an exact title. An ambiguous title is an error, never a guess.

| `op` | Fields | What it does |
|---|---|---|
| `add_module` | `title`, `after` (`end` or a module), `published` | A new module |
| `add_page` | `module`, `title`, `body`, `after`, `published` | A new page, placed in the module |
| `add_assignment` | `module`, `title`, `body`, `points`, `submission_types`, `group`, `rubric`, `after`, `published` | A new assignment with an optional new rubric, placed in the module |
| `add_discussion` | `module`, `title`, `body`, `points` (optional, graded if set), `rubric`, `after`, `published` | A new discussion topic, placed in the module |
| `edit_syllabus` | `mode`, `heading`, `body` | Changes the syllabus page |
| `edit_page` | `page`, `mode`, `heading`, `body` | Changes an existing page |
| `edit_assignment` | `assignment`, `mode`, `heading`, `body`, `add_criteria`, `points`, `submission_types`, `allowed_extensions` | Changes an existing assignment's description, adds rubric criteria, changes points, submission types or allowed file types (`[]` or `""` allows any) |
| `edit_discussion` | `discussion`, `mode`, `heading`, `body`, `add_criteria`, `points` | Changes an existing discussion's text; adds rubric criteria or changes points if it is graded |

Quizzes are never edited (their questions are QTI the tool does not rewrite). A suggestion for a quiz is a page or discussion describing the question, for the instructor to add in Canvas.

- `body` is a path to a Markdown file under `drafts/` (converted to HTML at build time) or to an `.html` file (used as is).
- `mode` is `append` (add at the end), `insert_after` (after the section whose heading is `heading`), `insert_before` (just before the heading `heading`), or `replace_section` (replace the section whose heading is `heading`, up to the next heading of the same or higher level). An append onto text that ends with a table or a collapsed block (a rubric pasted into a discussion, say) lands after it; `--try` warns.
- `after` is `end` (default), `start`, or an item or module to follow.
- `published` defaults to `false`: new things arrive unpublished, so the instructor reviews them in Canvas before students see anything. Edits keep the object's existing state.
- `group` is an assignment group identifier or exact name. A name that does not exist creates the group with weight 0, and the build warns.
- `submission_types` uses Canvas names: `online_text_entry`, `online_upload`, `online_url`, `external_tool`, `none`, `on_paper`.
- `points` on `edit_assignment` changes `points_possible`. The build warns whenever a rubric's total does not equal the assignment's points.

### Rubric files

`rubric` and `add_criteria` point to a JSON file under `drafts/`:

```json
{
  "title": "Frictional log",
  "criteria": [
    {
      "description": "Attempts recorded honestly",
      "long_description": "Shows what was tried, what failed, and what changed, in the order it happened.",
      "points": 4,
      "ratings": [
        {"description": "Full", "long_description": "Every attempt, including failed ones, with what was learned", "points": 4},
        {"description": "Partial", "long_description": "Attempts listed without what changed", "points": 2},
        {"description": "Missing", "long_description": "No attempts recorded", "points": 0}
      ]
    }
  ]
}
```

### Drafts

Markdown with headings, paragraphs, bold, italics, links, images, code, block quotes, flat lists and pipe tables. Write `\|` for a literal pipe inside a table cell. Nested lists are flattened; consecutive lines join into one paragraph, so leave a blank line between paragraphs. Lines that are HTML block tags (`<details>`, `<summary>`, `<div>`, `<table>`, `<iframe>`, `<img>`, …) pass through unchanged. HTML comments (`<!-- -->`) are dropped: use them for notes to the agent, never for anything the instructor or students need.

Drafts must not reach Canvas with `{{slots}}` or `[bracketed instructor prompts]` in them: `plan` and `apply` warn when they do. Edits to existing published objects (the syllabus, a published page) are visible as soon as the course is imported.

## Trying a plan before anyone decides

`./arc plan <work> --try` builds every suggestion that is not rejected, in memory, and reports per suggestion whether it applies, every warning (rubric totals, shared rubrics, text landing after a table) and the validation result. Nothing is saved. Add `--show S03 S07` to print, as readable text, exactly where each listed suggestion's text lands, with its surroundings. Run it before handing a plan to the course team.

### Fixed course files

A course file the tool cannot edit (a notebook, a deck, a PDF) is fixed by a coding agent or a person and saved under `<work>/arc/files/` at the file's exact path in the course (`./arc text` and the notebooks README show paths, e.g. `web_resources/Assignments/Wk6.ipynb` → `arc/files/web_resources/Assignments/Wk6.ipynb`). `./arc apply` swaps every such file into the build and lists it in the build log; a path that is not in the course is refused with a warning. Briefs for these fixes should name the target path.

### Discussions without headings

`insert_before` also takes a tag instead of a heading: `"heading": "<details>"` inserts just before the first `<details>` (or `"<table>"`), so a new part can sit above a rubric pasted at the end of a discussion.

### Corrections

A suggestion that fixes a factual error in the course (a wrong claim on a page, a wrong expected output in a notebook) uses the framework move `correction`; upkeep that is neither (old copies, links to other courses, dates to shift) uses `housekeeping`. On a page, prefer a clearly titled correction note inserted after the wrong passage over rewriting the instructor's text. In files the tool cannot edit (notebooks, slides, PDFs), make it advice-only with a `brief`.

## What `apply` guarantees

- It starts from the untouched source copy every time and writes a separate build folder, so applying twice gives the same result and the original export is never modified.
- Identifiers for new objects are derived from the suggestion id, the op's position and its title, so rebuilding gives the same identifiers.
- It applies `accepted` suggestions only, in id order, and stops at the first op it cannot apply, naming the suggestion and op.
- It writes `<work>/arc/build-log.md`: every file added or changed, per suggestion.
