"""Tests for ai-readiness. Run: python3 -m unittest discover tests

They use a constructed course (tests/fixtures/materials), never a real export. Real exports hold names,
email addresses and account ids, and stay out of this repository.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import cartridge as cg  # noqa: E402
import checks  # noqa: E402
import plan as pl  # noqa: E402
from mdhtml import md_to_html, html_to_text  # noqa: E402

MATERIALS = os.path.join(ROOT, "tests", "fixtures", "materials")
TEMPLATES = os.path.join(ROOT, "templates")


def arc(*args):
    r = subprocess.run([os.path.join(ROOT, "arc")] + list(args), capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def tree_hash(folder):
    h = hashlib.md5()
    for dp, _, fn in sorted(os.walk(folder)):
        for f in sorted(fn):
            p = os.path.join(dp, f)
            h.update(os.path.relpath(p, folder).encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="arc-test-")
        self.work = os.path.join(self.tmp, "w")
        code, out = arc("open", MATERIALS, self.work, "--title", "Sorting 101")
        self.assertEqual(code, 0, out)
        # pack it once so later tests start from a real .imscc, as an instructor would
        self.imscc = os.path.join(self.tmp, "course.imscc")
        code, out = arc("pack", self.work, self.imscc)
        self.assertEqual(code, 0, out)
        self.w2 = os.path.join(self.tmp, "w2")
        code, out = arc("open", self.imscc, self.w2)
        self.assertEqual(code, 0, out)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def course(self, work=None, overlay=True):
        return cg.Course(cg.Store(work or self.w2, overlay=overlay))

    def write_plan(self, suggestions, drafts):
        d = os.path.join(self.w2, "arc", "drafts")
        os.makedirs(d, exist_ok=True)
        for name, text in drafts.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text)
        pl.save(self.w2, {"version": 1, "course": {"title": "Sorting 101"}, "suggestions": suggestions})

    def copy_template(self, name, as_name=None):
        d = os.path.join(self.w2, "arc", "drafts")
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(TEMPLATES, name), os.path.join(d, as_name or name))


class OpenAndRead(Base):
    def test_folder_becomes_modules_and_pages(self):
        c = self.course()
        self.assertEqual([m["title"] for m in c.modules], ["Introduction", "Sorting"])
        titles = [i["title"] for m in c.modules for i in m["items"]]
        self.assertIn("Merge sort", titles)
        self.assertIn("Files: Sorting", titles)
        self.assertEqual(len(c.pages), 5)

    def test_text_readout_written(self):
        text = os.path.join(self.w2, "arc", "text")
        self.assertTrue(os.path.exists(os.path.join(text, "syllabus.md")))
        mods = sorted(os.listdir(os.path.join(text, "modules")))
        self.assertEqual(len(mods), 2)
        with open(os.path.join(text, "modules", mods[1]), encoding="utf-8") as f:
            self.assertIn("Implement merge sort", f.read())

    def test_untouched_round_trip_is_identical(self):
        out = os.path.join(self.tmp, "again.imscc")
        code, msg = arc("pack", self.w2, out)
        self.assertEqual(code, 0, msg)
        with zipfile.ZipFile(self.imscc) as a, zipfile.ZipFile(out) as b:
            ea = {i.filename: i.CRC for i in a.infolist()}
            eb = {i.filename: i.CRC for i in b.infolist()}
        self.assertEqual(ea, eb)

    def test_check_finds_nothing_ai_in_a_plain_course(self):
        f = checks.run(self.course())
        self.assertEqual(f["edge"]["E1"]["verdict"], "MISSING")
        self.assertEqual(f["edge"]["E3"]["verdict"], "MISSING")
        self.assertGreaterEqual(sum(m["objectives"] for m in f["modules"]), 2)

    def test_zip_slip_refused(self):
        bad = os.path.join(self.tmp, "bad.imscc")
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("imsmanifest.xml", "<manifest/>")
            z.writestr("../escape.txt", "x")
        with self.assertRaises(cg.CourseError):
            cg.open_course(bad, os.path.join(self.tmp, "bad"))


class ApplyEveryOp(Base):
    def make_plan(self):
        self.copy_template("process-criteria.json", "pc.json")
        self.copy_template("frictional-rubric.json", "fr.json")
        self.copy_template("glimmer-rubric.json", "gl.json")
        self.write_plan([
            {"id": "S01", "title": "Policy", "why": "t", "status": "accepted",
             "ops": [{"op": "edit_syllabus", "mode": "insert_after", "heading": "Course description", "body": "drafts/policy.md"}]},
            {"id": "S02", "title": "AI lab module", "why": "t", "status": "accepted",
             "ops": [{"op": "add_module", "title": "AI lab", "after": "Introduction"},
                     {"op": "add_page", "module": "AI lab", "title": "Working with AI", "body": "drafts/gate.md"},
                     {"op": "add_assignment", "module": "AI lab", "title": "Conduct it: merge sort", "body": "drafts/conduct.md",
                      "rubric": "drafts/pc.json", "group": "Assignments"}]},
            {"id": "S03", "title": "Glimmer", "why": "t", "status": "accepted",
             "ops": [{"op": "add_discussion", "module": "Sorting", "title": "Glimmer: sorting & you", "body": "drafts/glimmer.md",
                      "rubric": "drafts/gl.json", "after": "start"}]},
            {"id": "S04", "title": "Objective", "why": "t", "status": "accepted",
             "ops": [{"op": "edit_page", "page": "Merge sort", "mode": "insert_after", "heading": "Objectives", "body": "drafts/obj.md"}]},
            {"id": "S05", "title": "Not this one", "why": "t", "status": "proposed",
             "ops": [{"op": "add_page", "module": "Sorting", "title": "Should not appear", "body": "drafts/obj.md"}]},
        ], {"policy.md": "## AI in this course\n\nAI assistance is allowed & expected <really>.\n",
            "gate.md": "## Working with AI\n\n**AI should:** check arithmetic.\n\n**Human should:** prove it.\n",
            "conduct.md": "# Conduct it\n\n1. Predict.\n2. Audit first.\n",
            "glimmer.md": "# Glimmer\n\nMake a proposal.\n",
            "obj.md": "- Judge whether an AI-generated merge is stable, before checking it by hand.\n"})

    def test_apply_validate_pack_reopen(self):
        self.make_plan()
        code, out = arc("plan", self.w2)
        self.assertEqual(code, 0, out)
        code, out = arc("apply", self.w2)
        self.assertEqual(code, 0, out)
        self.assertIn("validate: FAIL 0", out)
        c = self.course()
        self.assertEqual([m["title"] for m in c.modules], ["Introduction", "AI lab", "Sorting"])
        lab = c.modules[1]
        self.assertEqual([i["type"] for i in lab["items"]], ["WikiPage", "Assignment"])
        sorting = c.modules[2]
        self.assertEqual(sorting["items"][0]["type"], "DiscussionTopic")
        self.assertNotIn("Should not appear", [p["title"] for p in c.pages.values()])
        a = c.assignment("Conduct it: merge sort")
        self.assertEqual(a["points"], 10.0)
        self.assertEqual(a["state"], "unpublished")
        self.assertIn(a["rubric"], c.rubrics)
        t = [t for t in c.topics.values() if t["title"] == "Glimmer: sorting & you"][0]
        self.assertEqual(t["points"], 20.0)
        self.assertIn(t["rubric"], c.rubrics)
        syl = c.store.read(cg.SYLLABUS)
        self.assertIn("allowed &amp; expected &lt;really&gt;", syl)
        self.assertLess(syl.index("AI in this course"), syl.index("Course outcomes"))
        self.assertIn("<h2>AI in this course</h2>", syl)
        page = c.store.read(c.page("Merge sort")["href"])
        self.assertLess(page.index("AI-generated merge"), page.index("The idea"))
        # module positions are 1..n in module_meta
        mm = c.store.read(cg.MODULE_META)
        mod_pos = [int(p) for p in re.findall(r"<position>(\d+)</position>\s*<require_sequential", mm)]
        self.assertEqual(mod_pos, [1, 2, 3])
        out_path = os.path.join(self.tmp, "new.imscc")
        code, msg = arc("pack", self.w2, out_path)
        self.assertEqual(code, 0, msg)
        w3 = os.path.join(self.tmp, "w3")
        code, msg = arc("open", out_path, w3)
        self.assertEqual(code, 0, msg)
        code, msg = arc("validate", w3)
        self.assertEqual(code, 0, msg)
        self.assertEqual(checks.run(cg.Course(cg.Store(w3)))["edge"]["E1"]["verdict"], "CHECK")

    def test_apply_is_deterministic(self):
        self.make_plan()
        arc("apply", self.w2)
        h1 = tree_hash(os.path.join(self.w2, "arc", "build"))
        arc("apply", self.w2)
        self.assertEqual(h1, tree_hash(os.path.join(self.w2, "arc", "build")))

    def test_source_never_modified(self):
        before = tree_hash(os.path.join(self.w2, "source"))
        with open(self.imscc, "rb") as f:
            zbefore = hashlib.md5(f.read()).hexdigest()
        self.make_plan()
        arc("apply", self.w2)
        arc("pack", self.w2, os.path.join(self.tmp, "x.imscc"))
        self.assertEqual(before, tree_hash(os.path.join(self.w2, "source")))
        with open(self.imscc, "rb") as f:
            self.assertEqual(zbefore, hashlib.md5(f.read()).hexdigest())


class EditAssignment(Base):
    def test_shared_rubric_is_copied_not_changed(self):
        self.copy_template("process-criteria.json", "pc.json")
        self.copy_template("frictional-rubric.json", "fr.json")
        self.write_plan([
            {"id": "S01", "title": "two assignments", "why": "t", "status": "accepted",
             "ops": [{"op": "add_assignment", "module": "Sorting", "title": "A one", "body": "drafts/a.md", "rubric": "drafts/pc.json"},
                     {"op": "add_assignment", "module": "Sorting", "title": "A two", "body": "drafts/a.md", "rubric": "drafts/pc.json"}]}],
            {"a.md": "Do it.\n"})
        code, out = arc("apply", self.w2)
        self.assertEqual(code, 0, out)
        # make A two share A one's rubric, as Canvas courses often do, then rebuild the source from the build
        build = os.path.join(self.w2, "arc", "build")
        c = self.course()
        one, two = c.assignment("A one"), c.assignment("A two")
        p = os.path.join(build, two["settings"])
        with open(p, encoding="utf-8") as f:
            s = f.read()
        with open(p, "w", encoding="utf-8") as f:
            f.write(s.replace(two["rubric"], one["rubric"]))
        for dp, _, fn in os.walk(build):
            for name in fn:
                rel = os.path.relpath(os.path.join(dp, name), build)
                os.makedirs(os.path.dirname(os.path.join(self.w2, "source", rel)), exist_ok=True)
                shutil.copy(os.path.join(dp, name), os.path.join(self.w2, "source", rel))
        shutil.rmtree(build)
        self.write_plan([
            {"id": "S02", "title": "frictional on A one", "why": "t", "status": "accepted",
             "ops": [{"op": "edit_assignment", "assignment": "A one", "body": "drafts/f.md", "add_criteria": "drafts/fr.json"}]}],
            {"f.md": "## Frictional log\n\nKeep it.\n"})
        code, out = arc("apply", self.w2)
        self.assertEqual(code, 0, out)
        self.assertIn("shared its rubric", out)
        c = self.course()
        a1, a2 = c.assignment("A one"), c.assignment("A two")
        self.assertNotEqual(a1["rubric"], a2["rubric"])
        self.assertEqual(a2["rubric"], one["rubric"])
        self.assertEqual(len(c.rubrics[a1["rubric"]]["criteria"]), 4 + 5)
        self.assertEqual(len(c.rubrics[a2["rubric"]]["criteria"]), 4)


class NewOps(Base):
    def test_edit_discussion_requires_try_and_placeholders(self):
        self.copy_template("glimmer-rubric.json", "gl.json")
        self.copy_template("frictional-rubric.json", "fr.json")
        self.write_plan([
            {"id": "S01", "title": "graded discussion", "why": "t", "status": "accepted",
             "ops": [{"op": "add_discussion", "module": "Sorting", "title": "Talk about merge sort", "body": "drafts/d.md",
                      "rubric": "drafts/gl.json"}]},
            {"id": "S02", "title": "critique step on it", "why": "t", "status": "accepted", "requires": ["S01"],
             "ops": [{"op": "edit_discussion", "discussion": "Talk about merge sort", "mode": "append", "body": "drafts/c.md",
                      "add_criteria": "drafts/fr.json", "points": 30}]},
            {"id": "S03", "title": "policy with prompts left", "why": "t", "status": "proposed",
             "ops": [{"op": "edit_syllabus", "body": "drafts/p.md"}]},
        ], {"d.md": "## Prompt\n\nWhat makes merge sort stable?\n",
            "c.md": "## Check the AI\n\n<details><summary>Hint</summary>\n\nLook at ties.\n\n</details>\n",
            "p.md": "## AI\n\n[Which AI tools did you use while preparing this course?]\n\nUse {{tool}}.\n"})
        code, out = arc("plan", self.w2, "--try")
        self.assertEqual(code, 0, out)
        self.assertIn("S03: drafts/p.md still has 2 unfilled", out)
        self.assertIn("trial: FAIL 0", out)
        code, out = arc("apply", self.w2)
        self.assertEqual(code, 0, out)
        c = self.course()
        t = c.discussion("Talk about merge sort")
        self.assertEqual(t["points"], 30.0)
        self.assertEqual(len(c.rubrics[t["rubric"]]["criteria"]), 5 + 5)
        self.assertIn("<details><summary>Hint</summary>", t["text"])
        self.assertIn("Check the AI", t["text"])
        # S02 without S01 is refused
        arc("reset", self.w2, "S01")
        code, out = arc("apply", self.w2)
        self.assertNotEqual(code, 0)
        self.assertIn("S02 needs S01", out)

    def test_assignment_file_types(self):
        self.write_plan([
            {"id": "S01", "title": "a", "why": "t", "status": "accepted",
             "ops": [{"op": "add_assignment", "module": "Sorting", "title": "Notebook", "body": "drafts/a.md", "points": 10,
                      "submission_types": ["online_upload"]},
                     {"op": "edit_assignment", "assignment": "Notebook", "submission_types": ["online_upload", "online_text_entry"],
                      "allowed_extensions": ["ipynb", "md"]}]}], {"a.md": "Do it.\n"})
        code, out = arc("apply", self.w2)
        self.assertEqual(code, 0, out)
        a = self.course().assignment("Notebook")
        self.assertEqual(a["submission"], "online_upload,online_text_entry")
        self.assertEqual(a["extensions"], "ipynb,md")

    def test_plan_md_shows_titles_not_ids(self):
        c = self.course()
        mid = c.module("Sorting")["id"]
        self.write_plan([{"id": "S01", "title": "x", "why": "t", "status": "proposed", "module": mid,
                          "ops": [{"op": "add_page", "module": mid, "title": "P", "body": "drafts/x.md"}]}], {"x.md": "<!-- note to agent -->\nHello.\n"})
        arc("plan", self.w2)
        with open(os.path.join(self.w2, "arc", "plan.md"), encoding="utf-8") as f:
            md = f.read()
        self.assertIn("module *Sorting*", md)
        self.assertNotIn(mid, md)
        self.assertNotIn("note to agent", md)


class Batch(Base):
    def test_batch_opens_each_export_and_indexes(self):
        exports = os.path.join(self.tmp, "exports")
        os.makedirs(exports)
        shutil.copy(self.imscc, os.path.join(exports, "info6205-12345-algorithms-sec-1-fall-2023-export.imscc"))
        shutil.copy(self.imscc, os.path.join(exports, "info6205-99999-algorithms-sec-2-fall-2023-export.imscc"))
        shutil.copy(self.imscc, os.path.join(exports, "Old Course.imscc"))
        runs = os.path.join(self.tmp, "runs")
        code, out = arc("batch", exports, runs)
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(d for d in os.listdir(runs) if d != "README.md"),
                         ["info6205-fall-2023", "info6205-fall-2023-2", "old-course"])
        with open(os.path.join(runs, "README.md"), encoding="utf-8") as f:
            index = f.read()
        self.assertGreaterEqual(index.count("**missing**"), 3)
        code, out = arc("batch", exports, runs)
        self.assertIn("already open", out)

    def test_batch_refuses_runs_inside_exports(self):
        code, out = arc("batch", self.tmp, os.path.join(self.tmp, "runs"))
        self.assertNotEqual(code, 0)


class TwoAudiences(Base):
    def make(self):
        self.copy_template("process-criteria.json", "pc.json")
        self.write_plan([
            {"id": "S01", "title": "Add an AI section to the syllabus", "why": "No AI rules.", "framework": ["policy"],
             "status": "proposed", "effort": "small", "ops": [{"op": "edit_syllabus", "body": "drafts/p.md"}]},
            {"id": "S02", "title": "Conduct it on merge sort", "why": "No hands-on AI work.", "framework": ["conduct"],
             "status": "proposed", "effort": "medium",
             "ops": [{"op": "add_assignment", "module": "Sorting", "title": "Conduct it", "body": "drafts/c.md", "rubric": "drafts/pc.json"}]},
            {"id": "S03", "title": "Fix the week 2 notebook's expected output", "why": "It expects 6; the route takes 12.",
             "status": "proposed", "effort": "small", "readiness": ["R6"], "advice": "Change the expected output to 12.",
             "brief": "drafts/S03-brief.md", "ops": []},
        ], {"p.md": "## AI in this course\n\nAI is allowed.\n", "c.md": "# Conduct it\n\nPredict first.\n",
            "S03-brief.md": "**Where:** notebook wk2, cell 4.\n\n**Done when:** the test passes.\n"})
        with open(os.path.join(self.w2, "arc", "audit.md"), "w", encoding="utf-8") as f:
            f.write("# AI readiness audit\n\n## Summary\n\nNot ready yet; three changes would help.\n\n"
                    "## The six readiness questions\n\n| Q | Verdict |\n|---|---|\n| R1 | MISSING |\n\n"
                    "## Errors found in the course materials\n\nWeek 2 expects 6.\n")

    def test_report_feedback_implement(self):
        self.make()
        code, out = arc("plan", self.w2, "--try")
        self.assertEqual(code, 0, out)
        code, out = arc("report", self.w2)
        self.assertEqual(code, 0, out)
        path = os.path.join(self.w2, "arc", "suggestions.md")
        with open(path, encoding="utf-8") as f:
            doc = f.read()
        for s in ("## In short", "Not ready yet", "### S01 · Add an AI section", "**Your decision:** yes / change / no",
                  "Change the expected output to 12.", "Week 2 expects 6.", "strengthens R3, R4", "AI is allowed."):
            self.assertIn(s, doc)
        # the course team answers in the document
        doc = doc.replace("**Your decision:** yes / change / no", "**Your decision:** yes", 1)
        doc = doc.replace("**Your decision:** yes / change / no", "**Your decision:** change", 1)
        doc = doc.replace("**Your comments:** \n", "**Your comments:** \n", 1)
        i = doc.index("### S02")
        j = doc.index("**Your comments:**", i)
        doc = doc[:j] + "**Your comments:** Make it a discussion, not an assignment.\n" + doc[doc.index("\n", j) + 1:]
        returned = os.path.join(self.tmp, "returned.md")
        with open(returned, "w", encoding="utf-8") as f:
            f.write(doc.replace("**Your decision:** yes / change / no", "**Your decision:** yes"))
        code, out = arc("feedback", self.w2, returned)
        self.assertEqual(code, 0, out)
        plan = pl.load(self.w2)
        st = {s["id"]: (s["status"], s.get("note", "")) for s in plan["suggestions"]}
        self.assertEqual(st["S01"][0], "accepted")
        self.assertEqual(st["S02"], ("revise", "Make it a discussion, not an assignment."))
        self.assertEqual(st["S03"][0], "accepted")
        code, out = arc("implement", self.w2)
        self.assertEqual(code, 0, out)
        self.assertIn("2 accepted (1 built by arc, 1 by hand)", out)
        with open(os.path.join(self.w2, "arc", "implement.md"), encoding="utf-8") as f:
            brief = f.read()
        self.assertIn("**Built by arc**", brief)
        self.assertIn("**By hand**", brief)
        self.assertIn("notebook wk2, cell 4", brief)
        self.assertNotIn("Conduct it on merge sort", brief)
        # apply builds S01 and skips the advice-only S03
        code, out = arc("apply", self.w2)
        self.assertEqual(code, 0, out)

    def test_advice_without_text_fails(self):
        self.write_plan([{"id": "S01", "title": "x", "why": "t", "status": "proposed", "ops": []}], {})
        problems = pl.check(self.w2, pl.load(self.w2), self.course())
        self.assertTrue(any(p[0] == "FAIL" and "advice" in p[2] for p in problems))

    def test_standards_profile(self):
        code, out = arc("check", self.w2, "--standards", "northeastern-edge")
        self.assertEqual(code, 0, out)
        with open(os.path.join(self.w2, "arc", "check.md"), encoding="utf-8") as f:
            md = f.read()
        self.assertIn("## The six readiness questions", md)
        self.assertIn("Edge AI-ready course certification", md)
        code, out = arc("check", self.w2)
        with open(os.path.join(self.w2, "arc", "check.md"), encoding="utf-8") as f:
            self.assertIn("Edge AI-ready", f.read())  # remembered in source.json
        code, out = arc("check", self.w2, "--standards", "nowhere")
        self.assertNotEqual(code, 0)


class FixedFiles(Base):
    def test_files_swapped_in_and_unknown_paths_refused(self):
        c = self.course()
        pdf = [n for n in c.store.names() if n.endswith(".pdf")][0]
        self.write_plan([{"id": "S01", "title": "x", "why": "t", "status": "accepted",
                          "ops": [{"op": "edit_syllabus", "body": "drafts/x.md"}]}], {"x.md": "Hello.\n"})
        os.makedirs(os.path.dirname(os.path.join(self.w2, "arc", "files", pdf)), exist_ok=True)
        with open(os.path.join(self.w2, "arc", "files", pdf), "wb") as f:
            f.write(b"%PDF-1.4 fixed")
        os.makedirs(os.path.join(self.w2, "arc", "files", "web_resources"), exist_ok=True)
        with open(os.path.join(self.w2, "arc", "files", "web_resources", "nowhere.ipynb"), "w") as f:
            f.write("{}")
        code, out = arc("apply", self.w2)
        self.assertEqual(code, 0, out)
        self.assertIn("does not replace a file", out)
        out_path = os.path.join(self.tmp, "fixed.imscc")
        arc("pack", self.w2, out_path)
        with zipfile.ZipFile(out_path) as z:
            self.assertEqual(z.read(pdf), b"%PDF-1.4 fixed")
            self.assertNotIn("web_resources/nowhere.ipynb", z.namelist())

    def test_insert_before_a_tag(self):
        body = "<p>Prompt</p>\n<div><details><summary>Rubric</summary><table></table></details></div>"
        out = cg.edit_section(body, "insert_before", "<details>", "<p>Part 2</p>", "t")
        self.assertLess(out.index("Part 2"), out.index("<div><details>"))


class PlanRules(Base):
    def test_bad_refs_and_ambiguity_fail(self):
        self.write_plan([
            {"id": "S01", "title": "x", "why": "t", "status": "accepted",
             "ops": [{"op": "add_page", "module": "No such module", "title": "x", "body": "drafts/x.md"}]},
            {"id": "S02", "title": "y", "why": "t", "status": "accepted",
             "ops": [{"op": "edit_page", "page": "Merge sort", "mode": "replace_section", "body": "drafts/x.md"}]},
            {"id": "S03", "title": "z", "why": "t", "status": "rejected",
             "ops": [{"op": "edit_page", "page": "Nope", "body": "drafts/x.md"}]}],
            {"x.md": "x\n"})
        problems = pl.check(self.w2, pl.load(self.w2), self.course())
        fails = {(p[1]) for p in problems if p[0] == "FAIL"}
        self.assertEqual(fails, {"S01", "S02"})

    def test_decisions(self):
        self.write_plan([{"id": "S01", "title": "x", "why": "t", "status": "proposed",
                          "ops": [{"op": "edit_syllabus", "body": "drafts/x.md"}]}], {"x.md": "x\n"})
        arc("revise", self.w2, "S01", "--note", "shorter please")
        s = pl.load(self.w2)["suggestions"][0]
        self.assertEqual((s["status"], s["note"]), ("revise", "shorter please"))
        code, out = arc("apply", self.w2)
        self.assertNotEqual(code, 0)
        arc("accept", self.w2, "S01")
        self.assertEqual(pl.load(self.w2)["suggestions"][0]["status"], "accepted")

    def test_templates_are_valid_rubrics(self):
        for name in os.listdir(TEMPLATES):
            if name.endswith(".json"):
                self.assertEqual(pl.check_rubric(os.path.join(TEMPLATES, name)), [], name)


class Sections(unittest.TestCase):
    BODY = ('<div class="a"><h3>Objectives</h3><ul><li>one</li></ul></div>\n'
            '<div class="b"><h3>Skills</h3><p>s</p></div>')

    def test_insert_after_lands_inside_the_section_block(self):
        out = cg.edit_section(self.BODY, "insert_after", "Objectives", "<h2>New</h2><p>n</p>", "t")
        self.assertIn("</ul><h3>New</h3><p>n</p>\n</div>", out.replace("\n<h3>New", "<h3>New"))
        self.assertLess(out.index("New"), out.index('<div class="b">'))

    def test_insert_before_shifts_headings(self):
        out = cg.edit_section(self.BODY, "insert_before", "Skills", "<h2>Note</h2><p>n</p>", "t")
        self.assertLess(out.index("<h3>Note</h3>"), out.index("<h3>Skills</h3>"))

    def test_replace_refuses_to_break_layout(self):
        with self.assertRaises(cg.CourseError):
            cg.edit_section('<h3>A</h3><div><p>x</p>\n<h3>B</h3></div>', "replace_section", "A", "<p>y</p>", "t")

    def test_missing_heading_lists_what_is_there(self):
        with self.assertRaises(cg.CourseError) as e:
            cg.edit_section(self.BODY, "insert_after", "Nope", "<p/>", "t")
        self.assertIn("Objectives", str(e.exception))


class Markdown(unittest.TestCase):
    def test_round_trip_basics(self):
        h = md_to_html("# T\n\nA **b** and [c](https://x.org) & <d>.\n\n- one\n- two\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        self.assertIn("<h1>T</h1>", h)
        self.assertIn("&amp; &lt;d&gt;", h)
        self.assertIn('<a href="https://x.org">c</a>', h)
        self.assertIn("<td>1</td>", h)
        t = html_to_text(h)
        self.assertIn("# T", t)
        self.assertIn("- one", t)


if __name__ == "__main__":
    unittest.main()
