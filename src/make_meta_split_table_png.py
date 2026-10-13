"""Render the strength_audit vs strength_audit_nometa LiveMath runs as a PNG
table, split into META / OTHER questions. Same visual language as
src/make_table_png.py (imports its palette and McNemar test).

META = questions where one option reads "One of the remaining options is
correct, but a stronger result can be proven" -- the correct answer in all
263 cases it appears. OTHER = the remaining 345, all concrete maths options.
"""
from __future__ import annotations

import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.matrix import mcnemar  # noqa: E402
from src.make_table_png import (CMAP, INK, INK2, INK3, RULE, SURF)  # noqa: E402

META_RX = re.compile(r"stronger result can be proven|one of the (remaining|other) options", re.I)
MODELS = ["qwen3-8b", "qwen3-14b", "qwen3.6-27b"]
COLS = ["baseline", "text_strength_audit", "text_strength_audit_nometa"]
PRETTY = {"baseline": "baseline\n(no skill)",
          "text_strength_audit": "strength_audit\n(Adilet's skill)",
          "text_strength_audit_nometa": "strength_audit\nminus meta rule"}
SUBSETS = [("All", "all 608 questions"), ("META", "meta-option present"),
           ("OTHER", "all options are maths")]
SCALE = 20  # deltas reach +46 on META; +/-7 (original table) would saturate


def meta_ids():
    ids = set()
    for line in open(os.path.join(ROOT, "data", "livemath.jsonl")):
        q = json.loads(line)
        if META_RX.search(json.dumps(q)):
            ids.add(q["id"])
    return ids


def load(model, cond):
    out = {}
    for s in (0, 1):
        p = os.path.join(ROOT, "results", f"livemath_{model}_{cond}_s{s}of2.json")
        for r in json.load(open(p))["records"]:
            out[r["id"]] = float(r["em"]) > 0
    return out


def render(rows, cols, pretty, title, notes, scale, out):
    """rows: [(model, subset name, subset description, {col: {id: bool}})].
    The first entry of cols is the baseline every other column is compared to."""
    nr, nc = len(rows), len(cols)
    cw = 1.6
    x0 = 3.5
    fig_w = x0 + 0.1 + cw * nc
    fig_h = 2.5 + 0.62 * nr
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=210)
    ax.set_xlim(0, fig_w); ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor(SURF)

    y_top = fig_h - 1.05
    rh = 0.62

    fig.text(0.012, 0.975, title, fontsize=13.5, color=INK, fontweight="bold", va="top")
    for k, line in enumerate(["cell = accuracy % (n, change vs baseline).  tint = change vs that "
                              "row's own baseline.  * = p<0.05 (McNemar, paired, uncorrected)."]
                             + list(notes)):
        fig.text(0.012, 0.950 - 0.018 * k, line, fontsize=8.2, color=INK2, va="top")

    for j, c in enumerate(cols):
        ax.text(x0 + cw * j + cw / 2, y_top + 0.30, pretty[c],
                ha="center", va="center", fontsize=7.6, color=INK2, linespacing=1.35)
    ax.plot([0.12, x0 + cw * nc], [y_top - 0.02, y_top - 0.02], color=INK3, lw=1.1)

    norm = Normalize(vmin=-scale, vmax=scale)
    prev = None
    for i, (m, name, desc, cells) in enumerate(rows):
        y = y_top - 0.12 - rh * (i + 1)
        if prev is not None and m != prev:
            ax.plot([0.12, x0 + cw * nc], [y + rh - 0.06, y + rh - 0.06], color=RULE, lw=1.6)
        prev = m
        ax.text(0.14, y + rh / 2 + 0.07,
                f"Qwen {m.replace('qwen','').replace('3.6-','3.6 ').replace('3-','3 ')}  ·  {name}",
                ha="left", va="center", fontsize=8.4, color=INK, fontweight="bold")
        ax.text(0.14, y + rh / 2 - 0.13, desc, ha="left", va="center", fontsize=7.6, color=INK3)

        base = cells[cols[0]]
        base_acc = sum(base.values()) / len(base) * 100
        for j, c in enumerate(cols):
            cx = x0 + cw * j
            it = cells[c]
            acc = sum(it.values()) / len(it) * 100
            face, sig, bold, sub = SURF, "", False, f"n={len(it)}"
            if c != cols[0]:
                d = acc - base_acc
                face = CMAP(norm(d))
                sub += f"   {d:+.1f}"
                if mcnemar(base, it) < 0.05:
                    sig, bold = "*", True
            ax.add_patch(plt.Rectangle((cx + 0.06, y + 0.05), cw - 0.12, rh - 0.1,
                                       facecolor=face, edgecolor=RULE, lw=0.6, zorder=0))
            ax.text(cx + cw / 2, y + rh / 2 + 0.08, f"{acc:.1f}{sig}", ha="center",
                    va="center", fontsize=9.6, color=INK,
                    fontweight="bold" if bold else "normal")
            ax.text(cx + cw / 2, y + rh / 2 - 0.14, sub, ha="center", va="center",
                    fontsize=6.8, color=INK if abs(acc - base_acc) > scale * 0.6 and c != cols[0] else INK3)

    lx, ly = 0.14, 0.34
    for k in range(40):
        ax.add_patch(plt.Rectangle((lx + k * 0.035, ly), 0.036, 0.14,
                                   facecolor=CMAP(k / 39), edgecolor="none"))
    ax.text(lx, ly - 0.10, f"−{scale} pts", fontsize=6.8, color=INK3, ha="left", va="top")
    ax.text(lx + 40 * 0.035, ly - 0.10, f"+{scale} pts", fontsize=6.8, color=INK3,
            ha="right", va="top")
    ax.text(lx + 20 * 0.035, ly + 0.22, "change vs baseline", fontsize=7,
            color=INK2, ha="center", va="bottom")

    fig.savefig(out, bbox_inches="tight", facecolor=SURF, dpi=210)
    print(f"wrote {out}  ({nr} rows x {nc} cols)")


def main():
    meta = meta_ids()
    rows = []
    for m in MODELS:
        full = {c: load(m, c) for c in COLS}
        for name, desc in SUBSETS:
            keep = (lambda i: True) if name == "All" else \
                   (lambda i: i in meta) if name == "META" else (lambda i: i not in meta)
            rows.append((m, name, desc,
                         {c: {i: v for i, v in full[c].items() if keep(i)} for c in COLS}))

    render(rows, COLS, PRETTY, "LiveMath: strength_audit skill, with and without the meta rule",
           [f"META = the {len(meta)} questions with the option \"one of the remaining options is "
            "correct, but a stronger result can be proven\" (always the correct answer)."],
           SCALE, os.path.join(ROOT, "results_table_meta_split.png"))


if __name__ == "__main__":
    main()
