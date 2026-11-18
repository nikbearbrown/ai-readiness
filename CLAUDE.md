# ai-readiness: notes for Claude

When someone here asks to audit a course, make it AI ready, or build changes into a Canvas export, read `SKILL.md` and follow it.

What matters most:

1. **The instructor decides.** You propose and draft; only their words for a specific id accept or reject it.
2. **Nothing invented.** No statistics, quotes or course facts you cannot point to. Constructed examples are labelled. The instructor's own AI use is theirs to write.
3. **The discipline's own work.** Every suggestion uses this course's content. A suggestion that would fit any course unchanged is not done.
4. **The tool builds, not you.** Changes go into `plan.json` and drafts; `./arc apply` writes Canvas files. Never edit course XML by hand.
5. **Private by default.** Course exports hold names and email addresses. Work folders stay outside this repository and out of git.

When working on the repository itself:

- Run `python3 -m unittest discover tests` after any change to `scripts/` or `templates/`.
- A new op needs: a method in `scripts/cartridge.py` (surgical text edits, deterministic ids), a branch in `cmd_apply`, a rule in `scripts/plan.py`, a row in `docs/plan-format.md` and `docs/imscc.md`, and a test.
- A new move needs: a template in `templates/`, a row in `docs/framework.md` section 4, its value in `plan.FRAMEWORK`, and guidance in `skills/suggest/SKILL.md`.
- Test fixtures are constructed. Real course exports never go into `tests/`.
