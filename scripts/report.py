"""The two outputs of a plan.

suggestions.md   for people: the course team reads it, decides, comments (./arc report, ./arc feedback)
implement.md     for coding agents: what was accepted, as builds and briefs (./arc implement)
"""
import datetime
import json
import os
import re

import plan as pl

DECISIONS = {"yes": "accepted", "accept": "accepted", "accepted": "accepted",
             "change": "revise", "revise": "revise", "changes": "revise",
             "no": "rejected", "reject": "rejected", "rejected": "rejected"}


def audit_sections(work):
    """{heading: text} from arc/audit.md, by its fixed '## ' headings."""
    p = os.path.join(work, "arc", "audit.md")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        text = f.read()
    out = {}
    for m in re.finditer(r"^## (.+?)\n(.*?)(?=^## |\Z)", text, re.S | re.M):
        out[m.group(1).strip()] = m.group(2).strip()
    return out


def _section(sections, *names):
    for n in names:
        for k, v in sections.items():
            if k.lower().startswith(n.lower()):
                return v
    return ""


def _draft_text(work, rel):
    p = os.path.join(work, "arc", rel)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        t = f.read()
    if rel.endswith(".json"):
        return pl.rubric_md(json.loads(t))
    return re.sub(r"<!--.*?-->\s*", "", t, flags=re.S).strip()


def suggestions_md(work, plan, course=None):
    c = plan.get("course", {})
    sug = [s for s in plan.get("suggestions", []) if s.get("status") != "rejected" or s.get("note")]
    sec = audit_sections(work)
    prof = pl.profiles().get(c.get("standards") or "", None)
    today = datetime.date.today().isoformat()
    L = ["# AI readiness suggestions: %s" % c.get("title", "(course)"), "",
         "*For the course team. Prepared %s. These are suggestions for your review: nothing in the course changes until "
         "you decide.*" % today, ""]
    summary = _section(sec, "Summary")
    if summary:
        L += ["## In short", "", summary, ""]
    L += ["## How to respond", "",
          "Under each suggestion, after **Your decision**, keep one word: **yes**, **change** or **no**. Write anything "
          "you want after **Your comments**: what to change, why not, or an idea of your own. Send this file back, or "
          "tell whoever sent it. Accepted suggestions are then turned into course content, which you see before "
          "students do.", ""]
    if c.get("audience") or c.get("level"):
        L += ["## Assumptions to confirm", "", c.get("audience", ""), ""]
        if c.get("level"):
            L.append("Target level: **%s**." % c["level"])
            L.append("")
    ready = _section(sec, "The six readiness questions", "Readiness")
    if ready:
        L += ["## Where the course stands", "", ready, ""]
    if prof:
        std = _section(sec, prof.get("audit_heading", prof["name"]), "Edge")
        if std:
            L += ["## %s" % prof["name"], "", std, ""]
    level = _section(sec, "Recommended level")
    if level:
        L += ["## Level", "", level, ""]
    head = ["#", "Suggestion", "Kind", "Strengthens"] + (["Meets", "Supports"] if prof else []) + ["Your time to review"]
    L += ["## The suggestions", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for s in sug:
        row = [s["id"], s.get("title", "").replace("|", "/"), kind_of(s), ", ".join(pl.readiness_of(s)) or "-"]
        if prof:
            row += [", ".join(pl.standards_of(s)) or "-", ", ".join(s.get("supports") or []) or "-"]
        row.append(s.get("effort", "-"))
        L.append("| " + " | ".join(row) + " |")
    L += ["", "Readiness questions: " + "; ".join("%s %s" % kv for kv in pl.READINESS.items()) + ".", ""]
    for s in sug:
        L += ["---", "", "### %s · %s" % (s["id"], s.get("title", "")), ""]
        if s.get("origin") == "instructor":
            L += ["*Your own suggestion, drafted.*", ""]
        L += ["**Why.** %s" % s.get("why", ""), ""]
        tags = ["strengthens %s" % ", ".join(pl.readiness_of(s))] if pl.readiness_of(s) else []
        if prof and pl.standards_of(s):
            tags.append("meets %s" % ", ".join(pl.standards_of(s)))
        if prof and s.get("supports"):
            tags.append("supports %s" % ", ".join(s["supports"]))
        if s.get("level"):
            tags.append("level: %s" % s["level"])
        if s.get("module"):
            tags.append("module: %s" % pl.name_of(course, "module", s["module"]))
        if s.get("requires"):
            tags.append("goes with %s" % ", ".join(s["requires"]))
        if tags:
            L += ["*" + " · ".join(tags) + "*", ""]
        if pl.is_advice(s):
            L += ["**What we suggest.** %s" % s.get("advice", ""), ""]
        else:
            L += ["**What would change in the course:**", ""]
            L += ["- " + pl.describe_op(op, course) for op in s["ops"]]
            L.append("")
        for op in s.get("ops") or []:
            for k in ("body", "rubric", "add_criteria"):
                if isinstance(op.get(k), str):
                    d = _draft_text(work, op[k])
                    if d:
                        L += ["**%s** (draft):" % ("Rubric" if k != "body" else "Text"), "", _quote(d), ""]
        if s.get("brief") and pl.is_advice(s):
            d = _draft_text(work, s["brief"])
            if d:
                L += ["**Details:**", "", _quote(d), ""]
        decided = {"accepted": "yes", "rejected": "no", "revise": "change"}.get(s.get("status"), "yes / change / no")
        L += ["**Your decision:** %s" % decided, "", "**Your comments:** %s" % (s.get("note") or ""), ""]
    errors = _section(sec, "Errors found")
    if errors:
        L += ["---", "", "## Errors found in the current materials", "", errors, ""]
    L += ["---", "", "## About these suggestions", "",
          "They come from a framework in which students *conduct* AI in the discipline's own work: they attempt the "
          "learning first, frame the problem before prompting, give the AI bounded work, judge and verify what comes "
          "back against independent evidence, add what only they can, and keep an honest record of the process "
          "(the Frictional log). The aim is more hands-on work and more critical thinking, not more AI use for its own "
          "sake. Every draft uses this course's own content; examples made up for an exercise are labelled as such.", ""]
    return "\n".join(L) + "\n"


def kind_of(s):
    fw = s.get("framework") or []
    if "correction" in fw:
        k = "correction"
    elif "housekeeping" in fw:
        k = "housekeeping"
    else:
        k = "change"
    return k + (" (by hand)" if pl.is_advice(s) else "")


def _quote(text):
    return "\n".join("> " + ln if ln.strip() else ">" for ln in text.split("\n"))


def parse_feedback(text):
    """{sid: (status or None, comment)} from a returned suggestions.md."""
    out = {}
    for m in re.finditer(r"^### (S\d{2,}) ·.*?(?=^### S\d{2,} ·|^## |\Z)", text, re.S | re.M):
        block = m.group(0)
        d = re.search(r"\*\*Your decision:\*\*(.*)", block)
        cm = re.search(r"\*\*Your comments:\*\*(.*?)(?=^---\s*$|\Z)", block, re.S | re.M)
        status = None
        if d:
            words = re.findall(r"[a-z]+", d.group(1).lower())
            hits = {DECISIONS[w] for w in words if w in DECISIONS}
            if len(hits) == 1:
                status = hits.pop()
        comment = re.sub(r"\s+", " ", cm.group(1)).strip() if cm else ""
        out[m.group(1)] = (status, comment)
    return out


def implement_md(work, plan, course=None):
    """The coding agent's brief for everything accepted."""
    acc = [s for s in plan.get("suggestions", []) if s.get("status") == "accepted"]
    c = plan.get("course", {})
    L = ["# Implementation brief: %s" % c.get("title", "(course)"), "",
         "For a coding agent (Claude Code, Codex, Claude Desktop). The course team accepted the suggestions below. "
         "Build exactly these, nothing more.", "",
         "## Rules", "",
         "1. **Do not invent.** No statistics, quotes, results or course facts you cannot point to. Text the "
         "instructor must write (their own use of AI, anything in [brackets]) stays as a prompt for them.",
         "2. **Canvas changes go through the tool.** For suggestions marked *built by arc*, run `./arc apply <work>`, "
         "then `./arc validate <work>` and `./arc pack <work> <new.imscc>` from the ai-readiness folder. Never edit "
         "the course's XML by hand.",
         "3. **Everything new arrives unpublished.** The course team publishes after looking.",
         "4. **Fixed course files** (a corrected notebook, a slide deck) go in `arc/files/` at the file's exact path in "
         "the course, e.g. `arc/files/web_resources/Assignments/Wk6.ipynb`; `./arc apply` swaps them into the new "
         "export. Never rename them.",
         "5. **Check your work** against each suggestion's *Done when* list, and report what you could not check.",
         "6. **Ask before** changing anything not listed here, deleting anything, or touching a live course.", "",
         "Work folder: `%s`" % os.path.abspath(work), ""]
    if not acc:
        L += ["*Nothing has been accepted yet.*", ""]
    for s in sorted(acc, key=lambda s: s["id"]):
        L += ["---", "", "## %s · %s" % (s["id"], s.get("title", "")), ""]
        if s.get("note"):
            L += ["**Course team's note:** %s" % s["note"], ""]
        L += ["**Why:** %s" % s.get("why", ""), ""]
        if s.get("requires"):
            L += ["**Build together with:** %s" % ", ".join(s["requires"]), ""]
        if not pl.is_advice(s):
            L += ["**Built by arc** (`./arc apply`). It will:", ""]
            L += ["- " + pl.describe_op(op, course) for op in s["ops"]]
            drafts = sorted({op[k] for op in s["ops"] for k in ("body", "rubric", "add_criteria") if isinstance(op.get(k), str)})
            if drafts:
                L += ["", "Content: " + ", ".join("`arc/%s`" % d for d in drafts)]
            L += ["", "**Done when:**", "",
                  "- `./arc apply` lists %s in the build log with no FAIL" % s["id"],
                  "- after a sandbox import, each item above appears where described, unpublished, with its rubric "
                  "and points", ""]
        else:
            L += ["**By hand** (the tool cannot make this change).", "", "**What to do:** %s" % s.get("advice", ""), ""]
            if s.get("brief"):
                d = _draft_text(work, s["brief"])
                if d:
                    L += [d, ""]
            else:
                L += ["*No detailed brief was written; ask the course team or the planner for one before starting.*", ""]
    return "\n".join(L) + "\n"
