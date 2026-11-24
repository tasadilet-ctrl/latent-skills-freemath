"""Reasoning Gym decimal_arithmetic as 10-option multiple choice (2026-11-24), T2-style split:
train 100 (seed 11) / val 150 (seed 12) / test 250 (seed 100000; its first 200 = the batch-sweep test questions).

Question = RG's text with "Only reply with the final value." removed (that line kept the no-skill baseline from
working; see the fair-baseline rows of table/rg_batch_sweep.md). Options = the RG gold answer + 9 distractors,
all (gold included) printed as 12 significant digits without trailing zeros:
  * up to 4 "procedural" errors, each the expression evaluated with one typical mistake: strict left-to-right
    (no precedence), all parentheses dropped, one operator flipped (+<->-, *<->/), decimal point shifted x10 / /10;
  * the rest "near misses": gold + d * 10^p, p = place of gold's 3rd significant digit, d distinct non-zero
    integers drawn so that gold's rank inside the near-miss cluster is uniform (no "middle value" shortcut).
Distractor order shuffled per question; the gold letter is balanced: each of A-J is gold for exactly 10% of
each split (a shuffled list per split), so no letter bias can win validation. Shortcut audit printed at the end (centroid, median, longest,
shortest, closest-to-other-options), and centroid_right is stored on every item as for SuperGPQA.
    ~/rg_env/bin/python make_rg_mcq.py <split dir> <jsonl out>
        -> <split dir>/{train,val,test}/items.json (mcqkit format), <jsonl out> (all 500, evaluate_mcq_t1.py format)
"""
import ast
import json
import math
import operator
import os
import random
import re
import statistics
import sys

import reasoning_gym as rg

L = "ABCDEFGHIJ"
DROP = " Only reply with the final value."
SPLITS = (("train", 11, 100), ("val", 12, 150), ("test", 100000, 250))
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
FLIP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
SYM = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}


def fmt(x):  # RG: round to 12 significant digits, no trailing zeros
    if x == 0 or not math.isfinite(x):
        return None
    s = f"{x:.12g}"
    if "e" in s:
        s = f"{float(s):.15f}".rstrip("0").rstrip(".")
    return s


def ev(n):
    if isinstance(n, ast.BinOp):
        return OPS[type(n.op)](ev(n.left), ev(n.right))
    if isinstance(n, ast.UnaryOp):
        return -ev(n.operand)
    return float(n.value)


def tokens(expr):
    return re.findall(r"\d+\.\d+|\d+|[-+*/()]", expr)


def left_to_right(expr):  # ignore precedence and parentheses
    t = [x for x in tokens(expr) if x not in "()"]
    v = float(t[0])
    for op, num in zip(t[1::2], t[2::2]):
        v = {"+": v + float(num), "-": v - float(num), "*": v * float(num), "/": v / float(num)}[op]
    return v


def procedural(expr):
    tree = ast.parse(expr, mode="eval").body
    out = []
    try:
        out.append(left_to_right(expr))
    except (ZeroDivisionError, ValueError, KeyError, IndexError):  # unary minus etc.: skip this error type
        pass
    try:
        out.append(ev(ast.parse(expr.replace("(", "").replace(")", ""), mode="eval").body))
    except (ZeroDivisionError, SyntaxError):
        pass
    bins = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp)]
    for n in bins:
        old = n.op
        n.op = FLIP[type(old)]()
        try:
            out.append(ev(tree))
        except ZeroDivisionError:
            pass
        n.op = old
    return out


def build(q, gold, rnd, letter):
    expr = q.split("\n")[-1].replace("= ?", "").strip()
    g = float(gold)
    gold = fmt(g)  # RG sometimes keeps a trailing zero ("129.746140"); the distractors never would
    assert abs(ev(ast.parse(expr, mode="eval").body) - g) <= 1e-9 * max(1, abs(g)), (expr, gold)
    seen = {gold}
    opts = []

    def add(x):
        s = fmt(x)
        if s and s not in seen and abs(float(s) - g) > 1e-9 * max(1, abs(g)):
            seen.add(s)
            opts.append(s)
            return True
        return False

    proc = procedural(expr) + [g * 10, g / 10]
    rnd.shuffle(proc)
    for x in proc:
        if len(opts) == 4:
            break
        add(x)
    p = math.floor(math.log10(abs(g))) - 2  # 3rd significant digit
    need = 9 - len(opts)
    k = rnd.randint(0, need)  # gold's rank in the near-miss cluster: k below, need-k above
    ds = [-(i + 1) for i in range(k)] + [i + 1 for i in range(need - k)]
    for d in ds:
        e = 0
        while not add(g + d * 10 ** p * (1 + e)):
            e += 1
    opts = opts[:9]
    rnd.shuffle(opts)
    opts.insert(L.index(letter), gold)
    return q.replace(DROP, ""), opts, letter


def audit(rows):
    def pick(r, f):
        v = [float(o) for o in r["options"]]
        return L[f(v, r)] == r["answer"]
    rules = {
        "centroid": lambda v, r: min(range(10), key=lambda i: abs(v[i] - statistics.mean(v))),
        "median": lambda v, r: sorted(range(10), key=lambda i: v[i])[4],
        "longest": lambda v, r: max(range(10), key=lambda i: len(r["options"][i])),
        "shortest": lambda v, r: min(range(10), key=lambda i: len(r["options"][i])),
        "most-neighbours": lambda v, r: min(range(10), key=lambda i: sum(abs(math.log10(abs(v[i]) + 1e-12) - math.log10(abs(x) + 1e-12)) for x in v)),
        "sign-majority": lambda v, r: max(range(10), key=lambda i: sum((x > 0) == (v[i] > 0) for x in v) + 1e-6 * i),
    }
    return {k: round(100 * sum(pick(r, f) for r in rows) / len(rows), 1) for k, f in rules.items()}


def main():
    sdir, jout = sys.argv[1], sys.argv[2]
    allrows = []
    for name, seed, n in SPLITS:
        d = rg.create_dataset("decimal_arithmetic", size=n, seed=seed)
        rows, items = [], []
        letters = [L[i % 10] for i in range(n)]  # every letter exactly n/10 times per split, in random order
        random.Random(f"rgmcq-letters-{seed}").shuffle(letters)
        for i in range(n):
            rnd = random.Random(f"rgmcq-{seed}-{i}")
            q, opts, ans = build(d[i]["question"], str(d[i]["answer"]), rnd, letters[i])
            r = {"id": f"rgmcq-da-s{seed}-{i}", "question": q, "options": opts, "answer": ans,
                 "source": "decimal_arithmetic", "split": name}
            rows.append(r)
        cen = audit_flags(rows)
        for r, c in zip(rows, cen):
            r["centroid_right"] = c
            ch = [{"label": L[j], "text": t} for j, t in enumerate(r["options"])]
            items.append({"id": r["id"], "question": r["question"], "choices": ch,
                          "correct_choice": ch[L.index(r["answer"])], "theorem_type": ["decimal_arithmetic"],
                          "centroid_right": c, "theorem": "", "sketch": "", "month": "", "no": r["id"],
                          "paper_link": ""})
        os.makedirs(os.path.join(sdir, name), exist_ok=True)
        json.dump(items, open(os.path.join(sdir, name, "items.json"), "w"), ensure_ascii=False)
        print(name, n, "audit %:", audit(rows), "centroid_right", sum(cen))
        allrows += rows
    with open(jout, "w") as f:
        for r in allrows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("all", len(allrows), "audit %:", audit(allrows), "gold letter counts",
          {c: sum(r["answer"] == c for r in allrows) for c in L}, "->", jout)


def audit_flags(rows):
    out = []
    for r in rows:
        v = [float(o) for o in r["options"]]
        m = statistics.mean(v)
        out.append(L[min(range(10), key=lambda i: abs(v[i] - m))] == r["answer"])
    return out


if __name__ == "__main__":
    main()
