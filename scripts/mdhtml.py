"""Markdown to HTML (for drafts going into Canvas) and HTML to text (for reading a course).

md_to_html is ported from Nik Bear Brown's build-imscc-standard.py
(bear-textbooks/books/data-driven-design-with-figma), standard library only.
"""
import html
import re
from html.parser import HTMLParser

_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<![\*\w])\*([^*]+)\*(?![\*\w])")
_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline(text):
    """Escape HTML, then apply inline markdown. Code spans are protected."""
    spans = []

    def stash(m):
        spans.append(html.escape(m.group(1)))
        return "\x00%d\x00" % (len(spans) - 1)

    text = _INLINE_CODE.sub(stash, text)
    text = html.escape(text, quote=False)
    text = _IMG.sub(lambda m: '<img src="%s" alt="%s" />' % (m.group(2), m.group(1)), text)
    text = _LINK.sub(lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % spans[int(m.group(1))], text)
    return text


_BLOCK_START = re.compile(r"^(#{1,6}\s|```|\s*[-*+]\s|\s*\d+[.)]\s|>|\s*\|)")
# Lines that are raw HTML block tags pass through unchanged (Canvas keeps them): <details>, <summary>, <div>, ...
RAW_BLOCK = re.compile(r"^\s*</?(details|summary|div|section|figure|figcaption|iframe|table|thead|tbody|tr|td|th|"
                       r"br|hr|img|video|audio|source)\b[^>]*>.*$", re.I)


def md_to_html(md):
    out = []
    lines = md.replace("\r\n", "\n").split("\n")
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.lstrip().startswith("<!--"):
            while "-->" not in line and i + 1 < n:
                i += 1
                line = lines[i]
            i += 1
            continue
        if RAW_BLOCK.match(line):
            out.append(line.strip())
            i += 1
            continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(code)))
            continue
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, _inline(m.group(2).strip()), lvl))
            i += 1
            continue
        if re.match(r"^(\*{3,}|-{3,}|_{3,})\s*$", line):
            out.append("<hr />")
            i += 1
            continue
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1]):
            def cells(row):
                row = row.strip().replace("\\|", "\x01")
                return [c.strip().replace("\x01", "|") for c in row.strip("|").split("|")]
            header = cells(line)
            i += 2
            body = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append(cells(lines[i]))
                i += 1
            t = ['<table class="ic-Table">', "<thead><tr>"]
            t += ["<th>%s</th>" % _inline(c) for c in header]
            t.append("</tr></thead><tbody>")
            for r in body:
                t.append("<tr>" + "".join("<td>%s</td>" % _inline(c) for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue
        if line.lstrip().startswith(">"):
            quote = []
            while i < n and lines[i].lstrip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote><p>%s</p></blockquote>" % _inline(" ".join(quote)))
            continue
        if re.match(r"^\s*[-*+]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]):
                item = re.sub(r"^\s*[-*+]\s+", "", lines[i])
                i += 1
                while i < n and lines[i].startswith("  ") and lines[i].strip() and not re.match(r"^\s*[-*+]\s+", lines[i]):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(item)
            out.append("<ul>" + "".join("<li>%s</li>" % _inline(it) for it in items) + "</ul>")
            continue
        if re.match(r"^\s*\d+[.)]\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                item = re.sub(r"^\s*\d+[.)]\s+", "", lines[i])
                i += 1
                while i < n and lines[i].startswith("  ") and lines[i].strip() and not re.match(r"^\s*\d+[.)]\s+", lines[i]):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(item)
            out.append("<ol>" + "".join("<li>%s</li>" % _inline(it) for it in items) + "</ol>")
            continue
        para = [line]
        i += 1
        while i < n and lines[i].strip() and not _BLOCK_START.match(lines[i]) and not RAW_BLOCK.match(lines[i]):
            para.append(lines[i])
            i += 1
        out.append("<p>%s</p>" % _inline(" ".join(s.strip() for s in para)))
    return "\n".join(out)


class _Text(HTMLParser):
    """HTML to readable Markdown-ish text, so an agent can read a course without parsing HTML."""

    BLOCK = {"p", "div", "section", "article", "br", "tr", "table", "ul", "ol", "blockquote", "pre", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.href = None
        self.skip = 0
        self.list_stack = []
        self.cell = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        elif re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("ul", "ol"):
            self.list_stack.append([tag, 0])
            self.out.append("\n")
        elif tag == "li":
            depth = max(len(self.list_stack) - 1, 0)
            if self.list_stack and self.list_stack[-1][0] == "ol":
                self.list_stack[-1][1] += 1
                self.out.append("\n" + "  " * depth + "%d. " % self.list_stack[-1][1])
            else:
                self.out.append("\n" + "  " * depth + "- ")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag == "a":
            self.href = a.get("href")
        elif tag == "img":
            self.out.append("[image: %s]" % (a.get("alt") or a.get("src") or ""))
        elif tag == "iframe":
            self.out.append("\n[embedded: %s]\n" % (a.get("title") or a.get("src") or ""))
        elif tag in self.BLOCK:
            self.out.append("\n\n" if tag in ("p", "div", "section", "blockquote", "table") else "\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(self.skip - 1, 0)
        elif tag in ("ul", "ol") and self.list_stack:
            self.list_stack.pop()
            self.out.append("\n")
        elif tag == "a":
            if self.href and not self.href.startswith("#"):
                self.out.append(" (%s)" % self.href)
            self.href = None
        elif re.fullmatch(r"h[1-6]", tag) or tag in ("p", "tr"):
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(re.sub(r"\s+", " ", data))


def html_to_text(s):
    p = _Text()
    p.feed(s or "")
    p.close()
    text = "".join(p.out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+(?=[^-\d\s])", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
