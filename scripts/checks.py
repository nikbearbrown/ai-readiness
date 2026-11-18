"""The automatic part of the audit. It finds evidence and absences; it never says a standard is met.

Each Edge standard gets one of:
  MISSING       the material that would hold it was read, and nothing relevant is there
  CHECK         candidate evidence was found; the audit skill reads it and decides MEETS or PARTIAL
  NOT SUPPLIED  the material that would hold it is not in the export
"""
import html
import json
import os
import re

from cartridge import SYLLABUS, CourseError
from mdhtml import html_to_text
from readout import _body, KIND

AI_UP = re.compile(r"\b(AI|A\.I\.|GenAI|LLMs?|GPT(?:-?\d[\w.]*)?)\b")
AI_LO = re.compile(r"\b(artificial intelligence|generative|gen-ai|large language models?|chatgpt|claude|copilot|"
                   r"gemini|chatbots?|perplexity|midjourney|dall-?e|notebooklm|cursor|codex)\b", re.I)
REQUIRE = re.compile(r"\b(use|using|ask|prompt|generate|query|run|paste|have|interact|delegate|direct|conduct|consult|try|"
                     r"work with|collaborate)\b", re.I)
FORBID = re.compile(r"\b(do not|don't|not permitted|prohibited|not allowed|may not|must not|forbidden|banned)\b", re.I)
CRITIQUE = re.compile(r"\b(evaluat\w*|critiqu\w*|verif\w*|fact-?check\w*|audit\w*|assess\w*|compar\w*|reflect\w*|"
                      r"judg\w*|hallucinat\w*|limitation\w*|accura\w*|bias\w*|errors?|wrong|flaw\w*|plausib\w*|"
                      r"check\w*|sign-?off|not checked)\b", re.I)
PROCESS = re.compile(r"\b(AI|process|prompt\w*|verif\w*|disclos\w*|frictional|log|reflection|check\w*|"
                     r"contribution\w*|attempt\w*|audit\w*|sign-?off)\b", re.I)
STUDENT_USE = re.compile(r"\b(may|allowed|permitted|prohibited|must|disclos\w*|cite|acknowledg\w*|polic\w*|"
                         r"expected|encourag\w*|integrity)\b", re.I)
INSTRUCTOR_USE = re.compile(r"\b(I used|I use|I have used|I relied|instructor('s)? (own )?use|in (preparing|developing|"
                            r"building|designing) (this|the) course|course materials (were|are) (drafted|created|generated|developed)|"
                            r"AI-assisted|with the help of|prepared with|developed with|drafted with)\b", re.I)
OBJECTIVE_HEAD = re.compile(r"(objective|outcome|learning goal|by the end|you will be able|you will learn|"
                            r"learning target|students will)", re.I)
ACTIVITY_TITLE = re.compile(r"(exercise|practice|assessment|check|lab|quiz|activity|problem set|homework|"
                            r"reflection|assignment|discussion|project|case|worksheet|glimmer)", re.I)
MOVES = {
    "phase gate": re.compile(r"\b(AI should|Human should)\b"),
    "conducting AI": re.compile(r"\b(Conducting AI|Conduct it)\b"),
    "prediction": re.compile(r"\b(prediction-lock|predict (what|how|whether|which|the (result|output|outcome)|your)|"
                            r"(write|record|make|lock|date) (down )?(a |your )?predictions?|"
                            r"before (you )?(run|look at|see|check|ask|open)\w*)", re.I),
    "Frictional": re.compile(r"\bfrictional\b", re.I),
    "Glimmer": re.compile(r"\bglimmers?\b", re.I),
    "sign-off": re.compile(r"\b(sign-?off|not checked)\b", re.I),
    "disclosure": re.compile(r"\bdisclos\w*\b", re.I),
}


def move_found(name, rx, text):
    """Prediction must be asked of the student, not described in lesson prose."""
    if name != "prediction":
        return bool(rx.search(text))
    return any(rx.search(s) and re.search(r"\b(you|your)\b|^(predict|write|record|lock|make|date)\b", s, re.I)
               for s in sentences(text))


def other_course_links(c):
    """(where, url) for links and embeds (href, src, iframes, API endpoints) that point at another Canvas course."""
    from readout import raw_html_items
    out, seen = [], set()
    for where, h in raw_html_items(c):
        for m in re.finditer(r"(?:href|src|data-api-endpoint)=\"([^\"]*?/courses/(\d+)[^\"]*)\"", h):
            url = html.unescape(m.group(1))
            if (where, url) not in seen:
                seen.add((where, url))
                out.append((where, url))
    return out


def duplicate_pages(c):
    def key(t):
        return re.sub(r"\s+", " ", re.sub(r"[\u2013\u2014\u2012-]+", "-", t or "")).strip().lower()
    inside = {key(c.pages[r]["title"]) for r in c.pages if r in c.where}
    return sorted({p["title"] for r, p in c.pages.items() if r not in c.where and key(p["title"]) in inside})


def has_ai(s):
    return bool(AI_UP.search(s) or AI_LO.search(s))


def sentences(text):
    out = []
    for line in text.split("\n"):
        line = line.strip().lstrip("-*#0123456789.) ").strip()
        if not line:
            continue
        out += [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line) if p.strip()]
    return out


def clip(s, n=220):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def _read_text(c, href):
    try:
        return html_to_text(_body(c.store.read(href)))
    except CourseError:
        return ""


def item_texts(c):
    """[(where, kind, title, ref, text, rubric_id)] for every item a student meets, plus graded items in no module."""
    out, seen = [], set()
    for n, m in enumerate(c.modules, 1):
        for it in m["items"]:
            ref = it["ref"]
            where = "module %d (%s)" % (n, m["title"])
            if ref in c.pages:
                out.append((where, "page", it["title"], ref, _read_text(c, c.pages[ref]["href"]), None))
            elif ref in c.assignments:
                a = c.assignments[ref]
                out.append((where, "assignment", it["title"], ref, _read_text(c, a["href"]), a["rubric"]))
            elif ref in c.topics:
                t = c.topics[ref]
                out.append((where, "discussion", it["title"], ref, html_to_text(t["text"]), t.get("rubric")))
            elif ref in c.quizzes:
                out.append((where, "quiz", it["title"], ref, html_to_text(c.quizzes[ref]["description"]), None))
            if ref:
                seen.add(ref)
    for a in c.assignments.values():
        if a["id"] not in seen:
            out.append(("no module", "assignment", a["title"], a["id"], _read_text(c, a["href"]), a["rubric"]))
    for t in c.topics.values():
        if t["id"] not in seen and t["kind"] != "announcement":
            out.append(("no module", "discussion", t["title"], t["id"], html_to_text(t["text"]), t.get("rubric")))
    return out


def objectives(text):
    """Lines that look like objectives: list items under an objectives-like heading or lead-in."""
    found, on, budget = [], False, 0
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if OBJECTIVE_HEAD.search(s) and (s.startswith("#") or s.endswith(":") or len(s) < 40):
            on, budget = True, 12
            continue
        if on:
            if s.startswith("#"):
                on = False
                continue
            if re.match(r"^(-|\d+\.)\s+", s):
                found.append(re.sub(r"^(-|\d+\.)\s+", "", s))
                budget -= 1
                if budget <= 0:
                    on = False
            elif len(found) and not re.match(r"^(-|\d+\.)", s):
                on = False
    return found


ATTEMPT = re.compile(r"\b(AI should|Human should|before (you )?(use|using|ask|asking|consult|consulting|open|opening|turn"
                     r"|turning)\w* (to )?(AI|Claude|ChatGPT|Copilot|the chatbot|an? AI|a chatbot)|first attempt|"
                     r"attempt (it|the problem|this|the exercise|each) (first|yourself|on your own)|on your own first|"
                     r"without (using )?(AI|the chatbot|any AI))", re.I)
PROCESS_RECORD = re.compile(r"\b(frictional|process log|learning log|work log|journal|disclos\w*|sign-?off|"
                            r"what (I|you) tried|record (of )?(your|the) (process|attempts))\b", re.I)
CANT_FAKE = re.compile(r"\b(explain (your|the|how|why|it|this)|walk (us |me |the TA |the instructor )?through|oral|viva|"
                       r"in-class|in class|check-in|paper exam|closed[- ]book|without (notes|AI)|proctored|defend (your|the)|"
                       r"prediction-lock|whiteboard)\b", re.I)


def run(c, profile=None):
    items = item_texts(c)
    graded = [i for i in items if i[1] in ("assignment", "quiz") or (i[1] == "discussion" and c.topics[i[3]].get("points") is not None)]
    f = {"course": c.title, "edge": {}, "modules": [], "facts": {}, "notes": []}  # "edge" holds the raw signals

    # E1 ------------------------------------------------------------------------
    syl = ""
    try:
        syl = html_to_text(_body(c.store.read(SYLLABUS)))
    except CourseError:
        pass
    policy_pages = [p["title"] for p in c.pages.values() if re.search(r"\b(AI|artificial intelligence|generative)\b.*polic|polic.*\b(AI|generative)\b", p["title"], re.I)]
    if not syl.strip() or len(syl.split()) < 30:
        e1 = {"verdict": "NOT SUPPLIED", "evidence": [], "notes": ["The export has no syllabus text (or under 30 words). "
                                                                  "Canvas syllabi can live in a file or a page instead."]}
    else:
        ai_lines = [s for s in sentences(syl) if has_ai(s)]
        heads = [l.strip("# ").strip() for l in syl.split("\n")
                 if l.startswith("#") and (has_ai(l) or re.search(r"integrity|disclos", l, re.I))
                 and re.search(r"polic|integrity|disclos|guideline|use of|\buse\b|chatbot", l, re.I)]
        student = [s for s in ai_lines if STUDENT_USE.search(s)]
        instructor = [s for s in ai_lines if INSTRUCTOR_USE.search(s) and not s.rstrip().endswith("?")]
        notes = []
        if not ai_lines:
            verdict = "MISSING"
            notes.append("The syllabus never mentions AI.")
        else:
            verdict = "CHECK"
            if not student:
                notes.append("No sentence about what students may or may not do with AI was found.")
            if not instructor:
                notes.append("No sentence about the instructor's own use of AI in preparing the course was found. "
                             "Students should see both halves (Northeastern's Edge requires both in the syllabus); "
                             "only the instructor can write this one.")
        if policy_pages:
            notes.append("A page outside the syllabus looks like an AI policy: %s. Institutions that certify courses "
                         "usually want the policy in the syllabus itself."
                         % "; ".join(policy_pages[:3]))
        if re.search(r"https?://\S*(youtu|video|policy)\S*", " ".join(ai_lines), re.I):
            notes.append("The AI policy may be a link (video or page). A link alone is PARTIAL: students and certifiers read the syllabus.")
        e1 = {"verdict": verdict, "headings": heads[:5],
              "evidence": [{"where": "syllabus", "text": clip(s)} for s in (student + [s for s in ai_lines if s not in student])][:8],
              "instructor_signals": [clip(s) for s in instructor[:3]], "notes": notes}
    f["edge"]["E1"] = e1

    # E2 ------------------------------------------------------------------------
    mod_obj, ai_obj = {}, []
    for where, kind, title, ref, text, _ in items:
        if where == "no module":
            continue
        objs = objectives(text)
        if objs:
            mod_obj.setdefault(where, []).extend(objs)
            ai_obj += [(where, title, o) for o in objs if has_ai(o)]
    course_ai_obj = [o for o in objectives(syl) if has_ai(o)] if syl else []
    notes = ["Objectives were found in %d of %d modules." % (len(mod_obj), len(c.modules))]
    if ai_obj:
        verdict = "CHECK"
    elif not mod_obj:
        verdict = "CHECK"
        notes.append("No module-level objectives were detected. They may be phrased in a way this check does not "
                     "recognise, or the modules may not state objectives at all; read a few modules to tell.")
    else:
        verdict = "MISSING"
        notes.append("Modules state objectives, and none of them names AI.")
    if course_ai_obj and not ai_obj:
        notes.append("The syllabus has course-level outcomes naming AI. Course-level alone is PARTIAL where module-level "
                     "objectives are required (Northeastern's Edge E2).")
    f["edge"]["E2"] = {"verdict": verdict, "notes": notes,
                       "evidence": [{"where": "%s · %s" % (w, t), "text": clip(o)} for w, t, o in ai_obj[:8]],
                       "course_level": [clip(o) for o in course_ai_obj[:4]]}

    # E3, E4, E5 -----------------------------------------------------------------
    cands = []
    for where, kind, title, ref, text, rub in items:
        if kind == "page" and not ACTIVITY_TITLE.search(title):
            continue
        sents = sentences(text)
        req = [s for s in sents if has_ai(s) and REQUIRE.search(s) and not FORBID.search(s)
               and not re.search(r"\bpolicy\b", s, re.I)]
        if not req:
            continue
        crit = [s for s in sents if has_ai(s) and CRITIQUE.search(s)]
        rubric_hits = []
        if rub and rub in c.rubrics:
            for cr in c.rubrics[rub]["criteria"]:
                blob = cr["description"] + " " + cr["long_description"] + " " + " ".join(r.get("long_description", "") + " " + r["description"] for r in cr["ratings"])
                if PROCESS.search(blob):
                    rubric_hits.append("%s (%g)" % (cr["description"], cr["points"]))
        text_grading = [s for s in sents if re.search(r"\b(points?|graded|grading|rubric|criteri\w*)\b", s, re.I) and PROCESS.search(s)]
        score = len(req) + 2 * len(crit) + 3 * len(rubric_hits) + (2 if kind != "page" else 0)
        cands.append({"where": where, "kind": kind, "title": title, "id": ref, "score": score,
                      "requires_ai": [clip(s) for s in req[:3]], "critique": [clip(s) for s in crit[:3]],
                      "rubric": c.rubrics[rub]["title"] if rub in c.rubrics else None,
                      "rubric_process_criteria": rubric_hits, "grading_text": [clip(s) for s in text_grading[:3]]})
    cands.sort(key=lambda d: -d["score"])
    f["candidates"] = cands[:15]
    graded_ids = {i[3] for i in graded}
    if not items:
        e3 = {"verdict": "NOT SUPPLIED", "notes": ["No pages, assignments, discussions or quizzes were found."]}
    elif not cands:
        e3 = {"verdict": "MISSING", "notes": ["No activity asks students to use AI (prohibitions are not counted)."]}
    else:
        e3 = {"verdict": "CHECK", "notes": ["%d candidate activities; the strongest are listed. Optional or merely permitted "
                                             "use does not count: the activity must require it." % len(cands)]}
    f["edge"]["E3"] = e3
    with_crit = [d for d in cands if d["critique"]]
    f["edge"]["E4"] = ({"verdict": "MISSING" if cands else e3["verdict"],
                        "notes": ["No candidate activity asks students to evaluate the AI's output." if cands else "Depends on E3."]}
                       if not with_crit else
                       {"verdict": "CHECK", "notes": ["%d candidates ask for some evaluation of AI output. A generic reflection "
                                                      "on learning does not count." % len(with_crit)]})
    if not c.rubrics:
        e5 = {"verdict": "MISSING" if graded else "NOT SUPPLIED",
              "notes": ["The export has no Canvas rubrics at all. If grading is described in assignment text, check that "
                        "text; E5 expects a rubric that grades the process of AI engagement."]}
        if any(d["grading_text"] for d in cands):
            e5["verdict"] = "CHECK"
            e5["notes"].append("Some candidate activities describe process grading in their text.")
    else:
        hits = [d for d in cands if d["rubric_process_criteria"]]
        e5 = ({"verdict": "CHECK", "notes": ["%d candidate activities have rubric criteria that may grade process." % len(hits)]}
              if hits else
              {"verdict": "MISSING", "notes": ["No rubric attached to a candidate activity grades the process of working with AI."]})
    f["edge"]["E5"] = e5

    # modules and Bear's moves -----------------------------------------------------
    for n, m in enumerate(c.modules, 1):
        where = "module %d (%s)" % (n, m["title"])
        text = "\n".join(t for w, k, ti, r, t, _ in items if w == where)
        real = [it for it in m["items"] if it["type"] != "ContextModuleSubHeader"]
        last = real[-1] if real else None
        teaches = sum(1 for it in real if it["type"] == "WikiPage") >= 2
        ends_practice = bool(teaches and last and (last["type"] in ("Assignment", "DiscussionTopic", "Quizzes::Quiz")
                                                   or ACTIVITY_TITLE.search(last["title"])))
        f["modules"].append({
            "n": n, "title": m["title"], "id": m["id"], "state": m["state"], "items": len(m["items"]),
            "words": len(text.split()), "ai_mentions": len(AI_UP.findall(text)) + len(AI_LO.findall(text)),
            "ai_use_asked": sum(1 for s in sentences(text) if has_ai(s) and REQUIRE.search(s) and not FORBID.search(s)
                                and re.search(r"\byou(r)?\b|^(use|ask|prompt|run|have|give|paste)\b", s, re.I)),
            "objectives": len(mod_obj.get(where, [])), "ends_with_practice": ends_practice,
            "graded_items": sum(1 for it in real if it["ref"] in graded_ids),
            "moves": [k for k, rx in MOVES.items() if move_found(k, rx, text)],
        })
    allg = "\n".join(t for w, k, ti, r, t, _ in items if r in graded_ids)
    f["course_moves"] = {k: move_found(k, rx, allg + "\n" + syl) for k, rx in MOVES.items()}

    # the framework's six readiness questions ------------------------------------------
    sig = {"policy": f["edge"]["E1"], "objective": f["edge"]["E2"], "hands_on": f["edge"]["E3"],
           "critique": f["edge"]["E4"], "process_rubric": f["edge"]["E5"]}
    module_items = [i for i in items if i[0] != "no module"]

    def evidence(rx, pool, cue=None):
        out = []
        for where, kind, title, ref, text, _ in pool:
            for s in sentences(text):
                if rx.search(s) and (cue is None or cue(s)):
                    out.append({"where": "%s · %s" % (where, title), "text": clip(s)})
                    break
        return out
    att = evidence(ATTEMPT, module_items) + [{"where": "syllabus", "text": clip(s)} for s in sentences(syl) if ATTEMPT.search(s)][:2]
    sig["attempt_first"] = ({"verdict": "CHECK", "evidence": att[:8], "notes": ["%d places say what students do before or "
                             "without AI. Read them: a stated split per module (AI should / Human should) is the strong form." % len(att)]}
                            if att else {"verdict": "MISSING", "evidence": [], "notes": [
                                "Nothing tells students to attempt the work before turning to AI, or says per module what AI "
                                "should and should not do."]})
    graded_items = [i for i in items if i[3] in graded_ids]
    proc = evidence(PROCESS_RECORD, graded_items)
    rub_proc = [d for d in cands if d["rubric_process_criteria"]]
    if not graded_items:
        sig["process"] = {"verdict": "NOT SUPPLIED", "evidence": [], "notes": ["No graded work in the export."]}
    elif proc or rub_proc:
        sig["process"] = {"verdict": "CHECK", "evidence": proc[:8], "notes": [
            "%d graded items mention a process record (log, disclosure, sign-off). Check whether it is graded, not just "
            "requested." % len(proc)]}
    else:
        sig["process"] = {"verdict": "MISSING", "evidence": [], "notes": [
            "Graded work asks only for the product; nothing records or grades how it was made."]}
    fake = evidence(CANT_FAKE, graded_items + [("syllabus", "syllabus", "syllabus", None, syl, None)])
    pred = f["course_moves"].get("prediction")
    sig["cant_fake"] = ({"verdict": "CHECK", "evidence": fake[:8], "notes": [
        "%d graded items or syllabus passages ask for explanation, oral or paper checks, or predictions%s." %
        (len(fake), "; prediction steps appear in graded work" if pred else "")]}
        if fake or pred else {"verdict": "MISSING", "evidence": [], "notes": [
            "No assessment asks students to explain, defend or predict in a way an AI could not do for them."]})
    trivial = []
    for where, kind, title, ref, text, _ in items:
        for s in sentences(text):
            if has_ai(s) and re.search(r"\b(summari[sz]e|write|draft|generate|answer|complete)\b", s, re.I) \
                    and REQUIRE.search(s) and not FORBID.search(s) and not CRITIQUE.search(text):
                trivial.append({"where": "%s · %s" % (where, title), "text": clip(s)})
                break
    if trivial:
        sig["critique"] = dict(sig["critique"])
        sig["critique"]["trivial_use"] = trivial[:6]
    f["signals"] = sig
    f["readiness"] = {"R1": sig["policy"], "R2": sig["attempt_first"], "R3": sig["hands_on"], "R4": sig["critique"],
                      "R5": sig["process"], "R6": sig["cant_fake"]}
    if profile:
        f["standards"] = {"profile": profile["id"], "name": profile["name"], "short": profile.get("short", profile["id"]),
                          "results": {s["id"]: dict(sig[s["based_on"]], name=s["name"]) for s in profile["standards"]}}

    # facts and risks ---------------------------------------------------------------
    total_text = syl + "\n".join(i[4] for i in items)
    f["facts"] = {
        "modules": len(c.modules), "empty_modules": sum(1 for m in c.modules if not m["items"]),
        "unpublished_modules": sum(1 for m in c.modules if m["state"] != "active"),
        "pages": len(c.pages), "pages_in_no_module": sum(1 for p in c.pages if p not in c.where),
        "assignments": len(c.assignments), "assignments_in_no_module": sum(1 for a in c.assignments if a not in c.where),
        "graded_items": len(graded), "graded_with_rubric": sum(1 for i in graded if i[5]),
        "discussions": sum(1 for t in c.topics.values() if t["kind"] != "announcement"),
        "quizzes": len(c.quizzes), "rubrics": len(c.rubrics), "assignment_groups": len(c.groups),
        "assignments_limited_to_file_types": sum(1 for a in c.assignments.values() if a.get("extensions")),
        "shared_rubrics": sum(1 for r in c.rubrics if sum(1 for o in list(c.assignments.values()) + list(c.topics.values())
                                                         if o.get("rubric") == r) > 1),
        "links_to_other_courses": len(f.setdefault("links", other_course_links(c))),
        "duplicate_pages_outside_modules": len(f.setdefault("duplicates", duplicate_pages(c))),
        "announcements_mentioning_ai": len(f.setdefault("ai_announcements", sorted(
            [t["title"] for t in c.topics.values() if t["kind"] == "announcement" and has_ai(html_to_text(t["text"]))],
            key=lambda title: 0 if re.search(r"polic|grad|rubric|syllabus|use (of )?AI|AI (in|use)|integrity", title, re.I) else 1))),
        "email_addresses": len(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", total_text))),
    }
    mods_ai = sum(1 for m in f["modules"] if m["ai_mentions"])
    mods_use = sum(1 for m in f["modules"] if m["ai_use_asked"])
    f["level_signal"] = ("AI is mentioned in %d of %d modules (as a subject or a tool); %d modules address students "
                         "about using it, and %d activities are candidates for the designated AI activity. "
                         % (mods_ai, len(c.modules), mods_use, len(cands)) +
                         ("Signals point toward fluency (students already use AI in the work)."
                          if cands and mods_use > len(c.modules) / 2 else
                          "Signals point toward literacy as the starting level."))
    return f


READINESS_NAMES = {
    "R1": "Clear rules for AI use and disclosure",
    "R2": "Students attempt the learning first",
    "R3": "Hands-on AI work in the discipline",
    "R4": "Students judge and verify AI output",
    "R5": "The process is recorded and graded",
    "R6": "Assessment shows learning AI cannot fake",
}


def _detail(lines, d):
    for n in d.get("notes", []):
        lines.append("- %s" % n)
    if d.get("headings"):
        lines.append("- Headings: %s" % "; ".join(d["headings"]))
    for ev in d.get("evidence", []):
        lines.append("- *%s*: \u201c%s\u201d" % (ev["where"], ev["text"]))
    for s in d.get("instructor_signals", []):
        lines.append("- *instructor's own use?* \u201c%s\u201d" % s)
    for s in d.get("course_level", []):
        lines.append("- *course-level outcome*: \u201c%s\u201d" % s)
    for ev in d.get("trivial_use", []):
        lines.append("- *AI asked for an answer with no judgment step*: %s: \u201c%s\u201d" % (ev["where"], ev["text"]))
    lines.append("")


def report_md(f):
    r = f["readiness"]
    lines = ["# Automatic check: %s" % f["course"], ""]
    lines.append("**Summary.** Readiness: " + ", ".join("%s %s" % (k, r[k]["verdict"]) for k in sorted(r)) + "." +
                 ((" %s: " % f["standards"]["short"]) + ", ".join("%s %s" % (k, v["verdict"]) for k, v in f["standards"]["results"].items()) + "."
                  if f.get("standards") else "") +
                 " These are signals, not verdicts: CHECK means evidence was found for the audit to judge, MISSING means "
                 "the material was read and nothing relevant is there, NOT SUPPLIED means the material is not in the export. "
                 "The audit (skills/audit) reads the evidence and decides MEETS or PARTIAL.")
    lines += ["", f["level_signal"], "", "## The six readiness questions", "",
              "| # | Question | Signal |", "|---|---|---|"]
    for k in sorted(r):
        lines.append("| %s | %s | %s |" % (k, READINESS_NAMES[k], r[k]["verdict"]))
    lines.append("")
    for k in sorted(r):
        lines += ["### %s · %s: %s" % (k, READINESS_NAMES[k], r[k]["verdict"]), ""]
        _detail(lines, r[k])
    if f.get("standards"):
        st = f["standards"]
        lines += ["## %s" % st["name"], "", "| Standard | Signal |", "|---|---|"]
        for k, v in st["results"].items():
            lines.append("| %s %s | %s |" % (k, v["name"], v["verdict"]))
        lines.append("")
        obj = f["signals"]["objective"]
        if any(v is obj for v in st["results"].values()) or "E2" in st["results"]:
            lines += ["### Module objectives naming AI: %s" % obj["verdict"], ""]
            _detail(lines, obj)
    if f.get("candidates"):
        lines += ["## Candidate AI activities (E3–E5 chain)", ""]
        for d in f["candidates"][:8]:
            lines.append("**%s** · %s · %s · `%s`" % (d["title"], d["kind"], d["where"], d["id"]))
            for s in d["requires_ai"][:2]:
                lines.append("- uses AI: “%s”" % s)
            for s in d["critique"][:2]:
                lines.append("- critique: “%s”" % s)
            if d["rubric"]:
                lines.append("- rubric: %s; process-like criteria: %s" % (d["rubric"], ", ".join(d["rubric_process_criteria"]) or "none"))
            for s in d["grading_text"][:1]:
                lines.append("- grading text: “%s”" % s)
            lines.append("")
    lines += ["## Modules and the framework's moves", "",
              "| # | Module | Items | AI mentions | AI use asked | Objectives | Ends with practice | Graded | Moves found |",
              "|---|---|---|---|---|---|---|---|---|"]
    for m in f["modules"]:
        lines.append("| %d | %s%s | %d | %d | %d | %d | %s | %d | %s |" % (
            m["n"], m["title"].replace("|", "/"), "" if m["state"] == "active" else " (unpublished)", m["items"],
            m["ai_mentions"], m["ai_use_asked"], m["objectives"], "yes" if m["ends_with_practice"] else "no", m["graded_items"],
            ", ".join(m["moves"]) or "-"))
    cm = f["course_moves"]
    lines += ["", "Across graded work and the syllabus: " + ", ".join("%s %s" % (k, "yes" if v else "no") for k, v in cm.items()) + ".",
              "Moves are found by keywords: treat them as places to look, not as proof the move is there.", ""]
    lines += ["## Course facts", ""]
    for k, v in f["facts"].items():
        lines.append("- %s: %s" % (k.replace("_", " "), v))
    if f.get("links"):
        lines.append("- Links and embeds pointing to other Canvas courses (not rewritten on import):")
        for where, url in f["links"][:15]:
            lines.append("  - %s: `%s`" % (where, url[:120]))
        if len(f["links"]) > 15:
            lines.append("  - … and %d more" % (len(f["links"]) - 15))
    if f.get("duplicates"):
        lines.append("- Pages outside modules that duplicate a page inside a module (same title once dashes and spacing "
                     "are ignored): " + "; ".join(f["duplicates"][:10]) + (" …" if len(f["duplicates"]) > 10 else ""))
    if f.get("ai_announcements"):
        lines.append("- Announcements that mention AI (they do not count for E1, but may hold the real policy; "
                     "text in arc/text/announcements.md; policy and grading ones first): " + "; ".join(f["ai_announcements"][:8]) +
                     ("; … and %d more" % (len(f["ai_announcements"]) - 8) if len(f["ai_announcements"]) > 8 else ""))
    if f["facts"]["email_addresses"]:
        lines.append("- The course text contains email addresses. Keep exports and reports private.")
    return "\n".join(lines) + "\n"


def write(c, work, profile=None):
    f = run(c, profile)
    d = os.path.join(work, "arc")
    with open(os.path.join(d, "findings.json"), "w", encoding="utf-8") as fh:
        json.dump(f, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(d, "check.md"), "w", encoding="utf-8") as fh:
        fh.write(report_md(f))
    return f
