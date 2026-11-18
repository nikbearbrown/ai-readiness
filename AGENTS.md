# AGENTS.md: ai-readiness

For Codex and other coding agents. This folder audits a course for AI readiness, writes suggestions for the course team, and turns the ones they accept into implementation briefs and a new Canvas export.

When asked to audit a course, make a course AI ready, prepare a course for AI-ready certification, or add AI activities, assessments, policies, Frictional logs or Glimmers to a course: read `SKILL.md` and follow it. It routes to `skills/audit`, `skills/suggest`, `skills/decide` and `skills/build`. The framework is `docs/framework.md` (its six readiness questions are the lens); institutional standards are optional profiles in `docs/standards/`; the plan format is `docs/plan-format.md`.

**If you were handed an `implement.md`:** it is your brief. Do exactly what it lists, check each item against its *Done when*, and report what you could not check.

Commands: `./arc help`. Python 3.9 or newer, standard library only.

Never edit a course's XML by hand: write suggestions into `arc/plan.json` and let `./arc apply` build them. Never accept a suggestion without the course team's own words for that id. Never write the instructor's own AI-use statement. Never upload or import anything.
