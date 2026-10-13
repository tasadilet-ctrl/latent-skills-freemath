"""Diverging bars: every LiveMath gain is on the meta-option subset.

Form: the data's job is POLARITY -- each cell either beat its baseline or did
not -- so bars diverge around a zero line. Colour carries subset identity
(2 categorical slots, validated), not magnitude; the sign is already in the
geometry. Values are direct-labelled because there are only twelve of them.
"""
import json, glob, os, re, math, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# validated categorical slots 1 and 2 (node validate_palette.js, light surface)
META, OTHER = "#2a78d6", "#eb6834"
SURF, INK, INK2, INK3, RULE = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e2e1dc"

pat = re.compile(r"stronger result can be proven|one of the (remaining|other) options", re.I)
metaq = set()
for line in open(f"{KIT}/data/livemath.jsonl"):
    r = json.loads(line)
    opts = r["options"] if isinstance(r["options"], list) else list(r["options"].values())
    if any(pat.search(str(o)) for o in opts):
        metaq.add(r["id"])


def load(p):
    d = {}
    for f in glob.glob(f"{KIT}/results/{p}"):
        for rec in json.load(open(f))["records"]:
            d[rec["id"]] = rec["em"]
    return d


rows = []
for tag, label in (("qwen3-8b", "Qwen3-8B"), ("qwen3-14b", "Qwen3-14B"),
                   ("qwen3.6-27b", "Qwen3.6-27B")):
    base = load(f"livemath_{tag}_baseline_*.json")
    cells = [("strength_audit", load(f"livemath_{tag}_text_strength_audit_s*.json")),
             ("skill minus the\nmeta-option rule", load(f"livemath_{tag}_text_strength_audit_nometa_*.json"))]
    ids = set(base)
    for _, c in cells:
        ids &= set(c)
    A = [i for i in ids if i in metaq]
    B = [i for i in ids if i not in metaq]
    pc = lambda c, S: 100 * sum(c[i] for i in S) / len(S)
    for name, c in cells:
        rows.append((label, name, pc(c, A) - pc(base, A), pc(c, B) - pc(base, B),
                     pc(c, list(ids)) - pc(base, list(ids))))

fig, ax = plt.subplots(figsize=(11.4, 6.6), dpi=200)
fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)

H, GAP = 0.30, 0.04          # bar height, 2px-equivalent surface gap
ypos = []
for i, (model, skill, dm, do, _) in enumerate(rows):
    y = -i * 1.15
    ypos.append(y)
    for val, col, off in ((dm, META, +(H / 2 + GAP)), (do, OTHER, -(H / 2 + GAP))):
        x0 = min(0, val)
        ax.add_patch(FancyBboxPatch((x0, y + off - H / 2), abs(val), H,
                                    boxstyle="round,pad=0,rounding_size=0.9",
                                    mutation_aspect=0.06,
                                    facecolor=col, edgecolor=SURF, linewidth=1.4,
                                    zorder=3))
        ha = "left" if val > 0 else "right"
        ax.text(val + (1.1 if val > 0 else -1.1), y + off, f"{val:+.1f}",
                va="center", ha=ha, fontsize=9.3, color=INK, zorder=4,
                fontweight="bold" if abs(val) > 20 else "normal")

ax.axvline(0, color=INK3, lw=1.3, zorder=2)
for x in (-10, 10, 20, 30, 40, 50):
    ax.axvline(x, color=RULE, lw=0.8, zorder=0)

for y, (model, skill, *_rest) in zip(ypos, rows):
    ax.text(-13.5, y + 0.19, model, ha="right", va="center", fontsize=9.6,
            color=INK, fontweight="bold")
    ax.text(-13.5, y - 0.26, skill, ha="right", va="center", fontsize=8.5,
            color=INK2, linespacing=1.25)

ax.set_xlim(-30, 58); ax.set_ylim(min(ypos) - 0.75, 0.75)
ax.set_yticks([]); ax.set_xticks([-10, 0, 10, 20, 30, 40, 50])
ax.set_xticklabels(["−10", "0", "+10", "+20", "+30", "+40", "+50"],
                   fontsize=9, color=INK2)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(RULE)
ax.tick_params(axis="x", length=0)
ax.set_xlabel("change in accuracy vs that model's own no-skill baseline  (percentage points)",
              fontsize=9.2, color=INK2, labelpad=9)

# legend: 2 series, so a legend is mandatory; bars are also direct-labelled.
# Placed in FIGURE space above the axes -- inside the plot it collided with the
# gridlines and the zero rule.
for fx, col, lab in ((0.013, META,
                      'META  —  the 263 questions whose five options include\n'
                      '              "one of the remaining options is correct, but a\n'
                      '               stronger result can be proven".  It is the correct\n'
                      '               answer every time it appears.'),
                     (0.470, OTHER,
                      "OTHER —  the 345 questions where all five options are\n"
                      "               concrete mathematical statements and have to\n"
                      "               be told apart on the mathematics.")):
    fig.patches.append(plt.Rectangle((fx, 0.838), 0.011, 0.020,
                                     transform=fig.transFigure,
                                     facecolor=col, edgecolor="none"))
    fig.text(fx + 0.018, 0.848, lab, va="center", fontsize=8.2, color=INK2,
             linespacing=1.45)

fig.text(0.012, 0.975, "Every gain is on the questions with the format tell",
         fontsize=14.5, color=INK, fontweight="bold", va="top")
fig.text(0.012, 0.936,
         "LiveMath, n=608 per cell.  The meta-option is the correct answer in 263 of 263 cases it appears, "
         "so recognising it is worth 43.3% on its own.",
         fontsize=8.9, color=INK2, va="top")
fig.text(0.235, 0.022,
         "Not one of the six skill cells improves on baseline over the OTHER questions. The skills do not make these\n"
         "models better at mathematics; they make them better at one answer format, and slightly worse at everything else.",
         fontsize=8.6, color=INK2, va="bottom", linespacing=1.55)

fig.subplots_adjust(left=0.235, right=0.985, top=0.805, bottom=0.185)
out = f"{KIT}/livemath_meta_split_bars.png"
fig.savefig(out, facecolor=SURF, dpi=200)
print("wrote", out)
for m, s, dm, do, dall in rows:
    print(f"  {m:<12} {s.replace(chr(10),' '):<34} meta {dm:+6.1f}  other {do:+6.1f}  all {dall:+6.1f}")
