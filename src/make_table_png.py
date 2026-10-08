"""Render the results matrix as a PNG table.

Form: a table, not a chart. The data is a small grid of labelled values that
readers need to look up exactly, which is what tables are for.

Colour does exactly one job -- polarity of the delta versus that row's own
baseline -- as a CVD-safe blue/orange diverging pair with a neutral midpoint.
Significance is carried by text (bold + asterisk), never by colour alone.
Accuracy values are left uncoloured: they are magnitudes to be read, not
compared against a reference, so a fill would add ink without meaning.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.matrix import classify, mcnemar  # noqa: E402

# diverging pair: orange (negative) -- neutral -- blue (positive)
NEG, MID, POS = "#C2622D", "#EFEFEC", "#2C7FB8"
INK, INK2, INK3 = "#14181B", "#4A585E", "#7C8A90"
RULE, SURF, HEAD = "#D3DBDC", "#FFFFFF", "#EDF1F1"
CMAP = LinearSegmentedColormap.from_list("d", [NEG, MID, POS])

# @user-position arms are an ablation (skill in the user turn, no system
# prompt anywhere). Kept out of the headline grid; still in src/matrix.py.
COL_ORDER = ["baseline", "text", "embed/dummy", "embed/none", "CONTROL"]
PRETTY = {"baseline": "baseline\n(no skill)", "text": "text skill",
          "embed/dummy": "embed\nvs dummy", "embed/none": "embed\nvs nothing",
          "CONTROL": "CONTROL\ndummy only\n(no skill)",
          "text@usr": "text skill\n@user msg",
          "embed/none@usr": "embed\nvs nothing\n@user msg",
          "CONTROL@usr": "CONTROL\n@user msg"}
MSIZE = {"qwen3-8b": 8, "qwen3-14b": 14, "qwen3.6-27b": 27}
BORDER = {"LiveMath": 0, "SpreadsheetBench": 1, "OfficeQA": 2}


def collect():
    cells = defaultdict(dict)
    for p in sorted(glob.glob(os.path.join(ROOT, "results", "*.json"))):
        try:
            b = json.load(open(p))
        except Exception:
            continue
        if "summary" not in b or "records" not in b:
            continue
        if re.search(r"pilot", os.path.basename(p)):
            continue
        k = classify(b["summary"])
        if not k:
            continue
        bench, harness, model, col = k
        # A benchmark's own skill IS its text arm (spreadsheet_edit, officeqa_lookup).
        # Only LiveMath's ablation variants (v2/matched/notation/register, and
        # the archived compare_claims / compare_claims_v3) are extra conditions
        # and are left out of the headline grid. Folding compare_claims in here
        # would merge it with strength_audit by question id, silently.
        if col.startswith("text:"):
            variant = col.split(":", 1)[1].replace("@usr", "")
            if variant in ("v2", "v3", "claims", "matched", "notation", "register"):
                continue
            col = "text" + ("@usr" if col.endswith("@usr") else "")
        for r in b["records"]:
            cells[(bench, harness, model, col)][r["id"]] = r["em"]
    return cells


def main():
    cells = collect()
    rows = sorted({(b, h, m) for b, h, m, _ in cells},
                  key=lambda x: (BORDER.get(x[0], 9), x[1], MSIZE.get(x[2], 99)))
    cols = [c for c in COL_ORDER if any((b, h, m, c) in cells for b, h, m in rows)]

    nr, nc = len(rows), len(cols)
    fig_w = 3.6 + 1.35 * nc
    fig_h = 2.5 + 0.62 * nr
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=210)
    ax.set_xlim(0, 3.6 + 1.35 * nc); ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor(SURF)

    y_top = fig_h - 1.05
    rh = 0.62
    x0 = 3.5

    fig.text(0.012, 0.975, "Latent procedural skills: accuracy by condition",
             fontsize=13.5, color=INK, fontweight="bold", va="top")
    fig.text(0.012, 0.938,
             "cell = accuracy % (n).  tint = change vs that row's own baseline.  "
             "* = p<0.05 (McNemar, paired, uncorrected).",
             fontsize=8.2, color=INK2, va="top")

    # header
    for j, c in enumerate(cols):
        ax.text(x0 + 1.35 * j + 0.675, y_top + 0.30, PRETTY.get(c, c),
                ha="center", va="center", fontsize=7.6, color=INK2,
                linespacing=1.35)
    ax.plot([0.12, x0 + 1.35 * nc], [y_top - 0.02, y_top - 0.02],
            color=INK3, lw=1.1)

    norm = Normalize(vmin=-7, vmax=7)
    prev_bench = None
    for i, (b, h, m) in enumerate(rows):
        y = y_top - 0.12 - rh * (i + 1)
        if prev_bench is not None and b != prev_bench:
            ax.plot([0.12, x0 + 1.35 * nc], [y + rh - 0.06, y + rh - 0.06],
                    color=RULE, lw=1.6)
        prev_bench = b
        lbl = f"{b}" + (f"  [{h}]" if h != "direct" else "")
        ax.text(0.14, y + rh / 2 + 0.07, lbl, ha="left", va="center",
                fontsize=8.4, color=INK, fontweight="bold")
        ax.text(0.14, y + rh / 2 - 0.13, f"Qwen {m.replace('qwen','').replace('3.6-','3.6 ').replace('3-','3 ')}",
                ha="left", va="center", fontsize=7.6, color=INK3)

        base = cells.get((b, h, m, "baseline"), {})
        for j, c in enumerate(cols):
            cx = x0 + 1.35 * j
            it = cells.get((b, h, m, c), {})
            if not it:
                ax.text(cx + 0.675, y + rh / 2, "–", ha="center", va="center",
                        fontsize=9, color="#C8D0D2")
                continue
            acc = sum(it.values()) / len(it) * 100
            face, sig, bold = SURF, "", False
            if c != "baseline" and base:
                d = acc - sum(base.values()) / len(base) * 100
                face = CMAP(norm(d))
                p = mcnemar(base, it)
                if p < 0.05:
                    sig, bold = "*", True
            ax.add_patch(plt.Rectangle((cx + 0.06, y + 0.05), 1.23, rh - 0.1,
                                       facecolor=face, edgecolor=RULE, lw=0.6,
                                       zorder=0))
            ax.text(cx + 0.675, y + rh / 2 + 0.08, f"{acc:.1f}{sig}",
                    ha="center", va="center", fontsize=9.6, color=INK,
                    fontweight="bold" if bold else "normal")
            ax.text(cx + 0.675, y + rh / 2 - 0.14, f"n={len(it)}",
                    ha="center", va="center", fontsize=6.8, color=INK3)

    # legend for the diverging tint
    lx, ly = 0.14, 0.34
    for k in range(40):
        ax.add_patch(plt.Rectangle((lx + k * 0.035, ly), 0.036, 0.14,
                                   facecolor=CMAP(k / 39), edgecolor="none"))
    ax.text(lx, ly - 0.10, "−7 pts", fontsize=6.8, color=INK3, ha="left", va="top")
    ax.text(lx + 40 * 0.035, ly - 0.10, "+7 pts", fontsize=6.8, color=INK3,
            ha="right", va="top")
    ax.text(lx + 20 * 0.035, ly + 0.22, "change vs baseline", fontsize=7,
            color=INK2, ha="center", va="bottom")

    out = os.path.join(ROOT, "results_table.png")
    fig.savefig(out, bbox_inches="tight", facecolor=SURF, dpi=210)
    print(f"wrote {out}  ({nr} rows x {nc} cols)")


if __name__ == "__main__":
    main()
