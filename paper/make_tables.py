"""Writes paper/tables/*.tex from the saved cells (no hand-typed numbers).

    python paper/make_tables.py

Inputs: record/adilet/math_skills_cells.json, record/adilet/vector_arm/vector_cells.json.
Holm correction is applied within each (benchmark, model) row, as Section 3.6 specifies,
and across the whole table; both counts are written to tables/holm_summary.tex.
"""
import json
import os

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
T = os.path.join(R, "paper", "tables")


def holm(ps):
    """Holm step-down: returns the set of indices rejected at 0.05."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    rej = set()
    for k, i in enumerate(order):
        if ps[i] <= 0.05 / (len(ps) - k):
            rej.add(i)
        else:
            break
    return rej


def fmt(cell, base=False, holm_ok=False, letters=False):
    if cell is None:
        return "--"
    if base:
        return f"{cell['acc']:.1f}"
    s = f"{cell['d']:+.1f}".replace("-", "$-$")
    if cell["p"] is not None and cell["p"] < 0.05:
        s += "$^{*}$"
    if letters:
        s += "$^{\\dagger}$"
    return f"\\textbf{{{s}}}" if holm_ok else s


def table(rows, cols, name, kinds=True):
    allp = [(ri, c) for ri, r in enumerate(rows) for c, _ in cols[1:] if c in r["cells"]]
    glob = holm([rows[ri]["cells"][c]["p"] for ri, c in allp])
    glob_set = {allp[i] for i in glob}
    lines, prev, nsig, nrow = [], None, 0, 0
    for ri, r in enumerate(rows):
        keys = [c for c, _ in cols[1:] if c in r["cells"]]
        rowrej = {keys[i] for i in holm([r["cells"][c]["p"] for c in keys])}
        nrow += len(rowrej)
        if kinds and prev is not None and r.get("kind") != prev:
            lines.append("\\midrule")
        prev = r.get("kind")
        mdl = r["model"].replace("Qwen 3 ", "Qwen3-").replace("Qwen 3.6 ", "Qwen3.6-").replace("b", "B")
        cells = [fmt(r["cells"].get("baseline"), base=True)]
        for c, _ in cols[1:]:
            cell = r["cells"].get(c)
            if cell and cell["p"] is not None and cell["p"] < 0.05:
                nsig += 1
            cells.append(fmt(cell, holm_ok=c in rowrej,
                             letters=bool(cell and cell.get("letters", 0) >= 0.2 * cell["n"])))
        n = r["cells"]["baseline"]["n"]
        lines.append(f"{r['bench']} & {mdl} & {n} & " + " & ".join(cells) + " \\\\")
    open(os.path.join(T, name + ".tex"), "w").write("\n".join(lines) + "\n")
    return len(allp), nsig, nrow, len(glob_set)


cells = json.load(open(os.path.join(R, "record/adilet/math_skills_cells.json")))
COLS = [("baseline", ""), ("placebo", ""), ("strength_audit", ""), ("strength_audit_nometa", ""),
        ("placebo_ts", ""), ("livemath_ts", ""), ("livemath_ts_meta", ""), ("skill", "")]
a = table(cells, COLS, "clean_text")
vec = json.load(open(os.path.join(R, "record/adilet/vector_arm/vector_cells.json")))
VCOLS = [("baseline", ""), ("text", ""), ("placebo", ""), ("B1", ""), ("B2", ""), ("CONTROL", "")]
b = table(vec, VCOLS, "clean_vector", kinds=False)
# fidelity rows for the vector table
fl = []
for r in vec:
    f = r["fidelity"]
    mdl = r["model"].replace("Qwen 3 ", "Qwen3-").replace("Qwen 3.6 ", "Qwen3.6-").replace("b", "B")
    fl.append(f"{r['bench']} & {mdl} & {r['layer']} & " +
              " & ".join(f"{max(f[k], 0) if abs(f[k]) < 5e-3 else f[k]:.2f}".replace("-", "$-$") for k in ("B1", "B2", "CONTROL")) + " \\\\")
open(os.path.join(T, "clean_fidelity.tex"), "w").write("\n".join(fl) + "\n")
with open(os.path.join(T, "holm_summary.tex"), "w") as f:
    for tag, (n, s, hr, hg) in (("Text", a), ("Vec", b)):
        f.write(f"\\newcommand{{\\n{tag}Tests}}{{{n}}}\\newcommand{{\\n{tag}Sig}}{{{s}}}"
                f"\\newcommand{{\\n{tag}HolmRow}}{{{hr}}}\\newcommand{{\\n{tag}HolmAll}}{{{hg}}}\n")
print("text", a, "vector", b)
