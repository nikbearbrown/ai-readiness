"""Turn a course into things people and agents can read: the map, and plain text per module."""
import os
import re
import shutil

from cartridge import Course, CourseError, SYLLABUS, slugify
from mdhtml import html_to_text

KIND = {"WikiPage": "page", "Assignment": "assignment", "DiscussionTopic": "discussion",
        "Quizzes::Quiz": "quiz", "ContextModuleSubHeader": "heading", "ExternalUrl": "link",
        "ContextExternalTool": "tool", "Attachment": "file"}


def course_map(c, ids=True):
    lines = ["# %s" % (c.title or "(untitled course)"), ""]
    lines.append("%d modules, %d module items, %d pages (%d not in any module), %d assignments, %d discussions, "
                 "%d announcements, %d quizzes, %d rubrics, %d assignment groups."
                 % (len(c.modules), sum(len(m["items"]) for m in c.modules), len(c.pages),
                    sum(1 for p in c.pages if p not in c.where), len(c.assignments),
                    sum(1 for t in c.topics.values() if t["kind"] != "announcement"),
                    sum(1 for t in c.topics.values() if t["kind"] == "announcement"),
                    len(c.quizzes), len(c.rubrics), len(c.groups)))
    lines.append("")
    for n, m in enumerate(c.modules, 1):
        state = "" if m["state"] == "active" else " (%s)" % m["state"]
        lines.append("## %d. %s%s%s" % (n, m["title"], state, "  `%s`" % m["id"] if ids else ""))
        if not m["items"]:
            lines.append("  (empty)")
        for it in m["items"]:
            kind = KIND.get(it["type"], it["type"] or "item")
            extra = ""
            if it["ref"] in c.assignments:
                a = c.assignments[it["ref"]]
                extra = ", %g pts%s" % (a["points"], ", rubric" if a["rubric"] else "")
            elif it["ref"] in c.topics and c.topics[it["ref"]].get("points") is not None:
                extra = ", graded %g pts" % c.topics[it["ref"]]["points"]
            st = "" if it["state"] in ("active", "") else ", " + it["state"]
            pad = "  " * (it["indent"] + 1)
            lines.append("%s- [%s] %s%s%s%s" % (pad, kind, it["title"], extra, st, "  `%s`" % it["ref"] if ids and it["ref"] else ""))
        lines.append("")
    outside = [a for a in c.assignments.values() if a["id"] not in c.where]
    if outside:
        lines.append("## Assignments not in any module")
        for a in outside:
            lines.append("- %s, %g pts, %s%s%s" % (a["title"], a["points"], a["state"], ", rubric" if a["rubric"] else "",
                                                  "  `%s`" % a["id"] if ids else ""))
        lines.append("")
    gtopics = [t for t in c.topics.values() if t["kind"] != "announcement" and t["id"] not in c.where]
    if gtopics:
        lines.append("## Discussions not in any module")
        for t in gtopics:
            lines.append("- %s%s" % (t["title"], "  `%s`" % t["id"] if ids else ""))
        lines.append("")
    if c.groups:
        lines.append("## Assignment groups")
        for g in c.groups:
            lines.append("- %s, weight %s  `%s`" % (g["title"], g["weight"], g["id"]))
        lines.append("")
    if c.rubrics:
        lines.append("## Rubrics")
        users = {}
        for a in list(c.assignments.values()) + list(c.topics.values()):
            if a.get("rubric"):
                users.setdefault(a["rubric"], []).append(a["title"])
        for r in c.rubrics.values():
            lines.append("- %s, %g pts, %d criteria, used by %d  `%s`" % (r["title"], r["points"], len(r["criteria"]),
                                                                        len(users.get(r["id"], [])), r["id"]))
        lines.append("")
    return "\n".join(lines)


def item_text(c, it):
    ref = it.get("ref")
    if ref in c.pages:
        p = c.pages[ref]
        try:
            body = html_to_text(_body(c.store.read(p["href"])))
        except CourseError:
            body = "(file missing)\n"
        return "## [page] %s\n`%s` · %s\n\n%s" % (p["title"], ref, p.get("state", ""), body)
    if ref in c.assignments:
        a = c.assignments[ref]
        try:
            body = html_to_text(_body(c.store.read(a["href"])))
        except CourseError:
            body = "(file missing)\n"
        head = "## [assignment] %s\n`%s` · %g points · %s · submit: %s%s%s\n" % (
            a["title"], ref, a["points"], a["state"], a["submission"] or "-",
            " (file types: %s)" % a["extensions"] if a.get("extensions") else "",
            " · due %s" % a["due"] if a["due"] else "")
        return head + "\n" + body + rubric_text(c, a.get("rubric"))
    if ref in c.topics:
        t = c.topics[ref]
        graded = " · graded, %g points" % t["points"] if t.get("points") is not None else ""
        return "## [discussion] %s\n`%s`%s\n\n%s%s" % (t["title"], ref, graded, html_to_text(t["text"]), rubric_text(c, t.get("rubric")))
    if ref in c.quizzes:
        q = c.quizzes[ref]
        pts = " · %g points" % q["points"] if q.get("points") is not None else ""
        return "## [quiz] %s\n`%s`%s\n\n%s\n(Quiz questions are not extracted.)\n" % (q["title"], ref, pts, html_to_text(q["description"]))
    if it.get("type") == "ContextModuleSubHeader":
        return "### — %s —\n" % it["title"]
    return "## [%s] %s\n" % (KIND.get(it.get("type"), "item"), it.get("title", ""))


def rubric_text(c, rid):
    if not rid or rid not in c.rubrics:
        return ""
    r = c.rubrics[rid]
    lines = ["", "**Rubric: %s (%g points)**" % (r["title"], r["points"])]
    for cr in r["criteria"]:
        lines.append("- %s (%g): %s" % (cr["description"], cr["points"], "; ".join(
            "%s %g" % (x["description"], x["points"]) for x in cr["ratings"])))
    return "\n".join(lines) + "\n"


def _body(t):
    m = re.search(r"<body[^>]*>(.*)</body>", t, re.S | re.I)
    return m.group(1) if m else t


def write_text(c, work):
    """Write <work>/arc/text/: course.md (the map), syllabus.md, one file per module, assignments.md,
    and unplaced/ for pages in no module. Announcements are left out on purpose (they hold names and
    addresses and say little about course design)."""
    out = os.path.join(work, "arc", "text")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "modules"))
    with open(os.path.join(out, "course.md"), "w", encoding="utf-8") as f:
        f.write(course_map(c))
    try:
        syl = html_to_text(_body(c.store.read(SYLLABUS)))
    except CourseError:
        syl = "(no syllabus in this export)\n"
    with open(os.path.join(out, "syllabus.md"), "w", encoding="utf-8") as f:
        f.write("# Syllabus\n\n" + syl)
    index = ["# Text of the course", "", "| File | Module | Items | Words |", "|---|---|---|---|"]
    for n, m in enumerate(c.modules, 1):
        name = "modules/%03d-%s.md" % (n, slugify(m["title"], 40))
        body = ["# %s" % m["title"], "Position %d in Canvas · `%s` · %s" % (n, m["id"], m["state"]), ""]
        body += [item_text(c, it) for it in m["items"]]
        text = "\n".join(body)
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(text)
        index.append("| %s | %s | %d | %d |" % (name, m["title"].replace("|", "/"), len(m["items"]), len(text.split())))
    a_text = ["# All assignments and graded discussions", ""]
    for a in c.assignments.values():
        a_text.append(item_text(c, {"ref": a["id"]}))
    for t in c.topics.values():
        if t["kind"] != "announcement" and t.get("points") is not None:
            a_text.append(item_text(c, {"ref": t["id"]}))
    with open(os.path.join(out, "assignments.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(a_text))
    unplaced = [p for p in c.pages.values() if p["id"] not in c.where]
    if unplaced:
        os.makedirs(os.path.join(out, "unplaced"))
        lst = ["# Pages in no module (%d)" % len(unplaced), "",
               "Students reach these only through links. Text is in unplaced/<file>.md.", ""]
        for p in unplaced:
            fn = os.path.splitext(os.path.basename(p["href"]))[0] + ".md"
            with open(os.path.join(out, "unplaced", fn), "w", encoding="utf-8") as f:
                f.write(item_text(c, {"ref": p["id"]}))
            lst.append("- %s (%s) → unplaced/%s" % (p["title"], p.get("state", ""), fn))
        with open(os.path.join(out, "unplaced.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lst) + "\n")
        index.append("| unplaced.md | pages in no module | %d | |" % len(unplaced))
    ann = [t for t in c.topics.values() if t["kind"] == "announcement"]
    if ann:
        lines = ["# Announcements (%d)" % len(ann), "",
                 "Announcements do not count for Edge standards (the certifier reads the syllabus and modules), but they "
                 "often hold the course's real policies and corrections. They also hold names and addresses: keep private.", ""]
        for t in ann:
            lines += ["## %s" % t["title"], "`%s`" % t["id"], "", html_to_text(t["text"]), ""]
        with open(os.path.join(out, "announcements.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        index.append("| announcements.md | announcements | %d | |" % len(ann))
    nb = write_notebooks(c, out)
    if nb:
        index.append("| notebooks/ | %d Jupyter notebooks from the course files (Markdown and code cells) | | |" % nb)
    index += ["", "Also: course.md (map), syllabus.md, assignments.md (every graded item with its rubric)."]
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index) + "\n")
    return out


def write_notebooks(c, out):
    """Course files that are Jupyter notebooks hold the real tasks in many courses. Write their cells as text."""
    import json
    names = sorted(n for n in c.store.names() if n.lower().endswith(".ipynb"))
    if not names:
        return 0
    d = os.path.join(out, "notebooks")
    os.makedirs(d, exist_ok=True)
    seen = {}
    listing = []
    for name in names:
        try:
            nb = json.loads(c.store.read_bytes(name).decode("utf-8", "replace"))
        except (ValueError, CourseError):
            continue
        digest = hash(json.dumps(nb.get("cells", []), sort_keys=True))
        base = slugify(os.path.splitext(os.path.basename(name))[0], 50)
        if digest in seen:
            continue
        seen[digest] = name
        users = linked_from(c, name)
        lines = ["# %s" % os.path.basename(name), "`%s`" % name,
                 ("Linked from: " + "; ".join(users)) if users else
                 "Not linked from any page, assignment or discussion (an older or spare copy?)", ""]
        for cell in nb.get("cells", []):
            src = "".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else (cell.get("source") or "")
            if cell.get("cell_type") == "code":
                lines += ["```python", src.rstrip(), "```", ""]
            else:
                lines += [src.rstrip(), ""]
        fn = base + ".md"
        k = 2
        while os.path.exists(os.path.join(d, fn)):
            fn = "%s-%d.md" % (base, k)
            k += 1
        with open(os.path.join(d, fn), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        listing.append("- %s%s" % (fn, " ← " + "; ".join(users) if users else " (not linked)"))
    with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Notebooks\n\n" + "\n".join(listing) + "\n")
    return len(seen)


def raw_html_items(c):
    """[(label, raw html)] for the syllabus, pages, assignments and discussions, for link searches."""
    out = []
    try:
        out.append(("syllabus", c.store.read(SYLLABUS)))
    except CourseError:
        pass
    for p in c.pages.values():
        try:
            out.append(("page %s" % p["title"], c.store.read(p["href"])))
        except CourseError:
            pass
    for a in c.assignments.values():
        try:
            out.append(("assignment %s" % a["title"], c.store.read(a["href"])))
        except CourseError:
            pass
    for t in c.topics.values():
        out.append(("%s %s" % ("announcement" if t["kind"] == "announcement" else "discussion", t["title"]), t["text"]))
    return out


_RAW_CACHE = {}


def linked_from(c, name):
    from urllib.parse import quote
    key = id(c)
    if key not in _RAW_CACHE:
        _RAW_CACHE.clear()
        _RAW_CACHE[key] = raw_html_items(c)
    rel = name[len("web_resources/"):] if name.startswith("web_resources/") else name
    forms = {rel, quote(rel), quote(rel, safe="/"), os.path.basename(rel), quote(os.path.basename(rel))}
    return [label for label, h in _RAW_CACHE[key] if any(f in h for f in forms if len(f) > 6)][:6]
