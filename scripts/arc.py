"""ai-readiness: audit a course for AI readiness, plan changes with the instructor, build a new .imscc.

    ./arc help
"""
import argparse
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import cartridge as cg          # noqa: E402
import checks                   # noqa: E402
import plan as pl               # noqa: E402
import readout                  # noqa: E402
import report as rp             # noqa: E402
from mdhtml import md_to_html   # noqa: E402

HELP = """ai-readiness  ·  ./arc <command>

Suggestions (for people):
  ./arc open <course.imscc | folder> <work> [--standards northeastern-edge]
                                               unpack, write the course as text, run the automatic check
  ./arc check <work>                           re-run the automatic check  ->  <work>/arc/check.md
  (agent)  skills/audit, then skills/suggest   ->  <work>/arc/audit.md, plan.json, drafts/
  ./arc plan <work> [--try]                    check the plan; --try builds it in memory and reports what would happen
  ./arc report <work>                          ->  <work>/arc/suggestions.md, the document for the course team
  ./arc feedback <work> <their-copy.md>        read their decisions and comments back into the plan
  ./arc accept|reject|revise|reset <work> S01 ...   or record decisions directly

Implementation (for coding agents):
  ./arc implement <work>                       ->  <work>/arc/implement.md, briefs for everything accepted
  ./arc apply <work>                           build the accepted Canvas changes into <work>/arc/build/
  ./arc validate <work>                        consistency checks Canvas import relies on
  ./arc pack <work> <new.imscc>                write the new course export

Many courses:
  ./arc batch <exports-folder> <runs-folder> [--standards ...]   open and check every .imscc, index in README.md

Also:
  ./arc map <work>          modules and items with identifiers (use these in the plan)
  ./arc text <work>         rewrite <work>/arc/text/ (the course as plain text)
  ./arc new-plan <work>     start an empty plan.json and drafts/ folder
  ./arc status <work>       where this course is in the loop
  ./arc diff <a.imscc> <b.imscc>   what changed between two exports
  ./arc install             make the skill available to Claude Code in every project

Nothing here uploads anything. Import the new .imscc into a Canvas sandbox or a new course shell first.
"""


def fail(msg):
    print("✗ " + msg)
    sys.exit(1)


def store(work, overlay=True):
    try:
        return cg.Store(work, overlay=overlay)
    except cg.CourseError as e:
        fail(str(e))


def course(work, overlay=False):
    try:
        return cg.Course(store(work, overlay))
    except cg.CourseError as e:
        fail(str(e))


def get_profile(name):
    if not name:
        return None
    profs = pl.profiles()
    if name not in profs:
        fail("No standards profile %r. Available: %s (docs/standards/)." % (name, ", ".join(profs) or "none"))
    return profs[name]


def work_profile(work, override=None):
    """The work folder's standards profile: --standards wins and is remembered in source.json."""
    meta_path = os.path.join(work, "arc", "source.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    if override:
        get_profile(override)
        meta["standards"] = override
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return get_profile(meta.get("standards"))


def signal_line(f):
    s = "readiness " + " ".join("%s %s" % (k, f["readiness"][k]["verdict"]) for k in sorted(f["readiness"]))
    if f.get("standards"):
        s += " · %s " % f["standards"]["short"] + " ".join("%s %s" % (k, v["verdict"]) for k, v in f["standards"]["results"].items())
    return s


def cmd_help(a):
    print(HELP)


def cmd_open(a):
    try:
        st = cg.open_course(a.source, a.work, a.title)
        c = cg.Course(st)
    except cg.CourseError as e:
        fail(str(e))
    readout.write_text(c, a.work)
    f = checks.write(c, a.work, work_profile(a.work, a.standards))
    meta = st.meta
    print("Opened %s" % (c.title or a.source))
    if meta["kind"] == "zip":
        print("  %d entries; media left in the original export (%d files): %s" % (meta["entries"], meta["media_left_in_zip"], meta["path"]))
        print("  Keep that file where it is until you have packed the new course.")
    elif meta["kind"] == "built":
        print("  Built a Canvas course from the folder: one module per subfolder, one page per text file.")
    fx = f["facts"]
    print("  %d modules, %d pages (%d in no module), %d assignments, %d quizzes, %d rubrics"
          % (fx["modules"], fx["pages"], fx["pages_in_no_module"], fx["assignments"], fx["quizzes"], fx["rubrics"]))
    print("  Automatic check: " + signal_line(f))
    w = os.path.abspath(a.work)
    print("\nRead next:\n  %s/arc/check.md\n  %s/arc/text/README.md" % (w, w))
    print("Then ask your agent to run the audit (skills/audit/SKILL.md).")


def cmd_map(a):
    print(readout.course_map(course(a.work), ids=not a.no_ids))


def cmd_text(a):
    out = readout.write_text(course(a.work), a.work)
    print("Wrote %s" % out)


def cmd_check(a):
    f = checks.write(course(a.work), a.work, work_profile(a.work, a.standards))
    if a.json:
        print(json.dumps(f, indent=2, ensure_ascii=False))
        return
    print(checks.report_md(f).split("\n## ")[0])
    print("Full report: %s" % os.path.join(os.path.abspath(a.work), "arc", "check.md"))


def cmd_new_plan(a):
    p = pl.plan_path(a.work)
    if os.path.exists(p):
        fail("A plan already exists: %s" % p)
    c = course(a.work)
    os.makedirs(os.path.join(a.work, "arc", "drafts"), exist_ok=True)
    pl.save(a.work, {"version": 1, "course": {"title": c.title, "audience": "", "level": "", "discipline": ""},
                     "suggestions": []})
    print("Started %s and %s/" % (p, os.path.join(a.work, "arc", "drafts")))


def _plan_and_course(a):
    plan = pl.load(a.work)
    c = course(a.work)
    return plan, c


def cmd_plan(a):
    plan, c = _plan_and_course(a)
    problems = pl.check(a.work, plan, c)
    md = pl.render_md(a.work, plan, c)
    out = os.path.join(a.work, "arc", "plan.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    sug = plan.get("suggestions", [])
    counts = {k: sum(1 for s in sug if s.get("status") == k) for k in pl.STATUSES}
    print("%d suggestions: %s" % (len(sug), ", ".join("%d %s" % (v, k) for k, v in counts.items() if v)))
    for level, sid, msg in problems:
        print("  %s %s: %s" % (level, sid, msg))
    nf = sum(1 for p in problems if p[0] == "FAIL")
    print("FAIL %d  WARN %d" % (nf, len(problems) - nf))
    print("Instructor's copy: %s" % os.path.abspath(out))
    if a.try_build and not nf:
        nf += cmd_try(a, plan, c)
    if nf:
        sys.exit(1)


def _decide(a, status):
    plan = pl.load(a.work)
    for sid in a.ids:
        s = pl.find(plan, sid)
        s["status"] = status
        if a.note is not None:
            s["note"] = a.note
        print("%s → %s" % (sid, status))
    pl.save(a.work, plan)
    try:
        c = cg.Course(cg.Store(a.work, overlay=False))
    except cg.CourseError:
        c = None
    with open(os.path.join(a.work, "arc", "plan.md"), "w", encoding="utf-8") as f:
        f.write(pl.render_md(a.work, plan, c))


def cmd_accept(a):
    _decide(a, "accepted")


def cmd_reject(a):
    _decide(a, "rejected")


def cmd_revise(a):
    if not a.note:
        fail("Say what to change: ./arc revise <work> S04 --note \"...\"")
    _decide(a, "revise")


def cmd_reset(a):
    _decide(a, "proposed")


def _body(work, rel):
    if not rel:
        return None
    p = os.path.join(work, "arc", rel)
    with open(p, encoding="utf-8") as f:
        t = f.read()
    if rel.lower().endswith((".html", ".htm")):
        import re
        m = re.search(r"<body[^>]*>(.*)</body>", t, re.S | re.I)
        return (m.group(1) if m else t).strip()
    return md_to_html(t)


def _rubric(work, rel):
    if not rel:
        return None
    if isinstance(rel, dict):
        return rel
    with open(os.path.join(work, "arc", rel), encoding="utf-8") as f:
        return json.load(f)


def run_ops(ed, work, suggestions, keep_going=False):
    """Apply each suggestion's ops through the Editor. Returns {sid: error or None}. Stops at the first error
    unless keep_going (used by plan --try, which reports every suggestion)."""
    results = {}
    for s in sorted(suggestions, key=lambda s: s["id"]):
        results[s["id"]] = None
        for j, op in enumerate(s["ops"], 1):
            key = "%s:%d:%s" % (s["id"], j, op.get("title") or op.get("page") or op.get("assignment")
                                or op.get("discussion") or op["op"])
            n = len(ed.log)
            try:
                o = op["op"]
                if o == "add_module":
                    ed.add_module(op["title"], op.get("after"), op.get("published", False), key)
                elif o == "add_page":
                    ed.add_page(op["module"], op["title"], _body(work, op["body"]), op.get("after"), op.get("published", False), key)
                elif o == "add_assignment":
                    ed.add_assignment(op["module"], op["title"], _body(work, op["body"]), op.get("points"),
                                      op.get("submission_types"), op.get("group"), _rubric(work, op.get("rubric")),
                                      op.get("after"), op.get("published", False), key)
                elif o == "add_discussion":
                    ed.add_discussion(op["module"], op["title"], _body(work, op["body"]), op.get("points"), op.get("group"),
                                      _rubric(work, op.get("rubric")), op.get("after"), op.get("published", False), key)
                elif o == "edit_syllabus":
                    ed.edit_html(cg.SYLLABUS, op.get("mode", "append"), op.get("heading"), _body(work, op["body"]), "syllabus")
                elif o == "edit_page":
                    p = ed.course.page(op["page"])
                    ed.edit_html(p["href"], op.get("mode", "append"), op.get("heading"), _body(work, op["body"]),
                                 "page %s" % p["title"])
                    ed.refresh()
                elif o == "edit_assignment":
                    ed.edit_assignment(op["assignment"], op.get("mode", "append"), op.get("heading"),
                                       _body(work, op.get("body")), _rubric(work, op.get("add_criteria")), op.get("points"), key,
                                       op.get("submission_types"), op.get("allowed_extensions"))
                elif o == "edit_discussion":
                    ed.edit_discussion(op["discussion"], op.get("mode", "append"), op.get("heading"),
                                       _body(work, op.get("body")), _rubric(work, op.get("add_criteria")), op.get("points"), key)
            except (cg.CourseError, KeyError, OSError, ValueError) as e:
                results[s["id"]] = "op %d (%s): %s" % (j, op.get("op"), e)
                if not keep_going:
                    return results
                break
            for i in range(n, len(ed.log)):
                ed.log[i] = ed.log[i] + (s["id"],)
    return results


def _readable(rel, content):
    import html as _h
    import re as _re
    from mdhtml import html_to_text
    if isinstance(content, bytes):
        return "(binary file)"
    m = _re.search(r'<text texttype="text/html">(.*?)</text>', content, _re.S)
    if m:
        return html_to_text(_h.unescape(m.group(1)))
    if rel.endswith(".html"):
        b = _re.search(r"<body[^>]*>(.*)</body>", content, _re.S | _re.I)
        return html_to_text(b.group(1) if b else content)
    return content


def show_changes(ed, sid):
    """Print, as readable text, what suggestion sid adds to each file, with a little context."""
    import difflib
    files = []
    for e in ed.log:
        if len(e) > 3 and e[3] == sid and e[1] not in files:
            files.append(e[1])
    print("\n--- %s: where the text lands ---" % sid)
    for rel in files:
        if rel.endswith((".xml",)) and "<text texttype" not in (ed.files.get(rel) if isinstance(ed.files.get(rel), str) else ""):
            continue
        new = _readable(rel, ed.files[rel]).splitlines()
        try:
            old = _readable(rel, ed.store.read(rel)).splitlines()
        except cg.CourseError:
            old = []
        print("\n[%s]" % rel)
        if not old:
            print("\n".join("  + " + ln for ln in new[:40]) + ("\n  …" if len(new) > 40 else ""))
            continue
        for g in difflib.SequenceMatcher(None, old, new, autojunk=False).get_grouped_opcodes(2):
            for tag, i1, i2, j1, j2 in g:
                if tag == "equal":
                    for ln in new[j1:j2]:
                        print("    " + ln[:160])
                if tag in ("insert", "replace"):
                    for ln in new[j1:j2]:
                        print("  + " + ln[:160])
            print("    …")


def cmd_try(a, plan, c):
    """Apply every suggestion that is not rejected, in memory, and report what would happen."""
    trial = [s for s in plan.get("suggestions", []) if s.get("status") != "rejected"]
    ed = cg.Editor(store(a.work, overlay=False))
    w0 = 0
    results = run_ops(ed, a.work, trial, keep_going=True)
    print("\nTrial build of %d suggestions (nothing saved):" % len(trial))
    for s in sorted(trial, key=lambda s: s["id"]):
        err = results.get(s["id"])
        files = sorted({e[1] for e in ed.log if len(e) > 3 and e[3] == s["id"]})
        print("  %s %s: %s" % ("FAIL" if err else "ok  ", s["id"], err or "%d files" % len(files)))
    for x in ed.warnings[w0:]:
        print("  WARN " + x)
    for sid in (a.show or []):
        show_changes(ed, sid)
    res = cg.validate(ed)
    nf = sum(1 for r in res if r[0] == "FAIL") + sum(1 for v in results.values() if v)
    for level, msg in res:
        print("  %s %s" % (level, msg))
    print("trial: FAIL %d  WARN %d" % (nf, len(ed.warnings) + len(res) - sum(1 for r in res if r[0] == "FAIL")))
    return nf


def cmd_apply(a):
    plan = pl.load(a.work)
    c = course(a.work)
    problems = [p for p in pl.check(a.work, plan, c) if p[0] == "FAIL"]
    accepted = [s for s in plan.get("suggestions", []) if s.get("status") == "accepted"]
    bad = [p for p in problems if any(p[1] == s["id"] for s in accepted)]
    if bad:
        for level, sid, msg in bad:
            print("  FAIL %s: %s" % (sid, msg))
        fail("Fix the accepted suggestions above first (./arc plan %s)." % a.work)
    if not accepted:
        fail("No accepted suggestions. The instructor decides: ./arc accept %s S01 …" % a.work)
    for s in accepted:
        for r in s.get("requires") or []:
            if pl.find(plan, r).get("status") != "accepted":
                fail("%s needs %s, which is %s. Accept %s too, or revise %s so it stands alone."
                     % (s["id"], r, pl.find(plan, r).get("status"), r, s["id"]))
    for s in accepted:
        for draft, n in pl.placeholders(a.work, s):
            print("  WARN %s: %s still has %d unfilled slot(s) or instructor prompt(s); they will appear in Canvas as written"
                  % (s["id"], draft, n))
    ed = cg.Editor(store(a.work, overlay=False))
    w = a.work
    results = run_ops(ed, w, accepted)
    for sid, err in results.items():
        if err:
            fail("%s %s" % (sid, err))
    files_dir = os.path.join(w, "arc", "files")
    swapped = []
    if os.path.isdir(files_dir):
        names = ed.store.names()
        for dp, _, fn in os.walk(files_dir):
            for name in sorted(fn):
                if name.startswith("."):
                    continue
                full = os.path.join(dp, name)
                rel = os.path.relpath(full, files_dir).replace(os.sep, "/")
                if rel not in names:
                    ed.warnings.append("arc/files/%s does not replace a file in the course (no such path); not included. "
                                       "Fixed files must keep the course file's exact path." % rel)
                    continue
                with open(full, "rb") as fh:
                    ed.write(rel, fh.read(), "fixed course file")
                swapped.append(rel)
    if a.dry_run:
        print("Dry run: %d suggestions, %d file writes, nothing saved." % (len(accepted), len(ed.log)))
        return
    build = os.path.join(w, "arc", "build")
    ed.write_out(build)
    log = ["# Build log", "", "Accepted suggestions applied: %s" % ", ".join(s["id"] for s in accepted), ""]
    for s in sorted(accepted, key=lambda s: s["id"]):
        log.append("## %s · %s" % (s["id"], s["title"]))
        seen = []
        for entry in ed.log:
            if len(entry) > 3 and entry[3] == s["id"] and (entry[0], entry[1]) not in seen:
                seen.append((entry[0], entry[1]))
                log.append("- %s `%s` (%s)" % (entry[0], entry[1], entry[2]))
        log.append("")
    if swapped:
        log += ["## Fixed course files swapped in from arc/files/", ""] + ["- `%s`" % r for r in swapped] + [""]
    if ed.warnings:
        log += ["## Warnings", ""] + ["- " + x for x in ed.warnings]
    with open(os.path.join(w, "arc", "build-log.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("Applied %d suggestions; %d files added or changed → %s" % (len(accepted), len(ed.files), build))
    for x in ed.warnings:
        print("  WARN " + x)
    _report_validation(store(w))


def _report_validation(st):
    res = cg.validate(st)
    nf = sum(1 for r in res if r[0] == "FAIL")
    for level, msg in res:
        print("  %s %s" % (level, msg))
    print("validate: FAIL %d  WARN %d" % (nf, len(res) - nf))
    return nf


def cmd_validate(a):
    if _report_validation(store(a.work)):
        sys.exit(1)


def cmd_pack(a):
    st = store(a.work)
    nf = _report_validation(st)
    if nf and not a.force:
        fail("Not packing a course that fails validation. Fix it, or pass --force to pack anyway.")
    out = cg.pack(st, a.out)
    size = os.path.getsize(out)
    print("Wrote %s (%.1f MB)" % (out, size / 1e6))
    print("Import it in Canvas: Settings → Import Course Content → Canvas Course Export Package.")
    print("Import into a sandbox or a new, empty course shell first. Re-importing into the live course can duplicate")
    print("pages and modules that were created there by hand.")


def cmd_diff(a):
    def entries(p):
        with zipfile.ZipFile(p) as z:
            return {i.filename: (i.CRC, i.file_size) for i in z.infolist() if not i.filename.endswith("/")}
    x, y = entries(a.a), entries(a.b)
    added = sorted(set(y) - set(x))
    removed = sorted(set(x) - set(y))
    changed = sorted(k for k in set(x) & set(y) if x[k] != y[k])
    print("%d added, %d changed, %d removed, %d identical" % (len(added), len(changed), len(removed), len(set(x) & set(y)) - len(changed)))
    for k in added:
        print("  + " + k)
    for k in changed:
        print("  ~ " + k)
    for k in removed:
        print("  - " + k)


def cmd_status(a):
    w = os.path.join(a.work, "arc")
    steps = [("opened", os.path.exists(os.path.join(w, "source.json"))),
             ("automatic check", os.path.exists(os.path.join(w, "check.md"))),
             ("audit written", os.path.exists(os.path.join(w, "audit.md"))),
             ("plan written", os.path.exists(os.path.join(w, "plan.json"))),
             ("built", os.path.isdir(os.path.join(w, "build")))]
    for name, done in steps:
        print("  [%s] %s" % ("x" if done else " ", name))
    if os.path.exists(os.path.join(w, "plan.json")):
        plan = pl.load(a.work)
        sug = plan.get("suggestions", [])
        print("  plan: " + ", ".join("%d %s" % (sum(1 for s in sug if s.get("status") == k), k) for k in pl.STATUSES))


def course_slug(filename):
    """info6205-12345-…-fall-2026-…-export.imscc → info6205-fall-2026."""
    import re
    base = os.path.splitext(os.path.basename(filename))[0].lower()
    code = re.search(r"\b([a-z]{2,5})[-_ ]?(\d{4})\b", base.replace("_", "-"))
    term = re.search(r"(fall|spring|summer|winter)[-_ ]?(\d{4})", base)
    if code and term:
        return "%s%s-%s-%s" % (code.group(1), code.group(2), term.group(1), term.group(2))
    return cg.slugify(base, 50)


def stage(work):
    w = os.path.join(work, "arc")
    if os.path.isdir(os.path.join(w, "build")):
        return "built"
    if os.path.exists(os.path.join(w, "plan.json")):
        sug = pl.load(work).get("suggestions", [])
        acc = sum(1 for s in sug if s.get("status") == "accepted")
        return "planned (%d of %d accepted)" % (acc, len(sug))
    if os.path.exists(os.path.join(w, "audit.md")):
        return "audited"
    return "checked"


def cmd_batch(a):
    """Open and check every .imscc in a folder, each in its own work folder, and write an index."""
    exports = sorted(os.path.join(dp, f) for dp, _, fn in os.walk(a.exports) for f in fn if f.lower().endswith(".imscc"))
    if not exports:
        fail("No .imscc files in %s" % a.exports)
    runs = os.path.abspath(a.runs)
    if os.path.abspath(a.exports) == runs or runs.startswith(os.path.abspath(a.exports) + os.sep):
        fail("Put the runs folder outside the exports folder, so work files never sit next to the exports.")
    os.makedirs(runs, exist_ok=True)
    rows, used = [], set()
    for path in exports:
        slug = course_slug(path)
        n = 2
        while slug in used:
            slug = "%s-%d" % (course_slug(path), n)
            n += 1
        used.add(slug)
        work = os.path.join(runs, slug)
        meta = os.path.join(work, "arc", "source.json")
        if os.path.exists(meta):
            with open(meta, encoding="utf-8") as f:
                same = json.load(f).get("path") == os.path.abspath(path)
            if not same:
                fail("%s already holds a different course. Move it or rename the export." % work)
            print("· %s (already open)" % slug)
        else:
            print("· %s: opening %s" % (slug, os.path.basename(path)))
            try:
                cg.open_course(path, work)
            except cg.CourseError as e:
                print("  ✗ %s" % e)
                rows.append((slug, os.path.basename(path), None, str(e)))
                continue
        try:
            c = cg.Course(cg.Store(work, overlay=False))
            if not os.path.isdir(os.path.join(work, "arc", "text")) or a.again:
                readout.write_text(c, work)
            f = checks.write(c, work, work_profile(work, a.standards))
            rows.append((slug, os.path.basename(path), f, stage(work)))
        except cg.CourseError as e:
            print("  ✗ %s" % e)
            rows.append((slug, os.path.basename(path), None, str(e)))
    lines = ["# AI readiness runs", "", "Exports from `%s`. One work folder per course. Signals from the automatic check "
             "(check = evidence to judge, missing = read and absent, n/s = not in the export); the audit decides."
             % os.path.abspath(a.exports), "",
             "Readiness questions: R1 rules for AI use, R2 attempt first, R3 hands-on AI work, R4 judge and verify, "
             "R5 process recorded and graded, R6 assessment AI cannot fake.", "",
             "| Course | Title | Modules | Graded | R1 | R2 | R3 | R4 | R5 | R6 | Standards | Stage | For people |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for slug, fname, f, st in rows:
        if f is None:
            lines.append("| %s | (%s) | | | | | | | | | | error: %s |" % (slug, fname, st))
            continue
        r = f["readiness"]
        short = {"CHECK": "check", "MISSING": "**missing**", "NOT SUPPLIED": "n/s"}
        std = (" ".join("%s:%s" % (k, short.get(v["verdict"], v["verdict"]).strip("*")[0]) for k, v in f["standards"]["results"].items())
               if f.get("standards") else "")
        people = os.path.join(work, "arc", "suggestions.md")
        lines.append("| [%s](%s/arc/check.md) | %s | %d | %d | %s | %s | %s | %s |" % (
            slug, slug, (f["course"] or fname).replace("|", "/"), f["facts"]["modules"], f["facts"]["graded_items"],
            " | ".join(short.get(r[k]["verdict"], r[k]["verdict"]) for k in sorted(r)), std, st,
            "[suggestions](%s/arc/suggestions.md)" % slug if os.path.exists(people) else ""))
    with open(os.path.join(runs, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines[4:]))
    print("\nIndex: %s" % os.path.join(runs, "README.md"))


def cmd_report(a):
    plan = pl.load(a.work)
    try:
        c = cg.Course(cg.Store(a.work, overlay=False))
    except cg.CourseError:
        c = None
    out = os.path.join(a.work, "arc", "suggestions.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(rp.suggestions_md(a.work, plan, c))
    n = len([s for s in plan.get("suggestions", []) if s.get("status") != "rejected"])
    print("Wrote %s (%d suggestions) for the course team." % (os.path.abspath(out), n))
    if not os.path.exists(os.path.join(a.work, "arc", "audit.md")):
        print("  WARN no audit.md: the document has no summary or standing. Run the audit first (skills/audit).")


def cmd_feedback(a):
    plan = pl.load(a.work)
    with open(a.file, encoding="utf-8") as f:
        fb = rp.parse_feedback(f.read())
    if not fb:
        fail("No suggestions found in %s. Is it a suggestions.md from ./arc report?" % a.file)
    ids = {s["id"] for s in plan.get("suggestions", [])}
    changed, undecided = [], []
    for sid, (status, comment) in sorted(fb.items()):
        if sid not in ids:
            print("  WARN %s is in the file but not in the plan; ignored" % sid)
            continue
        s = pl.find(plan, sid)
        if status is None:
            undecided.append(sid)
            if comment and comment != s.get("note"):
                s["note"] = comment
                changed.append("%s comment" % sid)
            continue
        if status == "revise" and not comment:
            print("  WARN %s: 'change' with no comment; recorded, but ask what to change" % sid)
        if s.get("status") != status or (comment and comment != s.get("note")):
            s["status"] = status
            if comment:
                s["note"] = comment
            changed.append("%s → %s" % (sid, status))
    pl.save(a.work, plan)
    with open(os.path.join(a.work, "arc", "plan.md"), "w", encoding="utf-8") as f:
        f.write(pl.render_md(a.work, plan, None))
    print("Recorded: " + (", ".join(changed) if changed else "nothing new"))
    if undecided:
        print("No decision yet: " + ", ".join(undecided))


def cmd_implement(a):
    plan = pl.load(a.work)
    try:
        c = cg.Course(cg.Store(a.work, overlay=False))
    except cg.CourseError:
        c = None
    out = os.path.join(a.work, "arc", "implement.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(rp.implement_md(a.work, plan, c))
    acc = [s for s in plan.get("suggestions", []) if s.get("status") == "accepted"]
    print("Wrote %s: %d accepted (%d built by arc, %d by hand) for a coding agent."
          % (os.path.abspath(out), len(acc), sum(1 for s in acc if not pl.is_advice(s)), sum(1 for s in acc if pl.is_advice(s))))


def cmd_install(a):
    dest_dir = os.path.expanduser("~/.claude/skills")
    os.makedirs(dest_dir, exist_ok=True)
    link = os.path.join(dest_dir, "ai-readiness")
    if os.path.islink(link) or os.path.exists(link):
        print("Already there: %s → %s" % (link, os.path.realpath(link)))
        return
    os.symlink(ROOT, link)
    print("Linked %s → %s. Claude Code will find the skill in every project." % (link, ROOT))


def main():
    p = argparse.ArgumentParser(prog="arc", add_help=False)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("help").set_defaults(fn=cmd_help)
    s = sub.add_parser("open"); s.add_argument("source"); s.add_argument("work"); s.add_argument("--title")
    s.add_argument("--standards"); s.set_defaults(fn=cmd_open)
    s = sub.add_parser("map"); s.add_argument("work"); s.add_argument("--no-ids", action="store_true"); s.set_defaults(fn=cmd_map)
    s = sub.add_parser("text"); s.add_argument("work"); s.set_defaults(fn=cmd_text)
    s = sub.add_parser("check"); s.add_argument("work"); s.add_argument("--json", action="store_true")
    s.add_argument("--standards"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("new-plan"); s.add_argument("work"); s.set_defaults(fn=cmd_new_plan)
    s = sub.add_parser("plan"); s.add_argument("work"); s.add_argument("--try", dest="try_build", action="store_true")
    s.add_argument("--show", nargs="+", metavar="S01", help="with --try: print where each listed suggestion's text lands")
    s.set_defaults(fn=cmd_plan)
    for name, fn in (("accept", cmd_accept), ("reject", cmd_reject), ("revise", cmd_revise), ("reset", cmd_reset)):
        s = sub.add_parser(name); s.add_argument("work"); s.add_argument("ids", nargs="+"); s.add_argument("--note")
        s.set_defaults(fn=fn)
    s = sub.add_parser("apply"); s.add_argument("work"); s.add_argument("--dry-run", action="store_true"); s.set_defaults(fn=cmd_apply)
    s = sub.add_parser("validate"); s.add_argument("work"); s.set_defaults(fn=cmd_validate)
    s = sub.add_parser("pack"); s.add_argument("work"); s.add_argument("out"); s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_pack)
    s = sub.add_parser("diff"); s.add_argument("a"); s.add_argument("b"); s.set_defaults(fn=cmd_diff)
    s = sub.add_parser("status"); s.add_argument("work"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("batch"); s.add_argument("exports"); s.add_argument("runs"); s.add_argument("--again", action="store_true")
    s.add_argument("--standards")
    s.set_defaults(fn=cmd_batch)
    sub.add_parser("install").set_defaults(fn=cmd_install)
    s = sub.add_parser("report"); s.add_argument("work"); s.set_defaults(fn=cmd_report)
    s = sub.add_parser("feedback"); s.add_argument("work"); s.add_argument("file"); s.set_defaults(fn=cmd_feedback)
    s = sub.add_parser("implement"); s.add_argument("work"); s.set_defaults(fn=cmd_implement)
    a = p.parse_args()
    if not a.cmd:
        print(HELP)
        return
    a.fn(a)


if __name__ == "__main__":
    main()
