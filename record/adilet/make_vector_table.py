"""Table: livemath_ts as text vs as a steering vector, on MMLU-Pro math and SuperGPQA hard math.

    python make_vector_table.py vector_arm/vector_cells.json vector_arm/vector_table.png

Cells come from compute_vector_cells.py (run on the box). Same style as make_math_skills_table.py.
"""
import json
import sys

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle

rows = json.load(open(sys.argv[1]))
out = sys.argv[2]
COLS = [("baseline", "baseline\n(no skill)"), ("text", "livemath_ts\nas text"),
        ("placebo", "its placebo\nas text"), ("B1", "B1 vector\nskill − placebo"),
        ("B2", "B2 vector\nskill − nothing"), ("CONTROL", "CONTROL vector\nplacebo − nothing")]
cmap = LinearSegmentedColormap.from_list("d", ["#c0612b", "#e3c9b6", "#efebe6", "#c9d8e3", "#2f7fb8"])
norm = Normalize(-10, 10)
INK, MUTED, RULE = "#1a1a1a", "#7a8088", "#8a949e"
ntest = sum(len(r["cells"]) - 1 for r in rows)

notes = [
    "Reading it:",
    f"• No vector beats no skill. {sum(1 for r in rows for c, v in r['cells'].items() if v['p'] is not None and v['p'] < .05)} of {ntest} cells are significant, all losses; "
    "B1 on SuperGPQA 8B (−10.3*) is also below CONTROL (p=0.04).",
    "• The text skill itself changes nothing (−0.6 to +1.9, none significant), so there is no gain for a vector to carry.",
    "• Fidelity: the 8B/14B vectors move the model about a third of the way to the text skill's next-token distribution. On the 27B",
    "   at L62 (Adil's LiveMath setting) B1/B2 reach only ~0.06, below CONTROL's 0.20: that layer does not carry this skill, so 27B cells are weak evidence.",
    "• The text placebo hurts the 8B by halving reply length, as in the main table. The steered arms do not shorten replies.",
]

H = 250 + 68 * len(rows) + 60 + 21 * len(notes) + 110
fig = plt.figure(figsize=(16.1, H / 100), dpi=110)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1610); ax.set_ylim(H, 0); ax.axis("off")
ax.text(14, 30, "livemath_ts as text vs as a steering vector", fontsize=19, fontweight="bold", color=INK, va="center")
ax.text(14, 62, f"cell = accuracy % (n).  tint = change vs that row's own baseline.  * = p<0.05 (exact McNemar, paired, "
        f"uncorrected; {ntest} tests, ~{round(.05 * ntest, 1)} expected by chance).", fontsize=10.5, color="#4a525a", va="center")
ax.text(14, 84, "Greedy, thinking off, test split; every cell on the same HF engine. Vectors: diff-in-means at the last prompt "
        "token over the 40 train items; h += 0.3·‖h‖·v̂ at one layer (fixed in advance).", fontsize=10.5, color="#4a525a", va="center")

x0, cw, gap = 450, 140, 10
xs = [x0 + i * (cw + gap) for i in range(len(COLS))]
fx = xs[-1] + cw + 24
for x, (_, lab) in zip(xs, COLS):
    ax.text(x + cw / 2, 165, lab, ha="center", va="center", fontsize=9.6, color="#4a525a")
ax.text(fx + 105, 165, "fidelity at that layer\nB1 · B2 · CONTROL", ha="center", va="center", fontsize=9.6, color="#4a525a")
ax.plot([185, fx + 215], [212, 212], color=RULE, lw=1.6)

y, prev = 228, None
for r in rows:
    if prev is not None and r["bench"] != prev:
        ax.plot([185, fx + 215], [y - 6, y - 6], color="#c5ccd1", lw=2.4); y += 14
    prev = r["bench"]
    ax.text(188, y + 17, r["bench"], fontsize=11.5, fontweight="bold", color=INK, va="center")
    ax.text(188, y + 39, f"{r['model']}  ·  layer {r['layer']}", fontsize=10.5, color=MUTED, va="center")
    for (c, _), x in zip(COLS, xs):
        cell = r["cells"].get(c)
        if cell is None:
            ax.text(x + cw / 2, y + 27, "–", ha="center", va="center", color="#c3c8cd")
            continue
        sig = cell["p"] is not None and cell["p"] < 0.05
        face = "white" if c == "baseline" else cmap(norm(cell["d"]))
        ax.add_patch(Rectangle((x, y), cw, 54, facecolor=face,
                               edgecolor="#d0d5da" if c == "baseline" else "#d8dcdf", lw=1))
        dark = c != "baseline" and abs(cell["d"]) >= 7
        ax.text(x + cw / 2, y + 19, f"{cell['acc']:.1f}" + ("*" if sig else ""), ha="center", va="center",
                fontsize=13, color="white" if dark else INK, fontweight="bold" if sig else "normal")
        sub = f"n={cell['n']}" if c == "baseline" else f"n={cell['n']}  {cell['d']:+.1f}"
        ax.text(x + cw / 2, y + 40, sub, ha="center", va="center", fontsize=9, color="#f4f4f4" if dark else MUTED)
    f = r.get("fidelity", {})
    if f:
        ax.text(fx + 105, y + 27, "  ·  ".join(f"{f.get(a, float('nan')) + 0.0:.2f}".replace("-0.00", "0.00") for a in ("B1", "B2", "CONTROL")),
                ha="center", va="center", fontsize=11, color=INK)
    y += 64

for i, t in enumerate(notes):
    ax.text(188, y + 26 + 21 * i, t, fontsize=9.8, color=INK if i == 0 else "#4a525a",
            fontweight="bold" if i == 0 else "normal", va="center")
ly = y + 26 + 21 * len(notes) + 30
ax.text(268, ly, "change vs baseline", ha="center", fontsize=9.5, color="#4a525a", va="center")
for i in range(60):
    ax.add_patch(Rectangle((188 + i * 2.7, ly + 14), 2.8, 16, color=cmap(i / 59), lw=0))
ax.text(188, ly + 46, "−10 pts", fontsize=9.5, color=MUTED, va="center")
ax.text(350, ly + 46, "+10 pts", fontsize=9.5, color=MUTED, va="center", ha="right")
fig.savefig(out, dpi=110, facecolor="white")
print("wrote", out)
