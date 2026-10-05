"""SpreadsheetBench grader: compare a produced .xlsx against the golden file.

Only the task's declared answer range on the declared sheet is compared, which
is how SpreadsheetBench defines success -- the agent may leave anything else in
the workbook untouched or altered.

Cell comparison is value-based with numeric tolerance, because two spreadsheets
that display the same thing can differ in storage (int vs float, trailing
whitespace, or a formula vs its computed value). Formulas are read with
data_only=True so a cached computed value is used where present.
"""
from __future__ import annotations

import json
import os

import re

import openpyxl
from openpyxl.utils import range_boundaries

# The dataset's quoting is inconsistent: some qualifiers lost their opening
# quote ("Sheet1'!A1:F14"), answer_sheet is sometimes a comma-separated list
# ("'Sheet1','Sheet2'"), and ranges may be whole-column ("A:G").
_RANGE = re.compile(
    r"""^\s*'?(?P<sheet>[^'!]+)'?\s*!\s*(?P<rng>.+?)\s*$|^\s*(?P<bare>.+?)\s*$""",
    re.X)
_COLONLY = re.compile(r"^\$?([A-Za-z]{1,3})\s*:\s*\$?([A-Za-z]{1,3})$")
_ROWONLY = re.compile(r"^\$?(\d+)\s*:\s*\$?(\d+)$")


def split_outside_quotes(spec: str) -> list[str]:
    """Split on commas that are not inside single quotes."""
    out, buf, inq = [], [], False
    for ch in spec:
        if ch == "'":
            inq = not inq
        if ch == "," and not inq:
            out.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


def parse_sheets(answer_sheet, existing: list[str] | None = None) -> list[str]:
    """answer_sheet may be None, one name, or a comma-separated list.

    A sheet name can itself contain commas ('b2b, sez, de'), which is
    syntactically identical to a list of three sheets. Resolve the ambiguity
    against the workbook: if the whole string names a real sheet, it is one
    sheet; otherwise split it.
    """
    if not answer_sheet:
        return []
    whole = str(answer_sheet).strip().strip("'")
    if existing and whole in existing:
        return [whole]
    return [x.strip().strip("'") for x in split_outside_quotes(str(answer_sheet))]


_TOKEN = re.compile(r"""
    (?:                                            # optional sheet qualifier
        '(?P<qsheet>[^']+)'\s*!\s*                  #   'Name, with commas'!
      | (?P<sheet>[^,'!]+)'?\s*!\s*                 #   Name!  or  Name'!  (lost quote)
    )?
    (?P<rng>
        \$?[A-Za-z]{1,3}\$?\d+\s*:\s*\$?[A-Za-z]{1,3}\$?\d+   # A1:B2
      | \$?[A-Za-z]{1,3}\s*:\s*\$?[A-Za-z]{1,3}                  # A:G
      | \$?\d+\s*:\s*\$?\d+                                    # 2:10
      | \$?[A-Za-z]{1,3}\$?\d+                                    # A1
    )""", re.X)


def parse_ranges(spec: str, default_sheets: list[str]):
    """Return [(sheet, range), ...].

    Scans for range tokens rather than splitting on commas: the dataset's
    quoting is unbalanced often enough ("Sheet1'!A1:F14") that any
    quote-aware splitter mis-groups the parts.
    A token with no qualifier applies to every sheet in default_sheets.
    """
    out = []
    for m in _TOKEN.finditer(spec):
        rng = m.group("rng").replace("$", "").replace(" ", "")
        sh = m.group("qsheet") or m.group("sheet")
        if sh:
            out.append((sh.strip(), rng))
        else:
            out.extend((sh, rng) for sh in default_sheets)
    return out


def bounded(rng: str, ws):
    """Resolve whole-column (A:G) / whole-row (2:10) ranges against the sheet."""
    m = _COLONLY.match(rng)
    if m:
        return f"{m.group(1)}1:{m.group(2)}{max(ws.max_row, 1)}"
    m = _ROWONLY.match(rng)
    if m:
        from openpyxl.utils import get_column_letter
        last = get_column_letter(max(ws.max_column, 1))
        return f"A{m.group(1)}:{last}{m.group(2)}"
    return rng


NUM_TOL = 1e-6


def _norm(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return s.lower()


def cells_equal(a, b) -> bool:
    a, b = _norm(a), _norm(b)
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= NUM_TOL * max(1.0, abs(a), abs(b))
    return a == b


def compare(produced_path: str, golden_path: str, sheet: str | None, cell_range: str):
    """Return (passed, n_cells, n_mismatch, note)."""
    try:
        wp = openpyxl.load_workbook(produced_path, data_only=True)
        wg = openpyxl.load_workbook(golden_path, data_only=True)
    except Exception as e:
        return False, 0, 0, f"load error: {type(e).__name__}: {e}"
    # Cell-level tasks carry no answer_sheet and often no qualifier in the
    # range; those are graded on the workbook's active sheet.
    sheets = parse_sheets(sheet, wg.sheetnames) or [wg.active.title]
    parts = parse_ranges(cell_range, sheets)
    if not parts:
        return False, 0, 0, f"unparseable answer_position {cell_range!r}"
    n = mism = 0
    for sh, rng in parts:
        if sh not in wp.sheetnames:
            return False, n, mism, f"missing sheet {sh!r} (has {wp.sheetnames})"
        if sh not in wg.sheetnames:
            return False, n, mism, f"golden missing sheet {sh!r}"
        sp, sg = wp[sh], wg[sh]
        c1, r1, c2, r2 = range_boundaries(bounded(rng, sg))
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                n += 1
                if not cells_equal(sp.cell(r, c).value, sg.cell(r, c).value):
                    mism += 1
    return mism == 0, n, mism, ""


def task_files(root: str, task: dict):
    d = os.path.join(root, task["spreadsheet_path"])
    # Most task dirs use "<n>_<id>_init.xlsx"/"..._golden.xlsx", but a handful
    # ship plain "initial.xlsx"/"golden.xlsx".
    init = golden = None
    for f in sorted(os.listdir(d)):
        if not f.endswith(".xlsx"):
            continue
        low = f.lower()
        if low.endswith("_init.xlsx") or low in ("init.xlsx", "initial.xlsx"):
            init = os.path.join(d, f)
        elif low.endswith("_golden.xlsx") or low == "golden.xlsx":
            golden = os.path.join(d, f)
    return init, golden


def selfcheck(root: str, limit: int = 400):
    """Sanity: golden-vs-golden must pass; init-vs-golden mostly must not.

    If golden-vs-golden is not ~100%, the grader is wrong and every downstream
    number is meaningless. If init-vs-golden is also ~100%, the tasks are
    no-ops and the benchmark measures nothing.
    """
    tasks = [t for t in json.load(open(os.path.join(root, "dataset.json")))
             if "exclude" not in t][:limit]
    gg = ig = bad = 0
    notes = []
    for t in tasks:
        init, golden = task_files(root, t)
        if not init or not golden:
            bad += 1
            continue
        sh = t.get("answer_sheet")
        ok, _, _, note = compare(golden, golden, sh, t["answer_position"])
        gg += ok
        if not ok and note:
            notes.append((t["id"], note))
        ok2, *_ = compare(init, golden, sh, t["answer_position"])
        ig += ok2
    n = len(tasks) - bad
    print(f"tasks checked            : {n} (missing files: {bad})")
    print(f"golden vs golden  PASS   : {gg}/{n}  ({gg/max(n,1)*100:.1f}%)   <- must be 100%")
    print(f"init   vs golden  PASS   : {ig}/{n}  ({ig/max(n,1)*100:.1f}%)   <- the do-nothing score")
    if notes:
        print(f"\ngolden-vs-golden failures ({len(notes)}), first 5:")
        for i, note in notes[:5]:
            print(f"   {i}: {note[:120]}")


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "spreadsheetbench_verified_400")
    selfcheck(root)
