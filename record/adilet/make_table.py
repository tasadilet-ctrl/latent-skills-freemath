"""Redraw the 'Latent procedural skills: accuracy by condition' table."""
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle

COLS = ["baseline\n(no skill)", "text skill\n(compare_claims_v3)",
        "text skill v2\n(strength_audit)", "embed\nvs dummy",
        "embed\nvs nothing", "CONTROL\ndummy only\n(no skill)"]

# (benchmark, model, [cells]) ; cell = (acc, n, significant) or None
ROWS = [
    ("LiveMath", "Qwen 3 8b", [(26.2, 608, 0), (27.0, 608, 0), (29.4, 608, 0),
                               (25.8, 608, 0), (27.1, 608, 0), (25.7, 608, 0)]),
    ("LiveMath", "Qwen 3 14b", [(25.3, 608, 0), (27.6, 608, 0), (32.7, 608, 1),
                                (25.2, 608, 0), (26.2, 608, 0), (28.0, 608, 0)]),
    ("LiveMath", "Qwen 3.6 27b", [(33.1, 608, 0), (34.7, 608, 0), None,
                                  (35.2, 608, 0), (39.3, 608, 1), (36.7, 608, 0)]),
    ("SpreadsheetBench  [agent]", "Qwen 3 14b", [(20.0, 200, 0), (24.0, 200, 0), None, None, None, None]),
    ("SpreadsheetBench  [agent]", "Qwen 3.6 27b", [(83.0, 200, 0), None, None, None, None, None]),
    ("SpreadsheetBench  [single-turn]", "Qwen 3 8b", [(15.1, 398, 0), (14.1, 99, 0), None, None, None, None]),
    ("OfficeQA", "Qwen 3 14b", [(0.0, 239, 0), None, None, None, None, None]),
    ("OfficeQA", "Qwen 3.6 27b", [(74.2, 89, 0), None, None, None, None, None]),
]
GROUP_BREAKS = {3, 6}          # rule drawn above these row indices
NEW = {(0, 1), (0, 2), (0, 5), (1, 2), (1, 5)}  # cells measured in this round (Blackwell)

cmap = LinearSegmentedColormap.from_list(
    "d", ["#c0612b", "#e3c9b6", "#efebe6", "#c9d8e3", "#2f7fb8"])
norm = Normalize(-7, 7)
INK, MUTED, RULE = "#1a1a1a", "#7a8088", "#8a949e"

fig = plt.figure(figsize=(14.2, 10.6), dpi=110)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1420); ax.set_ylim(1060, 0); ax.axis("off")

ax.text(14, 30, "Latent procedural skills: accuracy by condition", fontsize=19,
        fontweight="bold", color=INK, va="center")
ax.text(14, 64, "cell = accuracy % (n).  tint = change vs that row's own baseline.  "
        "* = p<0.05 (McNemar, paired, uncorrected).  bold outline = new run (Blackwell, 2026-10-04/05).",
        fontsize=10.5, color="#4a525a", va="center")

x0, cw, gap = 548, 130, 12
xs = [x0 + i * (cw + gap) for i in range(len(COLS))]
hy = 205
for x, c in zip(xs, COLS):
    ax.text(x + cw / 2, hy, c, ha="center", va="center", fontsize=10, color="#4a525a")
ax.plot([185, xs[-1] + cw + 8], [245, 245], color=RULE, lw=1.6)

y, rh = 260, 64
for r, (bench, model, cells) in enumerate(ROWS):
    if r in GROUP_BREAKS:
        ax.plot([185, xs[-1] + cw + 8], [y - 6, y - 6], color="#d5d9dd", lw=2.2)
        y += 2
    ax.text(188, y + 17, bench, fontsize=11.5, fontweight="bold", color=INK, va="center")
    ax.text(188, y + 39, model, fontsize=10.5, color=MUTED, va="center")
    base = cells[0][0]
    for c, cell in enumerate(cells):
        x = xs[c]
        if cell is None:
            ax.text(x + cw / 2, y + 27, "–", ha="center", va="center", color="#c3c8cd")
            continue
        acc, n, sig = cell
        if c == 0:
            face, edge = "white", "#d0d5da"
        else:
            face, edge = cmap(norm(acc - base)), "#d8dcdf"
        new = (r, c) in NEW
        ax.add_patch(Rectangle((x, y), cw, 54, facecolor=face,
                               edgecolor=INK if new else edge, lw=1.8 if new else 1))
        ax.text(x + cw / 2, y + 19, f"{acc:.1f}" + ("*" if sig else ""), ha="center",
                va="center", fontsize=13.5, color=INK, fontweight="bold" if sig else "normal")
        ax.text(x + cw / 2, y + 40, f"n={n}", ha="center", va="center", fontsize=9.5, color=MUTED)
    y += rh + 1

# footnote on the new skill
fy = y + 22
ax.text(188, fy, "strength_audit (LiveMath) by question type:", fontsize=10.5,
        fontweight="bold", color=INK, va="center")
notes = [
    "263 questions offering \"One of the remaining options is correct, but a stronger result can be proven\" "
    "(always the correct answer when present):",
    "      Qwen 3 8b:   baseline 2.7  →  16.0   (39 gained / 4 lost, p = 3e-8)        Qwen 3 14b:   baseline 1.5  →  27.4   (69 / 1, p = 1e-19)",
    "other 345 questions:",
    "      Qwen 3 8b:   baseline 44.1  →  39.7   (51 / 66, p = 0.20, n.s.)            Qwen 3 14b:   baseline 43.5  →  36.8   (39 / 62, p = 0.03)",
    "overall: 8b +3.3 pts (p = 0.13);  14b +7.4 pts (p = 7e-4).  Held-out questions 100–607 (not used to pick the skill): 8b 26.4 → 29.7;  14b 26.2 → 32.9.",
    "placebo: 8b 1.1 on the 263, 44.3 on the other 345;  14b 4.6 / 45.8.   strength_audit vs placebo: 8b p = 0.08;  14b p = 0.035.",
]
for i, t in enumerate(notes):
    ax.text(188, fy + 24 + 21 * i, t, fontsize=9.6, color="#4a525a", va="center")

# legend
ly = fy + 175
ax.text(262, ly, "change vs baseline", ha="center", fontsize=9.5, color="#4a525a", va="center")
for i in range(60):
    ax.add_patch(Rectangle((188 + i * 2.5, ly + 16), 2.6, 16, color=cmap(i / 59), lw=0))
ax.text(188, ly + 48, "−7 pts", fontsize=9.5, color=MUTED, va="center")
ax.text(338, ly + 48, "+7 pts", fontsize=9.5, color=MUTED, va="center", ha="right")

fig.savefig("/Users/adilettasbolat/Desktop/Latent_skills/latent_skills_table_updated.png",
            dpi=110, facecolor="white")
