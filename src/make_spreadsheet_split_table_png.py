"""Render the SpreadsheetBench single-turn runs (baseline vs the
spreadsheet_edit text skill) as a PNG table, split by the benchmark's own
instruction_type field: Cell-Level vs Sheet-Level Manipulation. Same layout
as src/make_meta_split_table_png.py.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.make_meta_split_table_png import render  # noqa: E402

MODELS = ["qwen3-8b", "qwen3-14b", "qwen3.6-27b"]
COLS = ["baseline", "text_spreadsheet_edit"]
PRETTY = {"baseline": "baseline\n(no skill)",
          "text_spreadsheet_edit": "spreadsheet_edit\n(text skill)"}
SUBSETS = [("All", None), ("Cell-Level", "Cell-Level Manipulation"),
           ("Sheet-Level", "Sheet-Level Manipulation")]
SCALE = 7  # same as the original results table; deltas here stay within it


def load(model, cond):
    out = {}
    for s in (0, 1):
        p = os.path.join(ROOT, "results", f"spreadsheet_{model}_{cond}_s{s}of2.json")
        for r in json.load(open(p))["records"]:
            out[r["id"]] = (float(r["em"]) > 0, r["instruction_type"])
    return out


def main():
    rows = []
    for m in MODELS:
        full = {c: load(m, c) for c in COLS}
        n_all = len(full[COLS[0]])
        for name, itype in SUBSETS:
            cells = {c: {i: ok for i, (ok, t) in full[c].items() if itype in (None, t)}
                     for c in COLS}
            desc = (f"all {n_all} tasks" if itype is None
                    else itype.lower().replace(" manipulation", " edits"))
            rows.append((m, name, desc, cells))

    render(rows, COLS, PRETTY, "SpreadsheetBench (single-turn): spreadsheet_edit skill",
           ["Split by the benchmark's instruction_type: Cell-Level = write values into a "
            "target range; Sheet-Level = restructure the sheet."],
           SCALE, os.path.join(ROOT, "results_table_spreadsheet_split.png"))


if __name__ == "__main__":
    main()
