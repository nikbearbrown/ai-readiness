"""Read, change and repack Canvas course exports (.imscc). See docs/imscc.md.

Design:
- The original export is never modified. `open` extracts every non-media entry into <work>/source/
  so it can be read; media stays in the original zip, which `pack` reads again.
- Changes are written as surgical text edits (never an XML re-serialization, which would rewrite
  namespaces and every untouched byte) into an overlay folder, <work>/arc/build/.
- `pack` streams the original entries, swapping in overlay files and adding new ones.
"""
import hashlib
import html
import json
import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from mdhtml import md_to_html, html_to_text

NS_CP = "http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1"
NS_C = "http://canvas.instructure.com/xsd/cccv1p0"
NS_DT = "http://www.imsglobal.org/xsd/imsccv1p1/imsdt_v1p1"
LAR = "associatedcontent/imscc_xmlv1p1/learning-application-resource"
MODULE_META = "course_settings/module_meta.xml"
COURSE_SETTINGS = "course_settings/course_settings.xml"
GROUPS = "course_settings/assignment_groups.xml"
RUBRICS = "course_settings/rubrics.xml"
SYLLABUS = "course_settings/syllabus.html"
MEDIA = "web_resources/"
ID_RE = re.compile(r"^g[0-9a-f]{32}$")
CANVAS_XSI = ('xmlns="http://canvas.instructure.com/xsd/cccv1p0" '
              'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
              'xsi:schemaLocation="http://canvas.instructure.com/xsd/cccv1p0 '
              'https://canvas.instructure.com/xsd/cccv1p0.xsd"')


def cp(t):
    return "{%s}%s" % (NS_CP, t)


def cc(t):
    return "{%s}%s" % (NS_C, t)


class CourseError(Exception):
    pass


def x(s):
    """Escape text for XML element content."""
    return html.escape(s or "", quote=False)


def slugify(s, limit=60):
    s = re.sub(r"[^\w\s-]", "", (s or "").lower(), flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    s = s.encode("ascii", "ignore").decode() or "item"
    return s[:limit].strip("-") or "item"


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


# ── the store: original archive + extracted text + overlay ─────────────────────────

class Store:
    def __init__(self, work, overlay=True):
        self.work = os.path.abspath(work)
        meta_path = os.path.join(self.work, "arc", "source.json")
        if not os.path.exists(meta_path):
            raise CourseError("%s is not a work folder. Start with: ./arc open <course.imscc or folder> %s" % (work, work))
        with open(meta_path, encoding="utf-8") as f:
            self.meta = json.load(f)
        self.src = self.meta["path"] if self.meta.get("kind") == "dir" else os.path.join(self.work, "source")
        self.build = os.path.join(self.work, "arc", "build") if overlay else None
        self._zip = None
        self._names = None

    def zip(self):
        if self.meta.get("kind") != "zip":
            return None
        if self._zip is None:
            p = self.meta["path"]
            if not os.path.exists(p):
                raise CourseError("The original export has moved or gone: %s. Put it back or run open again." % p)
            st = os.stat(p)
            if st.st_size != self.meta.get("size"):
                raise CourseError("The original export changed size since open: %s. Run open again." % p)
            self._zip = zipfile.ZipFile(p)
        return self._zip

    def _local(self, rel):
        if self.build and os.path.isfile(os.path.join(self.build, rel)):
            return os.path.join(self.build, rel)
        if os.path.isfile(os.path.join(self.src, rel)):
            return os.path.join(self.src, rel)
        return None

    def read_bytes(self, rel):
        p = self._local(rel)
        if p:
            with open(p, "rb") as f:
                return f.read()
        z = self.zip()
        if z is not None and rel in self.names():
            return z.read(rel)
        raise CourseError("File not found in the course: %s" % rel)

    def read(self, rel):
        return self.read_bytes(rel).decode("utf-8")

    def exists(self, rel):
        return self._local(rel) is not None or rel in self.names()

    def names(self):
        if self._names is None:
            n = set()
            z = self.zip()
            if z is not None:
                n.update(i.filename for i in z.infolist() if not i.filename.endswith("/"))
            for base in (self.src, self.build):
                if base and os.path.isdir(base):
                    for dp, _, fn in os.walk(base):
                        for f in fn:
                            n.add(os.path.relpath(os.path.join(dp, f), base).replace(os.sep, "/"))
            self._names = n
        return self._names


# ── the course model (read only) ────────────────────────────────────────────────────

class Course:
    def __init__(self, store, cache=None):
        self.store = store
        self.cache = cache if cache is not None else {}
        if not store.exists("imsmanifest.xml"):
            raise CourseError("No imsmanifest.xml: this is not a course export.")
        if not store.exists(MODULE_META):
            raise CourseError("No course_settings/module_meta.xml: this is a Common Cartridge but not a Canvas "
                              "export. This version reads Canvas exports, or a folder of materials.")
        man = ET.fromstring(store.read_bytes("imsmanifest.xml"))
        self.manifest_id = man.get("identifier")
        self.resources = {}
        for r in man.iter(cp("resource")):
            self.resources[r.get("identifier")] = {
                "id": r.get("identifier"), "type": r.get("type") or "", "href": r.get("href") or "",
                "files": [f.get("href") for f in r.findall(cp("file"))],
                "deps": [d.get("identifierref") for d in r.findall(cp("dependency"))],
            }
        self.org = []
        orgs = man.find(cp("organizations"))
        o = orgs.find(cp("organization")) if orgs is not None else None
        lm = o.find(cp("item")) if o is not None else None
        if lm is not None:
            for m in lm.findall(cp("item")):
                self.org.append({"id": m.get("identifier"), "title": m.findtext(cp("title")) or "",
                                 "items": [{"id": i.get("identifier"), "ref": i.get("identifierref"),
                                            "title": i.findtext(cp("title")) or ""} for i in m.findall(cp("item"))]})
        mm = ET.fromstring(store.read_bytes(MODULE_META))
        self.modules = []
        for m in mm.findall(cc("module")):
            its = m.find(cc("items"))
            items = []
            for it in (its.findall(cc("item")) if its is not None else []):
                items.append({"id": it.get("identifier"), "type": it.findtext(cc("content_type")) or "",
                              "state": it.findtext(cc("workflow_state")) or "", "title": it.findtext(cc("title")) or "",
                              "ref": it.findtext(cc("identifierref")) or None,
                              "indent": int(it.findtext(cc("indent")) or 0)})
            self.modules.append({"id": m.get("identifier"), "title": m.findtext(cc("title")) or "",
                                 "state": m.findtext(cc("workflow_state")) or "", "items": items})
        self.course_id, self.title, self.code = None, "", ""
        if store.exists(COURSE_SETTINGS):
            cs = ET.fromstring(store.read_bytes(COURSE_SETTINGS))
            self.course_id = cs.get("identifier")
            self.title = cs.findtext(cc("title")) or ""
            self.code = cs.findtext(cc("course_code")) or ""
        self.groups = []
        if store.exists(GROUPS):
            for g in ET.fromstring(store.read_bytes(GROUPS)).findall(cc("assignmentGroup")):
                self.groups.append({"id": g.get("identifier"), "title": g.findtext(cc("title")) or "",
                                    "weight": g.findtext(cc("group_weight"))})
        self.rubrics = {}
        if store.exists(RUBRICS):
            for r in ET.fromstring(store.read_bytes(RUBRICS)).findall(cc("rubric")):
                crit = []
                for c in r.iter(cc("criterion")):
                    crit.append({"description": c.findtext(cc("description")) or "",
                                 "long_description": c.findtext(cc("long_description")) or "",
                                 "points": float(c.findtext(cc("points")) or 0),
                                 "ratings": [{"description": x_.findtext(cc("description")) or "",
                                              "long_description": x_.findtext(cc("long_description")) or "",
                                              "points": float(x_.findtext(cc("points")) or 0)}
                                             for x_ in c.iter(cc("rating"))]})
                self.rubrics[r.get("identifier")] = {"id": r.get("identifier"), "title": r.findtext(cc("title")) or "",
                                                     "points": float(r.findtext(cc("points_possible")) or 0),
                                                     "criteria": crit}
        self.where = {}
        for m in self.modules:
            for it in m["items"]:
                if it["ref"]:
                    self.where.setdefault(it["ref"], []).append(m["title"])
        self.pages, self.assignments, self.topics, self.quizzes = {}, {}, {}, {}
        dep_ids = set()
        for r in self.resources.values():
            if r["type"] == "imsdt_xmlv1p1" or r["type"].startswith("imsqti"):
                dep_ids.update(r["deps"])
        for rid, r in self.resources.items():
            href = r["href"]
            if href.startswith("wiki_content/"):
                self.pages[rid] = self._page(rid, href)
            elif any(f.endswith("/assignment_settings.xml") for f in r["files"]):
                self.assignments[rid] = self._assignment(rid, r)
            elif r["type"] == "imsdt_xmlv1p1":
                self.topics[rid] = self._topic(rid, r)
            elif r["type"].startswith("imsqti"):
                self.quizzes[rid] = self._quiz(rid, r)

    def _page(self, rid, href):
        overlay = getattr(self.store, "files", {})
        if href in self.cache and href not in overlay:
            return dict(self.cache[href], id=rid)
        out = self._page_read(rid, href)
        if href not in overlay:
            self.cache[href] = out
        return out

    def _page_read(self, rid, href):
        try:
            text = self.store.read(href)
        except CourseError:
            return {"id": rid, "href": href, "title": "(missing file)", "state": "", "missing": True}
        t = re.search(r"<title>(.*?)</title>", text, re.S)
        s = re.search(r'<meta name="workflow_state" content="([^"]+)"', text)
        return {"id": rid, "href": href, "title": html.unescape(t.group(1).strip()) if t else "",
                "state": s.group(1) if s else "", "front": 'name="front_page" content="true"' in text}

    def _assignment(self, rid, r):
        sp = next(f for f in r["files"] if f.endswith("/assignment_settings.xml"))
        try:
            a = ET.fromstring(self.store.read_bytes(sp))
        except CourseError:
            return {"id": rid, "title": "(missing file)", "href": r["href"], "settings": sp, "missing": True}
        return {"id": rid, "href": r["href"], "settings": sp, "title": a.findtext(cc("title")) or "",
                "points": float(a.findtext(cc("points_possible")) or 0), "group": a.findtext(cc("assignment_group_identifierref")),
                "rubric": a.findtext(cc("rubric_identifierref")), "state": a.findtext(cc("workflow_state")) or "",
                "submission": a.findtext(cc("submission_types")) or "", "due": a.findtext(cc("due_at")) or "",
                "extensions": a.findtext(cc("allowed_extensions")) or ""}

    def _topic(self, rid, r):
        out = {"id": rid, "href": r["files"][0] if r["files"] else "", "meta": r["deps"][0] if r["deps"] else None,
               "title": "", "text": "", "kind": "topic", "state": "", "points": None, "rubric": None}
        try:
            t = ET.fromstring(self.store.read_bytes(out["href"]))
            out["title"] = t.findtext("{%s}title" % NS_DT) or ""
            out["text"] = t.findtext("{%s}text" % NS_DT) or ""
        except (CourseError, ET.ParseError):
            pass
        if out["meta"] and out["meta"] in self.resources:
            try:
                m = ET.fromstring(self.store.read_bytes(self.resources[out["meta"]]["href"]))
                out["kind"] = m.findtext(cc("type")) or "topic"
                out["state"] = m.findtext(cc("workflow_state")) or ""
                a = m.find(cc("assignment"))
                if a is not None:
                    out["points"] = float(a.findtext(cc("points_possible")) or 0)
                    out["rubric"] = a.findtext(cc("rubric_identifierref"))
                    out["group"] = a.findtext(cc("assignment_group_identifierref"))
            except (CourseError, ET.ParseError):
                pass
        return out

    def _quiz(self, rid, r):
        out = {"id": rid, "title": "", "description": "", "points": None}
        for d in r["deps"]:
            dr = self.resources.get(d)
            if not dr:
                continue
            for f in dr["files"]:
                if f.endswith("assessment_meta.xml"):
                    try:
                        q = ET.fromstring(self.store.read_bytes(f))
                        out["title"] = q.findtext(cc("title")) or ""
                        out["description"] = q.findtext(cc("description")) or ""
                        p = q.findtext(cc("points_possible"))
                        out["points"] = float(p) if p else None
                        out["type"] = q.findtext(cc("quiz_type"))
                    except (CourseError, ET.ParseError):
                        pass
        return out

    # lookups ---------------------------------------------------------------------
    def module(self, ref):
        return self._one("module", ref, self.modules)

    def page(self, ref):
        return self._one("page", ref, list(self.pages.values()))

    def assignment(self, ref):
        return self._one("assignment", ref, list(self.assignments.values()))

    def discussion(self, ref):
        return self._one("discussion", ref, [t for t in self.topics.values() if t["kind"] != "announcement"])

    def group(self, ref):
        hits = [g for g in self.groups if g["id"] == ref] or [g for g in self.groups if g["title"] == ref]
        if len(hits) > 1:
            raise CourseError("More than one assignment group is called %r; use its identifier: %s"
                              % (ref, ", ".join(g["id"] for g in hits)))
        return hits[0] if hits else None

    def _one(self, kind, ref, objs):
        hits = [o for o in objs if o["id"] == ref]
        if not hits:
            hits = [o for o in objs if o["title"] == ref]
        if not hits:
            hits = [o for o in objs if norm(o["title"]) == norm(ref)]
        if not hits:
            raise CourseError("No %s matches %r. Run ./arc map to see identifiers and titles." % (kind, ref))
        if len(hits) > 1:
            raise CourseError("%d %ss are titled %r; use the identifier instead: %s"
                              % (len(hits), kind, ref, ", ".join(o["id"] for o in hits[:6])))
        return hits[0]

    def resolve_message(self, kind, ref, plan, sug, op_index):
        """For plan checks: None if ref resolves (or is created earlier in the accepted plan), else a message."""
        try:
            getattr(self, kind)(ref)
            return None
        except CourseError as e:
            creates = {"module": "add_module", "page": "add_page", "assignment": "add_assignment",
                       "discussion": "add_discussion"}[kind]
            for s in plan.get("suggestions", []):
                if s.get("status") == "rejected":
                    continue
                for j, op in enumerate(s.get("ops", []), 1):
                    if s is sug and j >= op_index:
                        break
                    if op.get("op") == creates and op.get("title") == ref:
                        return None
            return str(e)

    def all_ids(self):
        ids = set(self.resources)
        for m in self.modules:
            ids.add(m["id"])
            ids.update(i["id"] for i in m["items"])
        ids.update(self.rubrics)
        ids.update(g["id"] for g in self.groups)
        if self.course_id:
            ids.add(self.course_id)
        return ids


# ── open: from .imscc or from a folder of materials ─────────────────────────────────

def open_course(src, work, title=None):
    work = os.path.abspath(work)
    arc_dir = os.path.join(work, "arc")
    if os.path.exists(os.path.join(arc_dir, "source.json")):
        raise CourseError("%s already holds a course. Use another folder, or delete it first." % work)
    os.makedirs(os.path.join(work, "source"), exist_ok=True)
    os.makedirs(arc_dir, exist_ok=True)
    src = os.path.abspath(src)
    if os.path.isfile(src) and zipfile.is_zipfile(src):
        meta = _extract(src, os.path.join(work, "source"))
    elif os.path.isdir(src) and os.path.exists(os.path.join(src, "imsmanifest.xml")):
        meta = {"kind": "dir", "path": src}
    elif os.path.isdir(src):
        meta = {"kind": "built", "path": src}
        _write_json(os.path.join(arc_dir, "source.json"), meta)
        from_folder(src, work, title)
        return Store(work)
    else:
        raise CourseError("Expected a .imscc file or a folder: %s" % src)
    _write_json(os.path.join(arc_dir, "source.json"), meta)
    return Store(work)


def _extract(path, dest):
    st = os.stat(path)
    n_media = 0
    root = os.path.realpath(dest)
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            if name.startswith(MEDIA):
                n_media += 1
                continue
            target = os.path.realpath(os.path.join(dest, name))
            if not target.startswith(root + os.sep):
                raise CourseError("Refusing an entry that points outside the work folder: %r" % name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as fsrc, open(target, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
        entries = len(z.infolist())
    return {"kind": "zip", "path": path, "size": st.st_size, "entries": entries, "media_left_in_zip": n_media}


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ── surgical text editing helpers ───────────────────────────────────────────────────

_ITEM_TAG = re.compile(r"<item\b[^>]*?(/?)>|</item>")


def item_children(text, start_tag_end):
    """Direct <item> children of the <item> whose start tag ends at start_tag_end.
    Returns ([(start, end), ...], close_start) where close_start is where its </item> begins."""
    depth, kids, cur = 0, [], None
    for m in _ITEM_TAG.finditer(text, start_tag_end):
        tok = m.group(0)
        if tok == "</item>":
            if depth == 0:
                return kids, m.start()
            depth -= 1
            if depth == 0:
                kids.append((cur, m.end()))
        elif m.group(1) == "/":
            if depth == 0:
                kids.append((m.start(), m.end()))
        else:
            if depth == 0:
                cur = m.start()
            depth += 1
    raise CourseError("Unbalanced <item> elements in the manifest.")


def line_start(text, pos):
    return text.rfind("\n", 0, pos) + 1


def indent_of(text, pos):
    ls = line_start(text, pos)
    return len(text[ls:pos]) - len(text[ls:pos].lstrip(" "))


def insert_at(text, pos, block):
    return text[:pos] + block + text[pos:]


def indent_block(block, n):
    pad = " " * n
    return "".join(pad + ln + "\n" if ln else "\n" for ln in block.split("\n"))


# ── the editor: applies plan ops into an overlay ────────────────────────────────────

class Editor:
    def __init__(self, store):
        self.store = store
        self.files = {}
        self.log = []
        self.warnings = []
        self.cache = {}
        self.refresh()

    # store-like interface so Course can read through the editor
    def read_bytes(self, rel):
        if rel in self.files:
            v = self.files[rel]
            return v.encode("utf-8") if isinstance(v, str) else v
        return self.store.read_bytes(rel)

    def read(self, rel):
        return self.read_bytes(rel).decode("utf-8")

    def exists(self, rel):
        return rel in self.files or self.store.exists(rel)

    def names(self):
        return self.store.names() | set(self.files)

    def write(self, rel, content, why):
        new = rel not in self.files and not self.store.exists(rel)
        self.files[rel] = content
        self.log.append(("added" if new else "changed", rel, why))

    def refresh(self):
        self.course = Course(self, self.cache)

    def new_id(self, key):
        taken = self.course.all_ids()
        i = "g" + hashlib.md5(key.encode("utf-8")).hexdigest()
        while i in taken:
            key += "'"
            i = "g" + hashlib.md5(key.encode("utf-8")).hexdigest()
        return i

    def unique_path(self, folder, slug, ext):
        names = self.names()
        cand, n = "%s%s%s" % (folder, slug, ext), 2
        while cand in names:
            cand = "%s%s-%d%s" % (folder, slug, n, ext)
            n += 1
        return cand

    # module tree -------------------------------------------------------------------
    def _index(self, module, after):
        items = module["items"]
        if after in (None, "", "end"):
            return len(items)
        if after == "start":
            return 0
        for k, it in enumerate(items):
            if after in (it["id"], it["ref"]) or it["title"] == after:
                return k + 1
        raise CourseError("Module %r has no item %r to place after." % (module["title"], after))

    def _check_tree(self):
        c = self.course
        if [m["id"] for m in c.modules] != [m["id"] for m in c.org] or \
           [[i["id"] for i in m["items"]] for m in c.modules] != [[i["id"] for i in m["items"]] for m in c.org]:
            raise CourseError("The manifest's module tree and module_meta.xml disagree in this export; "
                              "refusing to edit modules. Run ./arc validate for details.")

    def add_module_item(self, module, index, content_type, ref, title, state, key):
        self._check_tree()
        iid = self.new_id("item:" + key)
        # module_meta.xml
        mm = self.read(MODULE_META)
        m = re.search(r'<module identifier="%s">' % re.escape(module["id"]), mm)
        if not m:
            raise CourseError("Module %s not found in module_meta.xml" % module["id"])
        mend = mm.index("</module>", m.end())
        if re.search(r"<items\s*/>", mm[m.end():mend]):
            e = re.search(r"<items\s*/>", mm[m.end():mend])
            pad = " " * indent_of(mm, m.end() + e.start())
            mm = mm[:m.end() + e.start()] + "<items>\n" + pad + "</items>" + mm[m.end() + e.end():]
            mend = mm.index("</module>", m.end())
        istart = mm.index("<items>", m.end(), mend)
        iend = mm.index("</items>", istart)
        spans = [(s.start(), mm.index("</item>", s.start()) + len("</item>"))
                 for s in re.finditer(r"<item identifier=", mm[:iend]) if s.start() > istart]
        pad = indent_of(mm, iend) + 2
        block = indent_block(
            '<item identifier="%s">\n  <content_type>%s</content_type>\n  <workflow_state>%s</workflow_state>\n'
            '  <title>%s</title>\n  <identifierref>%s</identifierref>\n  <position>0</position>\n'
            '  <new_tab>false</new_tab>\n  <indent>0</indent>\n  <link_settings_json>null</link_settings_json>\n</item>'
            % (iid, content_type, state, x(title), ref), pad)
        pos = line_start(mm, spans[index][0]) if index < len(spans) else line_start(mm, iend)
        mm = insert_at(mm, pos, block)
        mm = self._renumber_items(mm, module["id"])
        self.write(MODULE_META, mm, "module item %s" % title)
        # manifest organization
        man = self.read("imsmanifest.xml")
        m2 = re.search(r'<item identifier="%s">' % re.escape(module["id"]), man)
        if not m2:
            raise CourseError("Module %s not found in the manifest's module tree" % module["id"])
        kids, close = item_children(man, m2.end())
        pad = indent_of(man, m2.start()) + 2
        block = indent_block('<item identifier="%s" identifierref="%s">\n  <title>%s</title>\n</item>'
                             % (iid, ref, x(title)), pad)
        pos = line_start(man, kids[index][0]) if index < len(kids) else line_start(man, close)
        man = insert_at(man, pos, block)
        self.write("imsmanifest.xml", man, "module tree item %s" % title)
        return iid

    def _renumber_items(self, mm, module_id):
        m = re.search(r'<module identifier="%s">' % re.escape(module_id), mm)
        istart = mm.index("<items>", m.end())
        iend = mm.index("</items>", istart)
        seg = mm[istart:iend]
        n = [0]

        def num(_):
            n[0] += 1
            return "<position>%d</position>" % n[0]
        seg = re.sub(r"<position>\d*</position>", num, seg)
        return mm[:istart] + seg + mm[iend:]

    def add_module(self, title, after, published, key):
        self._check_tree()
        mid = self.new_id("module:" + key)
        state = "active" if published else "unpublished"
        mods = self.course.modules
        if after in (None, "", "end"):
            k = len(mods)
        elif after == "start":
            k = 0
        else:
            k = mods.index(self.course.module(after)) + 1
        mm = self.read(MODULE_META)
        spans = [(s.start(), mm.index("</module>", s.start()) + len("</module>"))
                 for s in re.finditer(r"<module identifier=", mm)]
        close = mm.rindex("</modules>")
        pad = indent_of(mm, close) + 2
        block = indent_block(
            '<module identifier="%s">\n  <title>%s</title>\n  <workflow_state>%s</workflow_state>\n'
            '  <position>0</position>\n  <require_sequential_progress>false</require_sequential_progress>\n'
            '  <locked>false</locked>\n  <items>\n  </items>\n</module>' % (mid, x(title), state), pad)
        pos = line_start(mm, spans[k][0]) if k < len(spans) else line_start(mm, close)
        mm = insert_at(mm, pos, block)
        # renumber module positions: the first <position> after each <module ...> start, before <items>
        out, last, n = [], 0, 0
        for s in re.finditer(r"<module identifier=", mm):
            items_at = mm.index("<items", s.start())
            p = re.compile(r"<position>\d*</position>").search(mm, s.start(), items_at)
            if p:
                n += 1
                out.append(mm[last:p.start()] + "<position>%d</position>" % n)
                last = p.end()
        mm = "".join(out) + mm[last:]
        self.write(MODULE_META, mm, "module %s" % title)
        man = self.read("imsmanifest.xml")
        lm = re.search(r'<item identifier="LearningModules">', man)
        if not lm:
            raise CourseError("The manifest has no LearningModules tree.")
        kids, lclose = item_children(man, lm.end())
        pad = indent_of(man, lm.start()) + 2
        block = indent_block('<item identifier="%s">\n  <title>%s</title>\n</item>' % (mid, x(title)), pad)
        pos = line_start(man, kids[k][0]) if k < len(kids) else line_start(man, lclose)
        man = insert_at(man, pos, block)
        self.write("imsmanifest.xml", man, "module tree %s" % title)
        self.refresh()
        return mid

    def add_resource(self, block):
        man = self.read("imsmanifest.xml")
        close = man.rindex("</resources>")
        pad = indent_of(man, close) + 2
        man = insert_at(man, line_start(man, close), indent_block(block, pad))
        self.write("imsmanifest.xml", man, "manifest resource")

    # content -----------------------------------------------------------------------
    def add_page(self, module_ref, title, body_html, after, published, key):
        module = self.course.module(module_ref)
        index = self._index(module, after)
        pid = self.new_id("page:" + key)
        state = "active" if published else "unpublished"
        path = self.unique_path("wiki_content/", slugify(title), ".html")
        page = ('<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n'
                '<title>%s</title>\n<meta name="identifier" content="%s"/>\n'
                '<meta name="editing_roles" content="teachers"/>\n<meta name="workflow_state" content="%s"/>\n'
                '<meta name="editor_type" content="rce"/>\n</head>\n<body>\n%s\n</body>\n</html>\n'
                % (x(title), pid, state, body_html))
        self.write(path, page, "page %s" % title)
        self.add_resource('<resource identifier="%s" type="webcontent" href="%s">\n  <file href="%s"/>\n</resource>'
                          % (pid, x(path), x(path)))
        self.refresh()
        self.add_module_item(module, index, "WikiPage", pid, title, state, key)
        self.refresh()
        return pid

    def ensure_group(self, ref, key):
        if not ref:
            if not self.course.groups:
                return self._new_group("Assignments", key)
            return self.course.groups[0]["id"]
        g = self.course.group(ref)
        if g:
            return g["id"]
        self.warnings.append("Created a new assignment group %r with weight 0; set its weight in Canvas." % ref)
        return self._new_group(ref, key)

    def _new_group(self, title, key):
        gid = self.new_id("group:" + key + ":" + title)
        if self.exists(GROUPS):
            t = self.read(GROUPS)
        else:
            t = ('<?xml version="1.0" encoding="UTF-8"?>\n<assignmentGroups %s>\n</assignmentGroups>\n' % CANVAS_XSI)
            self._list_in_settings(GROUPS, after=("course_settings/module_meta.xml",))
        close = t.rindex("</assignmentGroups>")
        block = indent_block('<assignmentGroup identifier="%s">\n  <title>%s</title>\n  <position>%d</position>\n'
                             '  <group_weight>0.0</group_weight>\n</assignmentGroup>'
                             % (gid, x(title), len(self.course.groups) + 1), 2)
        self.write(GROUPS, insert_at(t, line_start(t, close), block), "assignment group %s" % title)
        self.refresh()
        return gid

    def _list_in_settings(self, rel, after):
        """Add <file href=rel/> to the course-settings resource, after the first of `after` that is listed."""
        man = self.read("imsmanifest.xml")
        if 'href="%s"' % rel in man:
            return
        m = re.search(r'<resource [^>]*href="course_settings/canvas_export.txt"[^>]*>', man)
        if not m:
            raise CourseError("No course-settings resource in the manifest.")
        end = man.index("</resource>", m.end())
        pos = None
        for a in after:
            f = man.find('<file href="%s"/>' % a, m.end(), end)
            if f >= 0:
                pos = man.index("\n", f) + 1
        if pos is None:
            pos = line_start(man, end)
        pad = indent_of(man, end) + 2
        man = insert_at(man, pos, " " * pad + '<file href="%s"/>\n' % rel)
        self.write("imsmanifest.xml", man, "list %s in course settings" % rel)

    def add_rubric(self, rubric, key):
        rid = self.new_id("rubric:" + key)
        if self.exists(RUBRICS):
            t = self.read(RUBRICS)
        else:
            t = '<?xml version="1.0" encoding="UTF-8"?>\n<rubrics %s>\n</rubrics>\n' % CANVAS_XSI
            self._list_in_settings(RUBRICS, after=(GROUPS, "course_settings/grading_standards.xml"))
        criteria = rubric["criteria"]
        total = sum(float(c["points"]) for c in criteria)
        used = set()

        def local_id(seed):
            n = int(hashlib.md5(seed.encode("utf-8")).hexdigest()[:8], 16) % 9000 + 1000
            while n in used:
                n += 1
            used.add(n)
            return "_%d" % n
        parts = ['<rubric identifier="%s">' % rid, "  <read_only>false</read_only>",
                 "  <title>%s</title>" % x(rubric.get("title", "Rubric")), "  <reusable>false</reusable>",
                 "  <public>false</public>", "  <points_possible>%.1f</points_possible>" % total,
                 "  <hide_score_total>false</hide_score_total>",
                 "  <free_form_criterion_comments>false</free_form_criterion_comments>",
                 "  <rating_order>descending</rating_order>", "  <criteria>"]
        for i, c in enumerate(criteria):
            cid = local_id("%s:c%d:%s" % (rid, i, c["description"]))
            parts += ["    <criterion>", "      <criterion_id>%s</criterion_id>" % cid,
                      "      <points>%.1f</points>" % float(c["points"]),
                      "      <description>%s</description>" % x(c["description"]),
                      "      <long_description>%s</long_description>" % x(c.get("long_description", "")),
                      "      <criterion_use_range>false</criterion_use_range>", "      <ratings>"]
            for k, r in enumerate(sorted(c["ratings"], key=lambda r: -float(r["points"]))):
                parts += ["        <rating>", "          <description>%s</description>" % x(r["description"]),
                          "          <points>%.1f</points>" % float(r["points"]),
                          "          <criterion_id>%s</criterion_id>" % cid,
                          "          <long_description>%s</long_description>" % x(r.get("long_description", "")),
                          "          <id>%s</id>" % local_id("%s:r%d" % (cid, k)), "        </rating>"]
            parts += ["      </ratings>", "    </criterion>"]
        parts += ["  </criteria>", "</rubric>"]
        close = t.rindex("</rubrics>")
        t = insert_at(t, line_start(t, close), indent_block("\n".join(parts), 2))
        self.write(RUBRICS, t, "rubric %s" % rubric.get("title"))
        self.refresh()
        return rid, total

    def add_assignment(self, module_ref, title, body_html, points, submission_types, group, rubric, after,
                       published, key):
        module = self.course.module(module_ref)
        index = self._index(module, after)
        aid = self.new_id("assignment:" + key)
        gid = self.ensure_group(group, key)
        rid, total = (self.add_rubric(rubric, key) if rubric else (None, None))
        if points is None:
            points = total if total is not None else 0
            if not points:
                self.warnings.append("Assignment %r has 0 points and no rubric." % title)
        if total is not None and abs(float(points) - total) > 1e-9:
            self.warnings.append("Assignment %r is worth %s points but its rubric totals %s." % (title, points, total))
        state = "published" if published else "unpublished"
        slug = slugify(title)
        hpath = "%s/%s.html" % (aid, slug)
        spath = "%s/assignment_settings.xml" % aid
        position = len(self.course.assignments) + 1
        self.write(hpath, '<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n'
                          '<title>Assignment: %s</title>\n</head>\n<body>\n%s\n</body>\n</html>\n'
                   % (x(title), body_html), "assignment %s" % title)
        self.write(spath, assignment_settings(aid, title, gid, state, rid, points,
                                              submission_types or ["online_text_entry", "online_upload"], position),
                   "assignment settings %s" % title)
        self.add_resource('<resource identifier="%s" type="%s" href="%s">\n  <file href="%s"/>\n'
                          '  <file href="%s"/>\n</resource>' % (aid, LAR, x(hpath), x(hpath), spath))
        self.refresh()
        self.add_module_item(module, index, "Assignment", aid, title, "active" if published else "unpublished", key)
        self.refresh()
        return aid

    def add_discussion(self, module_ref, title, body_html, points, group, rubric, after, published, key):
        module = self.course.module(module_ref)
        index = self._index(module, after)
        tid = self.new_id("topic:" + key)
        mid = self.new_id("topicmeta:" + key)
        state = "active" if published else "unpublished"
        topic = ('<?xml version="1.0" encoding="UTF-8"?>\n<topic xmlns="%s" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                 'xsi:schemaLocation="%s  http://www.imsglobal.org/profile/cc/ccv1p1/ccv1p1_imsdt_v1p1.xsd">\n'
                 '  <title>%s</title>\n  <text texttype="text/html">%s</text>\n</topic>\n'
                 % (NS_DT, NS_DT, x(title), html.escape(body_html, quote=False)))
        graded = ""
        if points is not None or rubric:
            gid = self.ensure_group(group, key)
            rid, total = (self.add_rubric(rubric, key) if rubric else (None, None))
            if points is None:
                points = total
            if total is not None and abs(float(points) - total) > 1e-9:
                self.warnings.append("Discussion %r is worth %s points but its rubric totals %s." % (title, points, total))
            aid = self.new_id("topicassignment:" + key)
            graded = indent_block(assignment_settings(aid, title, gid, "published" if published else "unpublished",
                                                      rid, points, ["discussion_topic"], len(self.course.assignments) + 1,
                                                      inner=True), 2)
        meta = ('<?xml version="1.0" encoding="UTF-8"?>\n<topicMeta identifier="%s" %s>\n  <topic_id>%s</topic_id>\n'
                '  <title>%s</title>\n  <position/>\n  <type>topic</type>\n  <discussion_type>threaded</discussion_type>\n'
                '  <require_initial_post>false</require_initial_post>\n  <has_group_category>false</has_group_category>\n'
                '  <workflow_state>%s</workflow_state>\n  <module_locked>false</module_locked>\n'
                '  <allow_rating>false</allow_rating>\n  <only_graders_can_rate>false</only_graders_can_rate>\n'
                '  <sort_by_rating>false</sort_by_rating>\n  <sort_order>desc</sort_order>\n'
                '  <sort_order_locked>false</sort_order_locked>\n  <expanded>false</expanded>\n'
                '  <expanded_locked>false</expanded_locked>\n  <todo_date/>\n%s</topicMeta>\n'
                % (mid, CANVAS_XSI, tid, x(title), state, graded))
        self.write("%s.xml" % tid, topic, "discussion %s" % title)
        self.write("%s.xml" % mid, meta, "discussion settings %s" % title)
        self.add_resource('<resource identifier="%s" type="imsdt_xmlv1p1">\n  <file href="%s.xml"/>\n'
                          '  <dependency identifierref="%s"/>\n</resource>' % (tid, tid, mid))
        self.add_resource('<resource identifier="%s" type="%s" href="%s.xml">\n  <file href="%s.xml"/>\n</resource>'
                          % (mid, LAR, mid, mid))
        self.refresh()
        self.add_module_item(module, index, "DiscussionTopic", tid, title, state, key)
        self.refresh()
        return tid

    def edit_html(self, rel, mode, heading, body_html, why):
        t = self.read(rel)
        b0 = re.search(r"<body[^>]*>", t, re.I)
        b1 = t.lower().rfind("</body>")
        if not b0 or b1 < 0:
            raise CourseError("%s has no <body>; cannot edit it safely." % rel)
        body = t[b0.end():b1]
        self._warn_tail(body, mode, why)
        body = edit_section(body, mode or "append", heading, body_html, rel)
        self.write(rel, t[:b0.end()] + body + t[b1:], why)

    def edit_assignment(self, ref, mode, heading, body_html, add_criteria, points, key,
                        submission_types=None, allowed_extensions=None):
        a = self.course.assignment(ref)
        if body_html:
            self.edit_html(a["href"], mode, heading, body_html, "assignment text %s" % a["title"])
        s = self.read(a["settings"])
        if add_criteria:
            rid, total = self._rubric_with(a["rubric"], add_criteria, a["title"], key)
            s = self.read(a["settings"])
            if "<rubric_identifierref>" in s:
                s = re.sub(r"<rubric_identifierref>[^<]*</rubric_identifierref>",
                           "<rubric_identifierref>%s</rubric_identifierref>" % rid, s)
            else:
                m = re.search(r"\n([ \t]*)<workflow_state>[^<]*</workflow_state>\n", s)
                if not m:
                    raise CourseError("Cannot place a rubric in %s" % a["settings"])
                pad = m.group(1)
                add = "".join("%s%s\n" % (pad, ln) for ln in (
                    "<rubric_identifierref>%s</rubric_identifierref>" % rid,
                    "<rubric_use_for_grading>false</rubric_use_for_grading>",
                    "<rubric_hide_points>false</rubric_hide_points>",
                    "<rubric_hide_outcome_results>false</rubric_hide_outcome_results>",
                    "<rubric_hide_score_total>false</rubric_hide_score_total>"))
                s = s[:m.end()] + add + s[m.end():]
            pts = float(points) if points is not None else a["points"]
            if abs(pts - total) > 1e-9:
                self.warnings.append("Assignment %r is worth %s points; its rubric now totals %s. Decide whether to "
                                     "change the points or scale the new criteria." % (a["title"], pts, total))
        if points is not None:
            s = re.sub(r"<points_possible>[^<]*</points_possible>", "<points_possible>%.1f</points_possible>" % float(points), s, count=1)
        if submission_types:
            s = re.sub(r"<submission_types>[^<]*</submission_types>",
                       "<submission_types>%s</submission_types>" % ",".join(submission_types), s, count=1)
        if allowed_extensions is not None:
            ext = ",".join(allowed_extensions) if isinstance(allowed_extensions, list) else str(allowed_extensions)
            if re.search(r"<allowed_extensions\s*/>|<allowed_extensions>[^<]*</allowed_extensions>", s):
                s = re.sub(r"<allowed_extensions\s*/>|<allowed_extensions>[^<]*</allowed_extensions>",
                           "<allowed_extensions>%s</allowed_extensions>" % x(ext), s, count=1)
        if s != self.read(a["settings"]):
            self.write(a["settings"], s, "assignment settings %s" % a["title"])
        self.refresh()

    def _warn_tail(self, body, mode, what):
        if (mode or "append") == "append" and re.search(r"</(table|details)>\s*(</(div|p|span|section)>\s*|<p>(\s|&nbsp;|\xa0)*</p>\s*)*$", body, re.I):
            self.warnings.append("%s ends with a table or a collapsed block; appended text lands after it. Use "
                                 "insert_before a heading if it should come earlier (see it with --show)." % what)

    def _rubric_with(self, old_rid, add_criteria, users_title, key):
        """A new rubric = old criteria + new ones. Never edits a rubric in place (it may be shared)."""
        base, title = [], add_criteria.get("title") or "Rubric: %s" % users_title
        if old_rid and old_rid in self.course.rubrics:
            old = self.course.rubrics[old_rid]
            base = [{"description": c["description"], "long_description": c["long_description"],
                     "points": c["points"], "ratings": c["ratings"]} for c in old["criteria"]]
            title = "%s + %s" % (old["title"], add_criteria.get("title", "added criteria"))
            users = [o["title"] for o in list(self.course.assignments.values()) + list(self.course.topics.values())
                     if o.get("rubric") == old_rid and o["title"] != users_title]
            if users:
                self.warnings.append("%r shared its rubric with %d others; it now gets its own copy with the new "
                                     "criteria, and the others are unchanged." % (users_title, len(users)))
        return self.add_rubric({"title": title, "criteria": base + add_criteria["criteria"]}, key)

    def edit_discussion(self, ref, mode, heading, body_html, add_criteria, points, key):
        t = self.course.discussion(ref)
        if body_html:
            xml = self.read(t["href"])
            m = re.search(r'(<text texttype="text/html">)(.*?)(</text>)', xml, re.S)
            if not m:
                raise CourseError("Discussion %r has no text element to edit." % t["title"])
            body = html.unescape(m.group(2))
            self._warn_tail(body, mode, "discussion %s" % t["title"])
            body = edit_section(body, mode or "append", heading, body_html, "discussion %s" % t["title"])
            xml = xml[:m.start(2)] + html.escape(body, quote=False) + xml[m.end(2):]
            self.write(t["href"], xml, "discussion text %s" % t["title"])
        if add_criteria or points is not None:
            meta_href = self.course.resources[t["meta"]]["href"]
            s = self.read(meta_href)
            if "<assignment identifier=" not in s:
                raise CourseError("Discussion %r is not graded; this version can add criteria only to graded "
                                  "discussions. Suggest a graded discussion instead, or grade it in Canvas first." % t["title"])
            a0 = s.index("<assignment identifier=")
            a1 = s.index("</assignment>", a0)
            seg = s[a0:a1]
            if add_criteria:
                rid, total = self._rubric_with(t.get("rubric"), add_criteria, t["title"], key)
                s = self.read(meta_href)
                seg = s[a0:a1]
                if "<rubric_identifierref>" in seg:
                    seg = re.sub(r"<rubric_identifierref>[^<]*</rubric_identifierref>",
                                 "<rubric_identifierref>%s</rubric_identifierref>" % rid, seg, count=1)
                else:
                    m = re.search(r"\n([ \t]*)<workflow_state>[^<]*</workflow_state>\n", seg)
                    pad = m.group(1)
                    add = "".join("%s%s\n" % (pad, ln) for ln in (
                        "<rubric_identifierref>%s</rubric_identifierref>" % rid,
                        "<rubric_use_for_grading>false</rubric_use_for_grading>",
                        "<rubric_hide_points>false</rubric_hide_points>",
                        "<rubric_hide_outcome_results>false</rubric_hide_outcome_results>",
                        "<rubric_hide_score_total>false</rubric_hide_score_total>"))
                    seg = seg[:m.end()] + add + seg[m.end():]
                pts = float(points) if points is not None else (t.get("points") or 0)
                if abs(pts - total) > 1e-9:
                    self.warnings.append("Discussion %r is worth %s points; its rubric now totals %s." % (t["title"], pts, total))
            if points is not None:
                seg = re.sub(r"<points_possible>[^<]*</points_possible>", "<points_possible>%.1f</points_possible>" % float(points), seg, count=1)
            s = s[:a0] + seg + s[a1:]
            self.write(meta_href, s, "discussion settings %s" % t["title"])
        self.refresh()

    def write_out(self, dest):
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        for rel, content in self.files.items():
            p = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(content.encode("utf-8") if isinstance(content, str) else content)


def assignment_settings(aid, title, gid, state, rid, points, submission_types, position, inner=False):
    lines = []
    if not inner:
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<assignment identifier="%s" %s>' % (aid, CANVAS_XSI))
    else:
        lines.append('<assignment identifier="%s">' % aid)
    f = ["<title>%s</title>" % x(title), "<due_at/>", "<lock_at/>", "<unlock_at/>", "<module_locked>false</module_locked>",
         "<assignment_group_identifierref>%s</assignment_group_identifierref>" % gid,
         "<workflow_state>%s</workflow_state>" % state]
    if rid:
        f += ["<rubric_identifierref>%s</rubric_identifierref>" % rid, "<rubric_use_for_grading>false</rubric_use_for_grading>",
              "<rubric_hide_points>false</rubric_hide_points>", "<rubric_hide_outcome_results>false</rubric_hide_outcome_results>",
              "<rubric_hide_score_total>false</rubric_hide_score_total>"]
    f += ["<assignment_overrides>", "</assignment_overrides>", "<allowed_extensions></allowed_extensions>",
          "<has_group_category>false</has_group_category>", "<points_possible>%.1f</points_possible>" % float(points or 0),
          "<grading_type>points</grading_type>", "<all_day>false</all_day>",
          "<submission_types>%s</submission_types>" % ",".join(submission_types), "<position>%d</position>" % position,
          "<turnitin_enabled>false</turnitin_enabled>", "<vericite_enabled>false</vericite_enabled>",
          "<peer_review_count>0</peer_review_count>", "<peer_reviews>false</peer_reviews>",
          "<automatic_peer_reviews>false</automatic_peer_reviews>", "<anonymous_peer_reviews>false</anonymous_peer_reviews>",
          "<grade_group_students_individually>false</grade_group_students_individually>", "<freeze_on_copy>false</freeze_on_copy>",
          "<omit_from_final_grade>false</omit_from_final_grade>", "<hide_in_gradebook>false</hide_in_gradebook>",
          "<intra_group_peer_reviews>false</intra_group_peer_reviews>",
          "<only_visible_to_overrides>false</only_visible_to_overrides>", "<post_to_sis>false</post_to_sis>",
          "<moderated_grading>false</moderated_grading>", "<grader_count>0</grader_count>",
          "<grader_comments_visible_to_graders>true</grader_comments_visible_to_graders>",
          "<anonymous_grading>false</anonymous_grading>", "<graders_anonymous_to_graders>false</graders_anonymous_to_graders>",
          "<grader_names_visible_to_final_grader>true</grader_names_visible_to_final_grader>",
          "<anonymous_instructor_annotations>false</anonymous_instructor_annotations>",
          "<rubric_self_assessment_enabled>false</rubric_self_assessment_enabled>"]
    lines += ["  " + ln for ln in f]
    lines.append("</assignment>")
    return "\n".join(lines) + ("\n" if not inner else "")


_HEADING = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.I | re.S)


def edit_section(body, mode, heading, new_html, where):
    if mode == "append":
        return body.rstrip("\n") + "\n" + new_html + "\n"
    target = norm(heading)
    tag = re.fullmatch(r"<(\w+)>", (heading or "").strip())
    if mode == "insert_before" and tag:
        m = re.search(r"<%s\b" % tag.group(1), body, re.I)
        if not m:
            raise CourseError("No <%s> in %s to insert before." % (tag.group(1), where))
        start = m.start()
        while True:  # step back over wrappers that open right before the tag
            w = re.search(r"<(div|section|span|p)\b[^>]*>\s*$", body[:start], re.I)
            if not w:
                break
            start = w.start()
        return body[:start] + new_html + "\n" + body[start:]
    if mode == "insert_before":
        heads = list(_HEADING.finditer(body))
        hit = [h for h in heads if norm(html_to_text(h.group(2))) == target]
        if len(hit) != 1:
            raise CourseError("Heading %r found %d times in %s; insert_before needs exactly one." % (heading, len(hit), where))
        h = hit[0]
        level = int(h.group(1))
        shift = level - min([int(t) for t in re.findall(r"<h([1-6])\b", new_html)] or [level])
        if shift:
            new_html = re.sub(r"<(/?)h([1-6])\b", lambda m: "<%sh%d" % (m.group(1), min(6, max(1, int(m.group(2)) + shift))), new_html)
        return body[:h.start()] + new_html + "\n" + body[h.start():]
    heads = list(_HEADING.finditer(body))
    hit = [h for h in heads if norm(html_to_text(h.group(2))) == target]
    if not hit:
        names = [html_to_text(h.group(2)).strip() for h in heads][:12]
        raise CourseError("No heading %r in %s. Headings there: %s" % (heading, where, "; ".join(names) or "none"))
    if len(hit) > 1:
        raise CourseError("Heading %r appears %d times in %s; cannot tell which section." % (heading, len(hit), where))
    h = hit[0]
    level = int(h.group(1))
    end = len(body)
    for n in heads:
        if n.start() > h.start() and int(n.group(1)) <= level:
            end = n.start()
            break
    # Canvas pages wrap sections in layout blocks. Step back over the wrappers that open the next section and
    # the closing tags of this one, so the new content lands at the end of this section's own block.
    while True:
        m = re.search(r"<(div|section|article|header|span|p)\b[^>]*>\s*$", body[:end], re.I) or \
            re.search(r"</(div|section|article|span)>\s*$", body[:end], re.I)
        if not m or m.start() <= h.end():
            break
        end = m.start()
    shift = level - min([int(t) for t in re.findall(r"<h([1-6])\b", new_html)] or [level])
    if shift:
        new_html = re.sub(r"<(/?)h([1-6])\b", lambda m: "<%sh%d" % (m.group(1), min(6, max(1, int(m.group(2)) + shift))), new_html)
    if mode == "insert_after":
        return body[:end].rstrip("\n") + "\n" + new_html + "\n" + body[end:]
    old = body[h.start():end]
    for tag in ("div", "section", "span", "table", "ul", "ol"):
        if len(re.findall(r"<%s\b" % tag, old, re.I)) != len(re.findall(r"</%s>" % tag, old, re.I)):
            raise CourseError("Replacing the section %r in %s would break the page's layout (unbalanced <%s>). "
                              "Use insert_after, or replace a smaller section." % (heading, where, tag))
    return body[:h.start()] + new_html + "\n" + body[end:]


# ── validate and pack ───────────────────────────────────────────────────────────────

def validate(store):
    """Consistency checks that Canvas import depends on. Returns [(level, message)]."""
    out = []
    try:
        man_bytes = store.read_bytes("imsmanifest.xml")
        ET.fromstring(man_bytes)
    except (CourseError, ET.ParseError) as e:
        return [("FAIL", "imsmanifest.xml does not parse: %s" % e)]
    build_files = list(getattr(store, "files", {}))
    if getattr(store, "build", None) and os.path.isdir(store.build):
        for dp, _, fn in os.walk(store.build):
            for f in fn:
                build_files.append(os.path.relpath(os.path.join(dp, f), store.build).replace(os.sep, "/"))
    for rel in build_files:
        if rel.endswith(".xml"):
            try:
                ET.fromstring(store.read_bytes(rel))
            except ET.ParseError as e:
                out.append(("FAIL", "%s does not parse as XML: %s" % (rel, e)))
    try:
        c = Course(store)
    except (CourseError, ET.ParseError) as e:
        return out + [("FAIL", str(e))]
    if [m["id"] for m in c.modules] != [m["id"] for m in c.org]:
        out.append(("FAIL", "Module order differs between the manifest and module_meta.xml"))
    for a, b in zip(c.modules, c.org):
        if [i["id"] for i in a["items"]] != [i["id"] for i in b["items"]]:
            out.append(("FAIL", "Items of module %r differ between the manifest and module_meta.xml" % a["title"]))
        elif [i["ref"] for i in a["items"]] != [i["ref"] for i in b["items"]]:
            out.append(("FAIL", "Item targets of module %r differ between the manifest and module_meta.xml" % a["title"]))
        elif [i["title"] for i in a["items"]] != [i["title"] for i in b["items"]]:
            out.append(("WARN", "Item titles of module %r differ between the manifest and module_meta.xml" % a["title"]))
    for m in c.modules:
        for it in m["items"]:
            if it["ref"] and it["ref"] not in c.resources:
                out.append(("FAIL", "Module %r item %r points to a missing resource %s" % (m["title"], it["title"], it["ref"])))
    names = store.names()
    missing = [f for r in c.resources.values() for f in r["files"] if f not in names]
    if missing:
        out.append(("FAIL", "%d files listed in the manifest are not in the course, e.g. %s" % (len(missing), missing[:3])))
    ids = list(c.resources) + [m["id"] for m in c.modules] + [i["id"] for m in c.modules for i in m["items"]]
    from collections import Counter
    dup = sorted(i for i, n in Counter(ids).items() if n > 1)
    if dup:
        out.append(("FAIL", "Identifiers used twice: %s" % dup[:5]))
    for pid, p in c.pages.items():
        if p.get("missing"):
            continue
        t = store.read(p["href"])
        m = re.search(r'<meta name="identifier" content="([^"]+)"', t)
        if not m or m.group(1) != pid:
            out.append(("FAIL", "Page %s: its identifier meta does not match its resource" % p["href"]))
    group_ids = {g["id"] for g in c.groups}
    for aid, a in c.assignments.items():
        if a.get("missing"):
            out.append(("FAIL", "Assignment %s: settings file missing" % aid))
            continue
        s = ET.fromstring(store.read_bytes(a["settings"]))
        if s.get("identifier") != aid or not a["settings"].startswith(aid + "/"):
            out.append(("FAIL", "Assignment %s: identifier, folder and resource disagree" % aid))
        if a["group"] and a["group"] not in group_ids:
            out.append(("FAIL", "Assignment %r points to a missing assignment group" % a["title"]))
        if a["rubric"] and a["rubric"] not in c.rubrics:
            out.append(("FAIL", "Assignment %r points to a missing rubric" % a["title"]))
        if a["rubric"] in c.rubrics and abs(c.rubrics[a["rubric"]]["points"] - a["points"]) > 1e-9:
            out.append(("WARN", "Assignment %r: %s points, rubric totals %s" % (a["title"], a["points"], c.rubrics[a["rubric"]]["points"])))
    for tid, t in c.topics.items():
        if t["meta"]:
            try:
                m = ET.fromstring(store.read_bytes(c.resources[t["meta"]]["href"]))
                if m.findtext(cc("topic_id")) != tid:
                    out.append(("FAIL", "Discussion %s: its settings point to another topic" % tid))
            except (KeyError, CourseError, ET.ParseError):
                out.append(("FAIL", "Discussion %s: settings missing or unreadable" % tid))
        if t.get("rubric") and t["rubric"] not in c.rubrics:
            out.append(("FAIL", "Discussion %r points to a missing rubric" % t["title"]))
    if store.exists(RUBRICS) and 'href="%s"' % RUBRICS not in man_bytes.decode("utf-8"):
        out.append(("FAIL", "rubrics.xml exists but is not listed in the course-settings resource"))
    for rid in c.resources:
        if not ID_RE.match(rid) and not rid.endswith("_syllabus") and rid != c.course_id:
            out.append(("WARN", "Unusual identifier %s" % rid))
            break
    return out


def pack(store, out_path):
    out_path = os.path.abspath(out_path)
    overlay = {}
    if store.build and os.path.isdir(store.build):
        for dp, _, fn in os.walk(store.build):
            for f in fn:
                full = os.path.join(dp, f)
                overlay[os.path.relpath(full, store.build).replace(os.sep, "/")] = full
    done = set()
    tmp = out_path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        z = store.zip()
        if z is not None:
            for info in z.infolist():
                name = info.filename
                if name in overlay:
                    zi = zipfile.ZipInfo(name, date_time=info.date_time)
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    with open(overlay[name], "rb") as f:
                        zout.writestr(zi, f.read())
                    done.add(name)
                    continue
                zi = zipfile.ZipInfo(name, date_time=info.date_time)
                zi.compress_type = info.compress_type
                zi.external_attr = info.external_attr
                if name.endswith("/"):
                    zout.writestr(zi, b"")
                    continue
                with z.open(info) as src, zout.open(zi, "w") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                done.add(name)
        else:
            base = store.meta["path"] if store.meta.get("kind") == "dir" else store.src
            for dp, _, fn in os.walk(base):
                for f in sorted(fn):
                    full = os.path.join(dp, f)
                    name = os.path.relpath(full, base).replace(os.sep, "/")
                    zout.write(overlay.get(name, full), name)
                    done.add(name)
        for name in sorted(set(overlay) - done):
            zout.write(overlay[name], name)
    os.replace(tmp, out_path)
    return out_path


# ── a folder of materials → a minimal Canvas cartridge ──────────────────────────────

TEXT_EXT = (".md", ".markdown", ".txt", ".html", ".htm")


def from_folder(folder, work, title=None):
    """Build a Canvas cartridge in <work>/source from a folder: subfolders become modules, Markdown/HTML/text
    files become pages, other files are attached and linked from a page per module. A file named syllabus.*
    becomes the syllabus."""
    dest = os.path.join(work, "source")
    title = title or os.path.basename(os.path.abspath(folder))
    cid = "g" + hashlib.md5(("course:" + title).encode("utf-8")).hexdigest()
    os.makedirs(os.path.join(dest, "course_settings"), exist_ok=True)

    def w(rel, text):
        p = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    head = '<?xml version="1.0" encoding="UTF-8"?>\n'
    w("imsmanifest.xml", head + (
        '<manifest identifier="%s" xmlns="%s" xmlns:lom="http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource" '
        'xmlns:lomimscc="http://ltsc.ieee.org/xsd/imsccv1p1/LOM/manifest" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1 http://www.imsglobal.org/profile/cc/ccv1p1/ccv1p1_imscp_v1p2_v1p0.xsd '
        'http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource http://www.imsglobal.org/profile/cc/ccv1p1/LOM/ccv1p1_lomresource_v1p0.xsd '
        'http://ltsc.ieee.org/xsd/imsccv1p1/LOM/manifest http://www.imsglobal.org/profile/cc/ccv1p1/LOM/ccv1p1_lommanifest_v1p0.xsd">\n'
        '  <metadata>\n    <schema>IMS Common Cartridge</schema>\n    <schemaversion>1.1.0</schemaversion>\n'
        '    <lomimscc:lom>\n      <lomimscc:general>\n        <lomimscc:title>\n          <lomimscc:string>%s</lomimscc:string>\n'
        '        </lomimscc:title>\n      </lomimscc:general>\n    </lomimscc:lom>\n  </metadata>\n'
        '  <organizations>\n    <organization identifier="org_1" structure="rooted-hierarchy">\n'
        '      <item identifier="LearningModules">\n      </item>\n    </organization>\n  </organizations>\n'
        '  <resources>\n'
        '    <resource identifier="%s" type="%s" href="course_settings/canvas_export.txt">\n'
        '      <file href="course_settings/course_settings.xml"/>\n      <file href="course_settings/module_meta.xml"/>\n'
        '      <file href="course_settings/assignment_groups.xml"/>\n      <file href="course_settings/files_meta.xml"/>\n'
        '      <file href="course_settings/media_tracks.xml"/>\n      <file href="course_settings/canvas_export.txt"/>\n'
        '    </resource>\n'
        '    <resource identifier="%s_syllabus" type="%s" href="course_settings/syllabus.html" intendeduse="syllabus">\n'
        '      <file href="course_settings/syllabus.html"/>\n    </resource>\n'
        '  </resources>\n</manifest>\n') % ("g" + hashlib.md5(("manifest:" + title).encode()).hexdigest(), NS_CP, x(title),
                                           cid, LAR, cid, LAR))
    w(COURSE_SETTINGS, head + '<course identifier="%s" %s>\n  <title>%s</title>\n  <course_code>%s</course_code>\n'
      '  <default_view>modules</default_view>\n</course>\n' % (cid, CANVAS_XSI, x(title), x(title[:40])))
    w(MODULE_META, head + "<modules %s>\n</modules>\n" % CANVAS_XSI)
    w(GROUPS, head + '<assignmentGroups %s>\n  <assignmentGroup identifier="%s">\n    <title>Assignments</title>\n'
      '    <position>1</position>\n    <group_weight>0.0</group_weight>\n  </assignmentGroup>\n</assignmentGroups>\n'
      % (CANVAS_XSI, "g" + hashlib.md5(("group:" + title).encode()).hexdigest()))
    w("course_settings/files_meta.xml", head + "<fileMeta %s>\n  <files>\n  </files>\n</fileMeta>\n" % CANVAS_XSI)
    w("course_settings/media_tracks.xml", head + "<media_tracks %s>\n</media_tracks>\n" % CANVAS_XSI)
    w("course_settings/canvas_export.txt", "Built by ai-readiness from a folder of materials.\n")
    syllabus_body = "<p>No syllabus file was found in the folder.</p>"
    entries = sorted(os.listdir(folder))
    for name in entries:
        if name.lower().startswith("syllabus") and name.lower().endswith(TEXT_EXT):
            syllabus_body = _file_html(os.path.join(folder, name))
    w(SYLLABUS, '<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n'
      '<title>Syllabus</title>\n</head>\n<body>\n%s\n</body>\n</html>\n' % syllabus_body)
    store = Store(work, overlay=False)
    ed = Editor(store)
    groups = []
    loose = [n for n in entries if os.path.isfile(os.path.join(folder, n)) and not n.startswith(".")
             and not n.lower().startswith("syllabus")]
    if loose:
        groups.append(("Course materials", folder, loose))
    for n in entries:
        p = os.path.join(folder, n)
        if os.path.isdir(p) and not n.startswith("."):
            files = []
            for dp, dn, fn in os.walk(p):
                dn[:] = sorted(d for d in dn if not d.startswith("."))
                files += [os.path.relpath(os.path.join(dp, f), p) for f in sorted(fn) if not f.startswith(".")]
            t_ = re.sub(r"^\d+[-_ ]*", "", n).replace("-", " ").replace("_", " ").strip() or n
            groups.append((t_[:1].upper() + t_[1:], p, files))
    for mtitle, base, files in groups:
        ed.add_module(mtitle, "end", True, "folder:" + base)
        attachments = []
        for rel in files:
            full = os.path.join(base, rel)
            if rel.lower().endswith(TEXT_EXT):
                body = _file_html(full)
                ptitle = _first_heading(full) or os.path.splitext(os.path.basename(rel))[0].replace("-", " ").replace("_", " ")
                ed.add_page(mtitle, ptitle, body, "end", True, "folder:" + full)
            else:
                attachments.append((rel, full))
        if attachments:
            links = []
            for rel, full in attachments:
                web = "web_resources/%s/%s" % (slugify(mtitle), rel.replace(os.sep, "/"))
                with open(full, "rb") as f:
                    ed.write(web, f.read(), "file %s" % rel)
                fid = ed.new_id("file:" + full)
                ed.add_resource('<resource type="webcontent" identifier="%s" href="%s">\n  <file href="%s"/>\n</resource>'
                                % (fid, x(web), x(web)))
                url = "$IMS-CC-FILEBASE$/" + "/".join(_pct(p) for p in web[len(MEDIA):].split("/"))
                links.append('<li><a href="%s">%s</a></li>' % (url, html.escape(rel)))
                ed.refresh()
            ed.add_page(mtitle, "Files: %s" % mtitle, "<ul>\n%s\n</ul>" % "\n".join(links), "end", True,
                        "folder-files:" + base)
    _flush(ed, dest)


def _flush(ed, dest):
    for rel, content in ed.files.items():
        p = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(content.encode("utf-8") if isinstance(content, str) else content)


def _pct(s):
    from urllib.parse import quote
    return quote(s)


def _file_html(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    low = path.lower()
    if low.endswith((".html", ".htm")):
        m = re.search(r"<body[^>]*>(.*)</body>", text, re.S | re.I)
        return m.group(1).strip() if m else text
    if low.endswith(".txt"):
        return "\n".join("<p>%s</p>" % html.escape(p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip())
    return md_to_html(text)


def _first_heading(path):
    if not path.lower().endswith((".md", ".markdown")):
        return None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"^#\s+(.+)", line)
            if m:
                return m.group(1).strip()
    return None
