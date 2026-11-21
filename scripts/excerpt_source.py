#!/usr/bin/env python3
"""Turn a source document (PDF, HTML or text) into a compact, searchable excerpt.

Maintainers use this script to prepare plain-text excerpts for checking
citations locally. The specs refer to inputs kept outside version control,
including originals under docs/refs/. The generated excerpts under
skills/explainer-guide/sources/ also stay outside version control.

Two commands:

    # 1. Look at the full extracted text to choose start and end markers.
    python3 -I scripts/excerpt_source.py dump INPUT [--html-root XPATH] [--reflow] [--out FILE]

    # 2. Build excerpts after supplying the local inputs named in the specs.
    python3 -I scripts/excerpt_source.py build scripts/explainer_sources/*.json

A spec file is JSON:

    {
      "output": "skills/explainer-guide/sources/<name>.md",
      "input": "docs/refs/.../original.pdf",
      "title": "Title of the source",
      "author": "Author or organisation",
      "source_url": "https://...",
      "scope": "Which parts are included, in Chinese",
      "cited_by": "Which reference files cite it, in Chinese",
      "license": "Copyright note, in Chinese",
      "html_root": "//main",            (optional, HTML only; default //body)
      "html_drop": ["//aside"],         (optional, extra XPaths to remove)
      "reflow": true,                   (optional; join lines broken by layout)
      "drop_lines": ["^regex$"],        (optional; lines to delete, e.g. running headers)
      "sections": [                     (optional; default is the whole text)
        {"start": "exact text", "end": "exact text", "occurrence": 1,
         "label": "where this part comes from",   (optional)
         "input": "another original",              (optional; overrides the spec's)
         "reflow": true, "drop_lines": [], "html_root": "..."}   (optional overrides)
      ]
    }

Markers are matched against the same text that "dump" prints with the same
options, so copy them from the dump. "end" is included in the excerpt.
"start" finds its first occurrence, which may be in a table of contents; use a
longer marker or "occurrence" to pick the right one. Labels are printed in
〔〕 brackets, which the header explains as notes added by the excerpt.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CJK = r"⺀-⿿　-〿぀-ヿ㐀-䶿一-鿿豈-﫿＀-￯"
CJK_SPACE_RE = re.compile(rf"(?<=[{CJK}])[ \t]+(?=[{CJK}])")
PAGE_MARK = "〔PDF 第 {n} 页〕"
PAGE_MARK_RE = re.compile(r"^〔PDF 第 \d+ 页〕$")
GAP = "〔……〕"

HEADER_NOTE = (
    "以下是原文的逐字摘录。处理只有这几项：从 PDF 或网页里提取纯文本，"
    "合并排版造成的断行，删去页眉页脚和网页导航。"
    "六角括号“〔〕”里的文字都是摘录时加的：“〔PDF 第 N 页〕”标出 PDF 文件的页码，"
    "和印刷的页码可能不同；“〔……〕”表示中间有省略；其他的说明下面一段出自哪里。"
)

DROP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "svg", "button", "form", "template", "iframe"}
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "dd", "details", "dialog", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "hr", "li", "main", "ol", "p", "pre", "section",
    "summary", "table", "tbody", "thead", "tfoot", "tr", "ul", "caption",
}
HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


# ---------------------------------------------------------------- extraction

def pdf_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(path), "-"],
        capture_output=True, check=True,
    )
    pages = result.stdout.decode("utf-8", errors="replace").split("\f")
    parts = []
    for number, page in enumerate(pages, 1):
        if not page.strip():
            continue
        parts.append(PAGE_MARK.format(n=number))
        parts.append(page)
    return "\n\n".join(parts)


class HtmlText:
    """A small HTML-to-text renderer that keeps headings, list items and table rows."""

    def __init__(self):
        self.blocks: list[str] = []
        self.line: list[str] = []

    def flush(self):
        text = re.sub(r"\s+", " ", "".join(self.line)).strip()
        if text:
            self.blocks.append(text)
        self.line = []

    def add(self, text: str | None):
        if text:
            self.line.append(text)

    def walk(self, el):
        tag = el.tag.lower() if isinstance(el.tag, str) else ""
        if tag in DROP_TAGS or not tag:
            self.add(el.tail)
            return
        if tag in HEADINGS:
            self.flush()
            heading = re.sub(r"\s+", " ", el.text_content()).strip()
            if heading:
                self.blocks.append("#" * HEADINGS[tag] + " " + heading)
            self.add(el.tail)
            return
        if tag == "pre":
            self.flush()
            self.blocks.append(el.text_content().rstrip())
            self.add(el.tail)
            return
        if tag == "br":
            self.flush()
            self.add(el.tail)
            return
        if tag == "img":
            alt = (el.get("alt") or "").strip()
            if alt:
                self.add(f"[图：{alt}]")
            self.add(el.tail)
            return
        block = tag in BLOCK_TAGS
        if block:
            self.flush()
        if tag == "li":
            self.add("- ")
        if tag in ("td", "th") and self.line:
            self.add(" | ")
        self.add(el.text)
        for child in el:
            self.walk(child)
        if block:
            self.flush()
        self.add(el.tail)

    def text(self) -> str:
        self.flush()
        return "\n\n".join(self.blocks)


def html_text(path: Path, root_xpath: str | None, drop_xpaths: list[str]) -> str:
    import lxml.html

    parser = lxml.html.HTMLParser(encoding="utf-8")
    doc = lxml.html.fromstring(path.read_bytes(), parser=parser)
    for xpath in drop_xpaths:
        for el in doc.xpath(xpath):
            el.drop_tree()
    roots = doc.xpath(root_xpath or "//body")
    if not roots:
        sys.exit(f"html_root {root_xpath!r} matched nothing in {path}")
    renderer = HtmlText()
    for root in roots:
        renderer.walk(root)
        renderer.flush()
    return renderer.text()


# ------------------------------------------------------------- normalising

def join_lines(prev: str, nxt: str) -> str:
    if not prev:
        return nxt
    if re.search(rf"[{CJK}]$", prev) and re.match(rf"[{CJK}]", nxt):
        return prev + nxt
    if prev.endswith("-") and re.match(r"[a-z]", nxt):
        return prev + nxt
    return prev + " " + nxt


BULLET_RE = re.compile(r"^[•◦▪●○■□▶►–]\s")


def reflow(text: str) -> str:
    """Join lines inside a paragraph; paragraphs are separated by blank lines.

    A line that starts with a bullet starts a new line, so list items stay apart.
    """
    out = []
    for para in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in para.splitlines() if line.strip()]
        rows: list[str] = []
        merged = ""
        for line in lines:
            if PAGE_MARK_RE.match(line):
                if merged:
                    rows.append(merged)
                    merged = ""
                if rows:
                    out.append("\n".join(rows))
                    rows = []
                out.append(line)
                continue
            if BULLET_RE.match(line) and merged:
                rows.append(merged)
                merged = line
                continue
            merged = join_lines(merged, line)
        if merged:
            rows.append(merged)
        if rows:
            out.append("\n".join(rows))
    # A blank line in the PDF text sometimes falls inside a sentence. If the
    # previous block ends with a lowercase letter, a comma or a hyphen and the
    # next one starts with a lowercase letter, they are one paragraph. Blocks
    # ending in digits are left alone, because table rows often do.
    joined: list[str] = []
    for block in out:
        if (joined and LOWER_START_RE.match(block) and not PAGE_MARK_RE.match(joined[-1])
                and MID_SENTENCE_END_RE.search(joined[-1])):
            joined[-1] = join_lines(joined[-1], block)
        else:
            joined.append(block)
    return "\n\n".join(joined)


LOWER_START_RE = re.compile(r"[a-z]")
MID_SENTENCE_END_RE = re.compile(r"[a-z,\-\u2013]$")

NBSP = "\u00a0"
ZERO_WIDTH = "\u200b"
# Bullets drawn with Symbol or Wingdings fonts come out of pdftotext as
# private-use code points; map them to the bullet they show on the page.
FONT_BULLETS = {"\uf0a7": "\u25aa", "\uf0b7": "\u2022"}


def normalise(text: str, do_reflow: bool, drop_lines: list[str]) -> str:
    text = text.replace("\r\n", "\n").replace(NBSP, " ").replace(ZERO_WIDTH, "")
    for glyph, bullet in FONT_BULLETS.items():
        text = text.replace(glyph, bullet)
    patterns = [re.compile(p) for p in drop_lines]
    kept = []
    for line in text.split("\n"):
        line = line.rstrip()
        if any(p.search(line) for p in patterns):
            continue
        kept.append(line)
    text = "\n".join(kept)
    if do_reflow:
        text = reflow(text)
    text = "\n".join(CJK_SPACE_RE.sub("", line) for line in text.split("\n"))
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def load_text(input_path: Path, spec: dict) -> str:
    suffix = input_path.suffix.lower()
    if suffix == ".pdf":
        raw = pdf_text(input_path)
    elif suffix in (".html", ".htm"):
        raw = html_text(input_path, spec.get("html_root"), spec.get("html_drop", []))
    else:
        raw = input_path.read_text(encoding="utf-8", errors="replace")
    return normalise(raw, spec.get("reflow", False), spec.get("drop_lines", []))


# --------------------------------------------------------------- excerpting

def find_nth(text: str, needle: str, n: int, start: int = 0) -> int:
    pos = start - 1
    for _ in range(n):
        pos = text.find(needle, pos + 1)
        if pos < 0:
            return -1
    return pos


def last_page_mark(text: str, before: int) -> str | None:
    marks = list(re.finditer(r"〔PDF 第 \d+ 页〕", text[:before]))
    return marks[-1].group(0) if marks else None


INPUT_OPTIONS = ("html_root", "html_drop", "reflow", "drop_lines")


class Texts:
    """Extracted texts, keyed by input path and options, so each input is read once."""

    def __init__(self, spec: dict):
        self.spec = spec
        self.cache: dict[str, str] = {}

    def options(self, sec: dict) -> dict:
        """Section-level options override the spec-level ones."""
        return {key: sec.get(key, self.spec.get(key)) for key in INPUT_OPTIONS}

    def get(self, sec: dict) -> tuple[str, str]:
        rel = sec.get("input") or self.spec.get("input")
        if not rel:
            sys.exit("every section needs an input, either its own or the spec's")
        opts = self.options(sec)
        key = rel + json.dumps(opts, sort_keys=True)
        if key not in self.cache:
            self.cache[key] = load_text(PROJECT_ROOT / rel, {k: v for k, v in opts.items() if v is not None})
        return rel, self.cache[key]


def cut_sections(texts: Texts, sections: list[dict], name: str) -> str:
    if not sections:
        return texts.get({})[1].strip()
    pieces = []
    for index, sec in enumerate(sections, 1):
        _, text = texts.get(sec)
        start = find_nth(text, sec["start"], sec.get("occurrence", 1))
        if start < 0:
            sys.exit(f"{name}: section {index}: start marker not found: {sec['start']!r}")
        end = text.find(sec["end"], start)
        if end < 0:
            sys.exit(f"{name}: section {index}: end marker not found after start: {sec['end']!r}")
        piece = text[start:end + len(sec["end"])].strip()
        mark = last_page_mark(text, start)
        if mark and not piece.startswith("〔PDF"):
            piece = mark + "\n\n" + piece
        if sec.get("label"):
            piece = f"〔{sec['label']}〕\n\n" + piece
        pieces.append(piece)
    return f"\n\n{GAP}\n\n".join(pieces)


def render(spec: dict, body: str) -> str:
    # The excerpt header gives the citation details. The spec keeps the
    # local input paths for maintainers.
    rows = [
        ("作者或机构", spec.get("author")),
        ("原始网址", spec.get("source_url")),
        ("摘录范围", spec.get("scope")),
        ("引用它的查阅文件", spec.get("cited_by")),
        ("版权说明", spec.get("license")),
    ]
    head = [f"# {spec['title']}", ""]
    head += [f"- {key}：{value}" for key, value in rows if value]
    head += ["", HEADER_NOTE, "", "---", "", ""]
    return "\n".join(head) + body.strip() + "\n"


def build(spec_path: Path):
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    texts = Texts(spec)
    body = cut_sections(texts, spec.get("sections", []), spec_path.name)
    out_path = PROJECT_ROOT / spec["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(spec, body), encoding="utf-8")
    size = out_path.stat().st_size
    print(f"{spec['output']}: {size // 1024} KB")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    dump = sub.add_parser("dump", help="print the full extracted text of one input")
    dump.add_argument("input", type=Path)
    dump.add_argument("--html-root")
    dump.add_argument("--reflow", action="store_true")
    dump.add_argument("--out", type=Path)

    b = sub.add_parser("build", help="build excerpts from spec files")
    b.add_argument("specs", type=Path, nargs="+")

    args = parser.parse_args()
    if args.command == "dump":
        spec = {"html_root": args.html_root, "reflow": args.reflow}
        text = load_text(args.input.resolve(), spec)
        if args.out:
            args.out.write_text(text, encoding="utf-8")
            print(f"wrote {len(text)} characters to {args.out}")
        else:
            sys.stdout.write(text)
    else:
        for spec_path in args.specs:
            build(spec_path)


if __name__ == "__main__":
    main()
