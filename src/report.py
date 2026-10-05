"""Merge sharded result files and print the model x condition matrix.

Conditions are compared against the no-skill baseline of the SAME model on the
SAME items, so the test is paired: every condition answers the identical 608
questions. McNemar on the discordant pairs is used rather than a two-proportion
z-test, which would throw away that pairing and need a much larger effect to
reach significance.
"""
from __future__ import annotations

import glob
import json
import math
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Questions whose prompts were consumed by the in-domain (`livemath`) extraction
# pool. Accuracy is reported on the disjoint remainder too, so a vector built
# from those prompts cannot be credited with an advantage they explain.
POOL_N = 50


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar(a: dict, b: dict) -> tuple[int, int, float]:
    """Exact two-sided binomial McNemar over items answered by both arms."""
    shared = set(a) & set(b)
    b01 = sum(1 for i in shared if not a[i] and b[i])      # baseline wrong, arm right
    b10 = sum(1 for i in shared if a[i] and not b[i])      # baseline right, arm wrong
    n = b01 + b10
    if n == 0:
        return b01, b10, 1.0
    lo = min(b01, b10)
    tail = sum(math.comb(n, k) for k in range(lo + 1)) / 2 ** n
    return b01, b10, min(1.0, 2 * tail)


def key_of(s: dict) -> str:
    if s["condition"] == "embed":
        v = s["vector"]
        lay = v["layers"]
        span = f"{lay[0]}-{lay[-1]}" if len(lay) > 1 else str(lay[0])
        stem = v["file"].replace(".pt", "").replace("v_", "", 1)
        # "from", not "vs": the placebo is what the vector was EXTRACTED
        # AGAINST -- the baseline of the contrast -- not something the result
        # is compared with.
        arm = "from-placebo" if stem.endswith("_placebo") else "from-nothing"
        # The SKILL the vector came from must be in the key. Without it two
        # cells that share (pool, arm, layer, gamma) but were built from
        # different skills collapse into one row and silently overwrite each
        # other -- which is exactly what a prompt-presence control does.
        body = stem.split("_", 1)[1] if "_" in stem else stem      # drop model tag
        for suf in ("_placebo", "_plain"):
            if body.endswith(suf):
                body = body[: -len(suf)]
        src = body.rsplit("_n", 1)[0]                              # drop _n50
        src = src.rsplit("_", 1)[0] if src.endswith(("_" + v["pool"],)) else src
        pos = "@usr" if "_usr_" in stem or stem.endswith("_usr") else ""
        return f"embed[{src}{pos}/{arm}] L{span} g{v['gamma']}"
    # skill_position must be in the key: a skill delivered in the user turn is
    # a DIFFERENT condition from the same skill as a system message, and
    # without this they merge into one row and overwrite each other.
    pos = "@usr" if s.get("skill_position") == "user" else ""
    if s["condition"] == "text":
        sk = (s.get("skill") or "?").replace(".md", "")
        # ONE alias, and only because the two names hold byte-identical text:
        # compare_claims_v3.md was renamed to compare_claims.md on 2026-10-05.
        # Without this, re-running a cell after the rename produces a second
        # row for the same intervention. Nothing else is aliased here -- this
        # function deliberately keeps distinct skills in distinct rows.
        if sk == "compare_claims_v3":
            sk = "compare_claims"
        return f"text[{sk}{pos}]"
    return "baseline"


def main():
    # (model, domain, condition) -> merged records
    cells: dict[tuple, dict] = defaultdict(
        lambda: {"items": {}, "parsed": 0, "n": 0, "chars": 0.0, "secs": 0.0})
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "*.json"))):
        blob = json.load(open(path))
        if "summary" not in blob or "records" not in blob:
            continue                                  # calib_/fidelity_ files
        s = blob["summary"]
        # Runs from before the model field existed (2026-09-17) predate the
        # 8B download on 2026-09-20, so they are all the 27B.
        tag = s.get("model_tag") or s.get("model", "Qwen/Qwen3.6-27B").split("/")[-1].lower()
        c = cells[(tag, s["domain"], key_of(s))]
        for r in blob["records"]:
            c["items"][r["id"]] = r["em"]
        c["n"] += s["n"]
        c["parsed"] += round(s.get("parse_rate", 1.0) * s["n"])
        c["chars"] += s.get("mean_pred_chars", 0.0) * s["n"]
        c["secs"] += s.get("seconds", 0.0)

    if not cells:
        print("no results yet"); return

    pool_ids = []
    lm = os.path.join(ROOT, "data", "livemath.jsonl")
    if os.path.exists(lm):
        pool_ids = [json.loads(l)["id"] for l in open(lm)][:POOL_N]

    for domain in sorted({d for _, d, _ in cells}):
        for model in sorted({m for m, d, _ in cells if d == domain}):
            keys = sorted({k for m, d, k in cells if (m, d) == (model, domain)},
                          key=lambda k: (k != "baseline", k))
            base = cells.get((model, domain, "baseline"), {}).get("items", {})
            w = max(len(k) for k in keys) + 2
            print(f"\n{'=' * (w + 62)}\n{domain}   {model}\n{'=' * (w + 62)}")
            print(f"{'condition':<{w}}{'acc %':>8}{'95% CI':>16}{'n':>6}"
                  f"{'parse':>7}{'d vs base':>11}{'McNemar p':>11}")
            print("-" * (w + 59))
            for k in keys:
                c = cells[(model, domain, k)]
                it = c["items"]
                n = len(it); hit = sum(it.values())
                lo, hi = wilson(round(hit), n)
                par = c["parsed"] / c["n"] if c["n"] else 0.0
                if k == "baseline" or not base:
                    delta = pval = None
                else:
                    _, _, pval = mcnemar(base, it)
                    delta = hit / n - sum(base.values()) / len(base)
                print(f"{k:<{w}}{hit / n * 100:>8.2f}"
                      f"{f'[{lo * 100:.1f}, {hi * 100:.1f}]':>16}{n:>6}{par:>7.3f}"
                      f"{'' if delta is None else f'{delta * 100:>+10.2f}'}"
                      f"{'' if pval is None else f'{pval:>11.3f}'}")

            # Same table restricted to items no extraction pool ever saw.
            if domain == "livemath" and pool_ids and len(keys) > 1:
                held = set(json.loads(l)["id"] for l in open(lm)) - set(pool_ids)
                print(f"\n  held-out subset (n={len(held)}, excludes the {POOL_N} "
                      f"prompts the in-domain pool used):")
                for k in keys:
                    it = {i: v for i, v in cells[(model, domain, k)]["items"].items()
                          if i in held}
                    if it:
                        print(f"    {k:<{w}}{sum(it.values()) / len(it) * 100:>8.2f}")
    print("\nacc = exact-match on the 5-way choice; chance = 20.0%")
    print("McNemar p is two-sided exact, paired against this model's baseline.\n")


if __name__ == "__main__":
    main()
