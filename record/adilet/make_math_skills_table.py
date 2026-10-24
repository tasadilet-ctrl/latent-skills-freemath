"""Table: text skills on math benchmarks without answer-format shortcuts.

    python make_math_skills_table.py cells.json out.png

cells.json is computed on the box from the saved per-question results (see
README.md). Every row is the PROTOCOL.md stage: SkillOpt's drafts chosen on dev
over Qwen3-8B/14B/3.6-27B, then the test split once, kit prompt + forcing.
"""
import json
import sys

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle

rows = json.load(open(sys.argv[1]))
out = sys.argv[2]
COLS = [("baseline", "baseline\n(no skill)"), ("placebo", "placebo\n(length-matched)"),
        ("strength_audit", "strength_audit"), ("strength_audit_nometa", "strength_audit\nminus meta rule"),
        ("placebo_ts", "placebo for\nlivemath_ts"), ("livemath_ts", "livemath_ts"),
        ("skill", "SkillOpt draft\nchosen by\nPROTOCOL.md")]
cmap = LinearSegmentedColormap.from_list("d", ["#c0612b", "#e3c9b6", "#efebe6", "#c9d8e3", "#2f7fb8"])
norm = Normalize(-10, 10)
INK, MUTED, RULE = "#1a1a1a", "#7a8088", "#8a949e"

H = 260 + 68 * len(rows) + 330
fig = plt.figure(figsize=(15.6, H / 100), dpi=110)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1560); ax.set_ylim(H, 0); ax.axis("off")
ax.text(14, 30, "Text skills on math benchmarks without answer-format shortcuts", fontsize=19,
        fontweight="bold", color=INK, va="center")
ax.text(14, 62, "cell = accuracy % (n).  tint = change vs that row's own baseline.  * = p<0.05 "
        f"(exact McNemar, paired, uncorrected; {sum(len(r['cells']) - 1 for r in rows)} tests in this table, "
        f"so ~{round(0.05 * sum(len(r['cells']) - 1 for r in rows))} are expected by chance).",
        fontsize=10.5, color="#4a525a", va="center")
ax.text(14, 84, "Greedy, thinking off. Every row: PROTOCOL.md stage (SkillOpt drafts chosen on dev over 8B/14B/27B, then test once; "
        "kit prompt + answer forcing, 2048 tokens, 4096 for 27B).",
        fontsize=10.5, color="#4a525a", va="center")

x0, cw, gap = 470, 140, 10
xs = [x0 + i * (cw + gap) for i in range(len(COLS))]
for x, (_, lab) in zip(xs, COLS):
    ax.text(x + cw / 2, 165, lab, ha="center", va="center", fontsize=9.6, color="#4a525a")
ax.plot([185, xs[-1] + cw + 6], [212, 212], color=RULE, lw=1.6)

y, prev_kind = 228, None
for r in rows:
    if prev_kind is not None and r["kind"] != prev_kind:
        ax.plot([185, xs[-1] + cw + 6], [y - 6, y - 6], color="#c5ccd1", lw=2.4); y += 14
    if prev_kind != r["kind"]:
        ax.text(14, y + 20, "MCQ, no meta-option" if r["kind"] == "mcq" else "free-form answers",
                fontsize=10, color=MUTED, va="center", style="italic")
    prev_kind = r["kind"]
    ax.text(188, y + 17, r["bench"], fontsize=11.5, fontweight="bold", color=INK, va="center")
    ax.text(188, y + 39, r["model"], fontsize=10.5, color=MUTED, va="center")
    for (c, _), x in zip(COLS, xs):
        cell = r["cells"].get(c)
        if cell is None:
            ax.text(x + cw / 2, y + 27, "–", ha="center", va="center", color="#c3c8cd")
            continue
        sig = cell["p"] is not None and cell["p"] < 0.05
        face = "white" if c == "baseline" else cmap(norm(cell["d"]))
        ax.add_patch(Rectangle((x, y), cw, 54, facecolor=face,
                               edgecolor="#d0d5da" if c == "baseline" else "#d8dcdf", lw=1))
        dark = c != "baseline" and abs(cell["d"]) >= 7          # light text on the darkest tints
        ax.text(x + cw / 2, y + 19, f"{cell['acc']:.1f}" + ("*" if sig else ""), ha="center", va="center",
                fontsize=13, color="white" if dark else INK, fontweight="bold" if sig else "normal")
        sub = f"n={cell['n']}" if c == "baseline" else f"n={cell['n']}  {cell['d']:+.1f}"
        ax.text(x + cw / 2, y + 40, sub, ha="center", va="center", fontsize=9, color="#f4f4f4" if dark else MUTED)
    y += 64

notes = [
    "Reading it:",
    "• No skill beats no system prompt. 10 of 96 cells are significant: 9 are losses; the one gain (MMLU-Pro 14B +5.5) reverses on the 27B",
    "   (−2.5*) with the same text and did not show on dev.  ~5 significant cells are expected by chance alone.",
    "• PROTOCOL.md picked SkillOpt's 4-line seed (or seed + empty tags) on all 7 benchmarks: every longer, optimized draft lost on dev.",
    "• Length-matched placebos hurt most often (MMLU-Pro, SuperGPQA and IMO on 8B): they halve reply length, and these problems need room.",
    "• HARDMath2 and ArxivMath sit near the floor for all three models with thinking off, so they cannot show small effects.",
    "• Tint shows size, not reliability: the dark-blue cells on BeyondAIME (n=40) and ArxivMath (n=43) are 4 extra questions, not significant.",
]
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
