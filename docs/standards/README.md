# Institutional standards profiles

The toolkit's own lens is the framework's six readiness questions (`../framework.md`). Many institutions add their own requirements for an "AI-ready" course. A profile maps them onto what the toolkit already checks, so the audit, the automatic check and the course team's suggestions document can report against them too.

Use one with `./arc open … --standards <id>`, `./arc batch … --standards <id>` or `./arc check <work> --standards <id>`, and set `"standards": "<id>"` in the plan's `course` block.

| Profile | File |
|---|---|
| Northeastern University: Edge AI-ready course certification (five minimum standards, four dimensions, two levels) | `northeastern-edge.json`, explained in `northeastern-edge.md` |

## Adding your institution

Copy `northeastern-edge.json` to `<your-id>.json` and write a `<your-id>.md` that states each standard in your institution's words and the test the audit should apply. Each standard's `based_on` names the automatic signal it rests on:

| Signal | What the automatic check looks for |
|---|---|
| `policy` | AI use rules and disclosure in the syllabus, including the instructor's own use |
| `objective` | module objectives that name AI |
| `attempt_first` | students attempting work before AI; per-module statements of what AI should and should not do |
| `hands_on` | activities that require students to use AI |
| `critique` | those activities asking students to evaluate the AI's output |
| `process` | process records in graded work (logs, disclosure, sign-offs) |
| `process_rubric` | rubric criteria that grade the process of working with AI |
| `cant_fake` | assessment that shows learning AI cannot supply (explanation on request, oral or paper checks, predictions) |

The automatic check only finds evidence and absences; the audit decides whether each standard is met.
