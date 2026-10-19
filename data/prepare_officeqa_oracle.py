"""OfficeQA as a text-only task: question + the cited bulletin page(s) in the prompt.

    python data/prepare_officeqa_oracle.py        # -> data/officeqa_oracle.jsonl

This is the setting SkillOpt calls "offline, no tools" (envs/officeqa, commit
343db22): each question's `source_docs` URLs name the PDF page the answer is on
(`...?page=14`), and the page text comes from Databricks' parsed bulletins
(`treasury_bulletins_parsed/jsons/<file>.json`, elements tagged with page ids).
The page rendering below is a copy of SkillOpt's tool_runtime helpers (MIT), so
the context is byte-identical to theirs, capped like theirs at 24k chars per
page and 80k chars in total (~20k tokens, fits every model's context).

Unlike the agent arm (04_officeqa_agent/), no search is needed: the model is
told where to look. It is a reading-and-arithmetic task over tables.

Needs the gated files (see DATA.md):
    data/officeqa_full.csv                      uid, question, answer, source_docs, source_files
    data/officeqa_parsed/jsons/<file>.json      only the 285 cited bulletins
Tolerances come from data/officeqa.jsonl (prepare_officeqa.py).
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
JSONS = os.path.join(HERE, "officeqa_parsed", "jsons")
MAX_PAGE_CHARS, MAX_TOTAL_CHARS = 24000, 80000


def as_list(value):
    text = str(value or "").strip()
    return [p.strip() for p in text.splitlines() if p.strip()] if text else []


def page_number(url):
    q = parse_qs(urlparse(url).query)
    for key in ("page", "pagenum", "page_id"):
        for v in q.get(key, []):
            try:
                return int(v)
            except ValueError:
                pass
    m = re.search(r"(?:[?&]|^)page=(\d+)", url)
    return int(m.group(1)) if m else None


class _Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self._row, self._cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "tr":
            self._row = []
        elif tag.lower() in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif t == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = self._cell = None


def table_md(raw):
    p = _Table()
    try:
        p.feed(raw)
    except Exception:  # noqa: BLE001
        p.rows = []
    if not p.rows:
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?is)<[^>]+>", " ", raw))).strip()
    w = max(len(r) for r in p.rows)
    rows = [r + [""] * (w - len(r)) for r in p.rows]
    esc = lambda c: str(c).replace("\n", " ").replace("|", "\\|").strip()
    out = ["| " + " | ".join(esc(c) for c in rows[0]) + " |", "| " + " | ".join(["---"] * w) + " |"]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join(out)


def render_content(content):
    t = content.strip()
    if not t:
        return ""
    if "<table" in t.lower():
        return table_md(t)
    t = re.sub(r"\r\n?", "\n", html.unescape(t))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


_ELEMENTS = {}


def elements(path):
    if path not in _ELEMENTS:
        doc = json.load(open(path, encoding="utf-8")).get("document") or {}
        _ELEMENTS[path] = [e for e in doc.get("elements") or [] if isinstance(e, dict)]
    return _ELEMENTS[path]


def render_page(path, page):
    out = []
    for e in elements(path):
        ids = {int(b["page_id"]) for b in e.get("bbox") or [] if isinstance(b, dict)
               and str(b.get("page_id", "")).lstrip("-").isdigit()}
        if page in ids and isinstance(e.get("content"), str) and e["content"].strip():
            s = render_content(e["content"])
            if s:
                out.append(s)
    return "\n\n".join(out).strip()


def oracle_context(files, docs):
    refs, seen = [], set()
    for i, url in enumerate(docs):
        pg = page_number(url)
        if pg is None:
            continue
        f = files[i] if i < len(files) else files[0] if len(files) == 1 else None
        if f and (f, pg, url) not in seen:
            seen.add((f, pg, url))
            refs.append((f, pg, url))
    blocks, total, pages = [], 0, set()
    for f, pg, url in refs:
        path = os.path.join(JSONS, os.path.splitext(f)[0] + ".json")
        if not os.path.isfile(path) or (path, pg) in pages:
            continue
        pages.add((path, pg))
        text = render_page(path, pg)
        if not text:
            continue
        if len(text) > MAX_PAGE_CHARS:
            text = text[:MAX_PAGE_CHARS].rstrip() + \
                f"\n\n[... {len(text) - MAX_PAGE_CHARS} characters omitted from this parsed page ...]"
        block = f"### {f} page {pg}\nSource URL: {url}\n\n{text}"
        if total + len(block) > MAX_TOTAL_CHARS:
            rest = MAX_TOTAL_CHARS - total
            if rest > 0:
                blocks.append(block[:rest].rstrip() + "\n\n[... oracle parsed page context truncated ...]")
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks), len(pages)


def main():
    tol = {r["id"]: r for r in map(json.loads, open(os.path.join(HERE, "officeqa.jsonl")))}
    out, empty = [], 0
    for r in csv.DictReader(open(os.path.join(HERE, "officeqa_full.csv"), encoding="utf-8")):
        files = [f if f.endswith(".txt") else f + ".txt" for f in as_list(r["source_files"])]
        ctx, n_pages = oracle_context(files, as_list(r["source_docs"]))
        if not ctx:
            empty += 1
        out.append({"id": r["uid"], "question": r["question"], "answer": r["answer"],
                    "source_files": files, "difficulty": r["difficulty"],
                    "tolerance": tol.get(r["uid"], {}).get("tolerance", 0.01),
                    "n_pages": n_pages, "context": ctx})
    with open(os.path.join(HERE, "officeqa_oracle.jsonl"), "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    chars = sorted(len(r["context"]) for r in out)
    print(f"wrote {len(out)} questions; {empty} with no page context; context chars "
          f"median {chars[len(chars) // 2]}, max {chars[-1]}")


if __name__ == "__main__":
    main()
