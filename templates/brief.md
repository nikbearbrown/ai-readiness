<!--
Template: implementation brief for an advice-only suggestion (one the arc tool cannot build: fixing a notebook,
changing an exam, adjusting grading weights, recording a video, changing a file in the course).
Referenced from the suggestion's "brief" field. People see it under "Details"; coding agents get it in implement.md.
Write it so an agent with no other context could do the work and know when it is finished.
-->

**Goal.** {{one sentence: what is true when this is done}}

**Where.** {{exact files, pages, cells, assignments; paths or titles from ./arc map; course files under web_resources/}}
For a course file: save the fixed version as `arc/files/<its exact path in the course>`; `./arc apply` swaps it in.

**Change.**

1. {{step}}
2. {{step}}

**Done when.**

- {{a check an agent can run or see: a test that passes, an output that matches, a sentence that is present}}
- {{…}}

**Do not.** {{what must stay as it is: the instructor's wording elsewhere, other notebooks, grading weights}}

**Needs a person.** {{anything only the instructor can decide or write; "nothing" if none}}
