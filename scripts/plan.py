"""plan.json: load, check, decide, and render plan.md. See docs/plan-format.md."""
import json
import os
import re

STATUSES = ("proposed", "accepted", "rejected", "revise")
OPS = {
    "add_module": {"title"},
    "add_page": {"module", "title", "body"},
    "add_assignment": {"module", "title", "body"},
    "add_discussion": {"module", "title", "body"},
    "edit_syllabus": {"body"},
    "edit_page": {"page", "body"},
    "edit_assignment": {"assignment"},
    "edit_discussion": {"discussion"},
}
PLACEHOLDER = re.compile(r"\{\{[^}]*\}\}|^\s*\[[^\]\n]{8,}\]\s*$", re.M)
MODES = ("append", "insert_after", "insert_before", "replace_section")
FRAMEWORK = ("policy", "objective", "phase-gate", "conduct", "glimmer", "frictional", "planted-flaw",
             "sign-off", "process-criteria", "module-assessments", "relative-quartile", "confession",
             "verb-audit", "correction", "housekeeping")
EDGE = ("E1", "E2", "E3", "E4", "E5")
DIMS = ("D1", "D2", "D3", "D4")
# The framework's six readiness questions (docs/framework.md section 2). Institution-neutral.
READINESS = {
    "R1": "Clear rules for AI use and disclosure",
    "R2": "Students attempt the learning first",
    "R3": "Hands-on AI work in the discipline",
    "R4": "Students judge and verify AI output",
    "R5": "The process is recorded and graded",
    "R6": "Assessment shows learning AI cannot fake",
}
MOVE_READINESS = {
    "policy": ["R1"], "objective": [], "phase-gate": ["R2"], "conduct": ["R3", "R4"],
    "glimmer": ["R3", "R4", "R5"], "frictional": ["R5"], "planted-flaw": ["R4", "R6"], "sign-off": ["R4", "R5"],
    "process-criteria": ["R5"], "module-assessments": ["R2", "R6"], "relative-quartile": ["R6"],
    "confession": ["R4", "R5"], "verb-audit": ["R4"], "correction": [], "housekeeping": [],
}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def profiles():
    """Institutional standards profiles from docs/standards/*.json: {id: {...}}."""
    out = {}
    d = os.path.join(ROOT, "docs", "standards")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    p = json.load(fh)
                out[p["id"]] = p
    return out


def readiness_of(s):
    """The readiness questions a suggestion serves: its own list, or derived from its framework moves."""
    if s.get("readiness"):
        return list(s["readiness"])
    out = []
    for m in s.get("framework") or []:
        for r in MOVE_READINESS.get(m, []):
            if r not in out:
                out.append(r)
    return sorted(out)


def standards_of(s):
    """Institutional standard ids a suggestion meets ('standards', or the older 'edge' field)."""
    return list(s.get("standards") or s.get("edge") or [])


def is_advice(s):
    return not s.get("ops")
SUBMISSION_TYPES = ("online_text_entry", "online_upload", "online_url", "external_tool", "none",
                    "on_paper", "media_recording", "discussion_topic")


def plan_path(work):
    return os.path.join(work, "arc", "plan.json")


def load(work):
    p = plan_path(work)
    if not os.path.exists(p):
        raise SystemExit("No plan at %s. The suggest step writes it (skills/suggest/SKILL.md)." % p)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(work, plan):
    with open(plan_path(work), "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
        f.write("\n")


def find(plan, sid):
    for s in plan.get("suggestions", []):
        if s.get("id") == sid:
            return s
    raise SystemExit("No suggestion %s in the plan." % sid)


def check(work, plan, course=None):
    """Return a list of (level, sid, message). level is FAIL or WARN."""
    out = []
    seen = set()
    drafts = os.path.join(work, "arc")
    for s in plan.get("suggestions", []):
        sid = s.get("id", "?")
        if not re.fullmatch(r"S\d{2,}", sid):
            out.append(("FAIL", sid, "id must look like S01"))
        if sid in seen:
            out.append(("FAIL", sid, "duplicate id"))
        seen.add(sid)
        for k in ("title", "why", "status"):
            if not s.get(k):
                out.append(("FAIL", sid, "missing %s" % k))
        if is_advice(s) and not s.get("advice"):
            out.append(("FAIL", sid, "has no ops; an advice-only suggestion needs an 'advice' text saying what the "
                                     "course team would do"))
        for v in s.get("readiness") or []:
            if v not in READINESS:
                out.append(("WARN", sid, "readiness value %r is not one of %s" % (v, ", ".join(READINESS))))
        if s.get("status") not in STATUSES:
            out.append(("FAIL", sid, "status must be one of %s" % ", ".join(STATUSES)))
        prof = profiles().get((plan.get("course") or {}).get("standards") or "northeastern-edge", {})
        std_ids = tuple(x["id"] for x in prof.get("standards", [])) or EDGE
        for k, allowed in (("framework", FRAMEWORK), ("edge", EDGE), ("standards", std_ids), ("supports", std_ids),
                           ("dimensions", DIMS)):
            for v in s.get(k) or []:
                if v not in allowed:
                    out.append(("WARN", sid, "%s value %r is not one of %s" % (k, v, ", ".join(allowed))))
        if s.get("level") not in ("literacy", "fluency", None):
            out.append(("WARN", sid, "level should be literacy or fluency"))
        ids = {x.get("id") for x in plan.get("suggestions", [])}
        for r in s.get("requires") or []:
            if r not in ids:
                out.append(("FAIL", sid, "requires %s, which is not in the plan" % r))
            elif s.get("status") == "accepted" and find(plan, r).get("status") != "accepted":
                out.append(("WARN", sid, "is accepted but requires %s, which is %s; apply will refuse"
                            % (r, find(plan, r).get("status"))))
        if s.get("status") in ("accepted", "proposed"):
            for k, n in placeholders(work, s):
                out.append(("WARN", sid, "%s still has %d unfilled slot(s) or instructor prompt(s); they will appear "
                                         "in Canvas as written" % (k, n)))
        for j, op in enumerate(s.get("ops") or [], 1):
            name = op.get("op")
            where = "%s op %d (%s)" % (sid, j, name)
            if name not in OPS:
                out.append(("FAIL", sid, "op %d: unknown op %r" % (j, name)))
                continue
            for k in OPS[name]:
                if not op.get(k):
                    out.append(("FAIL", sid, "%s: missing %s" % (where, k)))
            if op.get("mode") and op["mode"] not in MODES:
                out.append(("FAIL", sid, "%s: mode must be one of %s" % (where, ", ".join(MODES))))
            if op.get("mode") in ("insert_after", "insert_before", "replace_section") and not op.get("heading"):
                out.append(("FAIL", sid, "%s: mode %s needs a heading" % (where, op["mode"])))
            for k in ("body", "rubric", "add_criteria"):
                v = op.get(k)
                if isinstance(v, str):
                    full = os.path.join(drafts, v)
                    if not os.path.exists(full):
                        out.append(("FAIL", sid, "%s: %s file not found: arc/%s" % (where, k, v)))
                    elif k != "body":
                        out.extend(("FAIL", sid, "%s: %s" % (where, m)) for m in check_rubric(full))
            for t in op.get("submission_types") or []:
                if t not in SUBMISSION_TYPES:
                    out.append(("FAIL", sid, "%s: unknown submission type %r" % (where, t)))
            if course is not None and s.get("status") != "rejected":
                for k in ("module", "page", "assignment", "discussion"):
                    ref = op.get(k)
                    if ref and name != "add_module":
                        msg = course.resolve_message(k, ref, plan, s, j)
                        if msg:
                            out.append(("FAIL", sid, "%s: %s" % (where, msg)))
                if op.get("group"):
                    try:
                        if course.group(op["group"]) is None:
                            out.append(("WARN", sid, "%s: no assignment group %r; apply will create it with weight 0"
                                        % (where, op["group"])))
                    except Exception as e:  # ambiguous name
                        out.append(("FAIL", sid, "%s: %s" % (where, e)))
    return out


def placeholders(work, s):
    """[(draft file, count)] for drafts of suggestion s that still hold {{slots}} or [bracketed prompts]."""
    out = []
    for op in s.get("ops") or []:
        v = op.get("body")
        if isinstance(v, str):
            p = os.path.join(work, "arc", v)
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    text = re.sub(r"<!--.*?-->", "", f.read(), flags=re.S)
                n = len(PLACEHOLDER.findall(text))
                if n:
                    out.append((v, n))
    return out


def check_rubric(path):
    problems = []
    try:
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
    except (OSError, ValueError) as e:
        return ["rubric is not valid JSON: %s" % e]
    crit = r.get("criteria")
    if not crit:
        return ["rubric has no criteria"]
    for c in crit:
        if not c.get("description"):
            problems.append("a criterion has no description")
        ratings = c.get("ratings") or []
        if len(ratings) < 2:
            problems.append("criterion %r needs at least two ratings" % c.get("description"))
        pts = [x.get("points") for x in ratings]
        if any(not isinstance(p, (int, float)) for p in pts):
            problems.append("criterion %r has a rating without numeric points" % c.get("description"))
        elif c.get("points") != max(pts):
            problems.append("criterion %r: points (%s) should equal its top rating (%s)"
                            % (c.get("description"), c.get("points"), max(pts)))
    return problems


def rubric_total(path):
    with open(path, encoding="utf-8") as f:
        return sum(c.get("points", 0) for c in json.load(f).get("criteria", []))


def render_md(work, plan, course=None):
    c = plan.get("course", {})
    sug = plan.get("suggestions", [])
    counts = {k: sum(1 for s in sug if s.get("status") == k) for k in STATUSES}
    lines = ["# AI readiness plan: %s" % c.get("title", "(course)"), ""]
    lines.append("%d suggestions: %d proposed, %d accepted, %d rejected, %d to revise."
                 % (len(sug), counts["proposed"], counts["accepted"], counts["rejected"], counts["revise"]))
    if c.get("audience") or c.get("level"):
        lines.append("")
        lines.append("Audience: %s Target level: %s." % ((c.get("audience") or "not stated.").rstrip(".") + ".", c.get("level", "not set")))
    lines += ["", "To decide: `./arc accept <work> S01 S03`, `./arc reject <work> S02 --note \"...\"`, "
              "`./arc revise <work> S04 --note \"...\"`. Or tell your agent in plain words.", ""]
    lines += ["| Id | Status | Suggestion | Module | Edge | Effort |", "|---|---|---|---|---|---|"]
    for s in sug:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            s.get("id"), s.get("status"), s.get("title", "").replace("|", "/"),
            name_of(course, "module", s.get("module")).replace("|", "/") if s.get("module") else "course-wide",
            ", ".join(s.get("edge") or []) or "-", s.get("effort", "-")))
    for s in sug:
        lines += ["", "---", "", "## %s · %s" % (s.get("id"), s.get("title")), ""]
        lines.append("**Status:** %s%s" % (s.get("status"), " (from the instructor)" if s.get("origin") == "instructor" else ""))
        if s.get("note"):
            lines.append("**Instructor note:** %s" % s["note"])
        lines.append("**Why:** %s" % s.get("why", ""))
        tags = []
        if s.get("framework"):
            tags.append("framework: " + ", ".join(s["framework"]))
        if s.get("edge"):
            tags.append("Edge: " + ", ".join(s["edge"]))
        if s.get("dimensions"):
            tags.append("dimensions: " + ", ".join(s["dimensions"]))
        if s.get("level"):
            tags.append("level: " + s["level"])
        if tags:
            lines.append("**Tags:** " + "; ".join(tags))
        if s.get("requires"):
            lines.append("**Needs:** %s (accept those too, or this one will not build)" % ", ".join(s["requires"]))
        lines += ["", "**What it changes:**", ""]
        for op in s.get("ops", []):
            lines.append("- " + describe_op(op, course))
        for op in s.get("ops", []):
            for k in ("body", "rubric", "add_criteria"):
                v = op.get(k)
                if isinstance(v, str):
                    full = os.path.join(work, "arc", v)
                    if os.path.exists(full):
                        with open(full, encoding="utf-8") as f:
                            body = f.read().strip()
                        if k != "body":
                            body = rubric_md(json.loads(body))
                        else:
                            body = re.sub(r"<!--.*?-->\s*", "", body, flags=re.S).strip()
                        lines += ["", "<details><summary>%s (arc/%s)</summary>" % ("Rubric" if k != "body" else "Text", v), "", body, "", "</details>"]
    return "\n".join(lines) + "\n"


def name_of(course, kind, ref):
    """A title for an identifier, for people. Falls back to the reference itself."""
    if not ref or course is None:
        return ref or ""
    try:
        if kind == "discussion":
            return course._one("discussion", ref, list(course.topics.values()))["title"]
        return getattr(course, kind)(ref)["title"]
    except Exception:
        return ref


def describe_op(op, course=None):
    n = op.get("op")
    op = dict(op)
    for k in ("module", "page", "assignment", "discussion"):
        if op.get(k):
            op[k] = name_of(course, k, op[k])
    if op.get("after") not in (None, "", "end", "start") and course is not None:
        after = op["after"]
        for m in course.modules:
            for it in m["items"]:
                if after in (it["id"], it["ref"]):
                    after = it["title"]
        op["after"] = after
    pub = "" if op.get("published") else " (unpublished)"
    if n == "add_module":
        return "New module **%s**%s" % (op.get("title"), pub)
    if n in ("add_page", "add_assignment", "add_discussion"):
        kind = n.split("_")[1]
        extra = ""
        if op.get("points"):
            extra = ", %s points" % op["points"]
        if op.get("rubric"):
            extra += ", with rubric"
        where = " after *%s*" % op["after"] if op.get("after") not in (None, "", "end") else ""
        if op.get("after") == "start":
            where = " at the start"
        return "New %s **%s** in module *%s*%s%s%s" % (kind, op.get("title"), op.get("module"), where, extra, pub)
    if n == "edit_syllabus":
        return "Syllabus: %s" % mode_words(op)
    if n == "edit_page":
        return "Page *%s*: %s" % (op.get("page"), mode_words(op))
    if n == "edit_assignment":
        parts = []
        if op.get("body"):
            parts.append(mode_words(op))
        if op.get("add_criteria"):
            parts.append("add rubric criteria")
        if op.get("points") is not None:
            parts.append("points to %s" % op["points"])
        if op.get("submission_types"):
            parts.append("submission types to %s" % ", ".join(op["submission_types"]))
        if op.get("allowed_extensions") is not None:
            parts.append("allowed file types to %s" % (op["allowed_extensions"] or "any"))
        return "Assignment *%s*: %s" % (op.get("assignment"), ", ".join(parts))
    if n == "edit_discussion":
        parts = []
        if op.get("body"):
            parts.append(mode_words(op))
        if op.get("add_criteria"):
            parts.append("add rubric criteria")
        if op.get("points") is not None:
            parts.append("points to %s" % op["points"])
        return "Discussion *%s*: %s" % (op.get("discussion"), ", ".join(parts))
    return n


def mode_words(op):
    m = op.get("mode", "append")
    if m == "append":
        return "add a section at the end"
    if m == "insert_after":
        return "insert after the section \u201c%s\u201d" % op.get("heading")
    if m == "insert_before":
        return "insert before the heading \u201c%s\u201d" % op.get("heading")
    return "replace the section \u201c%s\u201d" % op.get("heading")


def rubric_md(r):
    rows = ["**%s**" % r.get("title", "Rubric"), "", "| Criterion | Points | Ratings |", "|---|---|---|"]
    for c in r.get("criteria", []):
        ratings = "; ".join("%s (%s)" % (x.get("description"), x.get("points")) for x in c.get("ratings", []))
        rows.append("| %s | %s | %s |" % (c.get("description"), c.get("points"), ratings))
    return "\n".join(rows)
