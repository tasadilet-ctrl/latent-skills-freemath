"""Vector (embedding) arm of the livemath_ts skill on MMLU-Pro math and SuperGPQA hard math.

The kit's steering (src/hooks.py, src/qwen.py) applied to the MCQ benchmarks of
record/adilet/. One skill, livemath_ts, and its length-matched placebo; three vectors
per model and benchmark, diff-in-means at the final prompt token:

    B1       mean h | [livemath_ts]          - mean h | [placebo_livemath_ts]   (controlled)
    B2       mean h | [livemath_ts]          - mean h | [no system message]     (uncontrolled)
    CONTROL  mean h | [placebo_livemath_ts]  - mean h | [no system message]     (no skill in it)

Extraction pool: the benchmark's 40 TRAIN items (neither dev nor test), rendered exactly
as the eval renders them; activations are read on the prompt only, never an answer.

Eval, on the test split, all on the same HF engine (vLLM cannot steer, and HF and vLLM
numerics differ, so no cell is borrowed from the vLLM runs):

    baseline   no system message
    text       livemath_ts as the system message
    placebo    placebo_livemath_ts as the system message
    B1, B2, CONTROL   no system message, h_l += gamma * ||h_l|| * v_hat at every position

Steered prompts are byte-identical to baseline, so any difference is the vector's.
Layers and gamma are fixed in advance (Adil's LiveMath operating points: 8B L34,
14B L37, 27B L62, gamma 0.3, relative mode), not picked on test.

    python vec_mcq.py extract  --bench B --out-dir D
    python vec_mcq.py fidelity --bench B --out-dir D --layer L
    python vec_mcq.py eval     --bench B --out-dir D --cond C [--layer L --gamma G]
    python vec_mcq.py report   --out-dir D

KIT must point at a kit checkout (for src/hooks.py and src/qwen.py); MODEL_ID selects the model.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
import time

KIT = os.environ.get("KIT", os.path.expanduser("~/vec_arm/kit"))
sys.path.insert(0, KIT)
MQ = os.path.expanduser(os.environ.get("MQ", "~/mcq_math"))
LETTERS = "ABCDEFGHIJ"
SKILL = f"{MQ}/skills/livemath_ts.md"
PLACEBO = f"{MQ}/skills/placebo_livemath_ts.md"
ANSWER_CUE = "\n\nAnswer:"
DEFAULT_LAYER = {"qwen3-8b": 34, "qwen3-14b": 37, "qwen3.6-27b": 62}


# ------------------------------------------------------------ data ---------

def render(row: dict) -> str:
    """Identical to mcq_math/evaluate_vllm_mcq.py, so HF cells see the vLLM cells' prompt."""
    opts = "\n".join(f"{LETTERS[i]}. {t}" for i, t in enumerate(row["options"]))
    return (f"{row['question']}\n\n{opts}\n\nEnd your reply with a line of the form "
            f"`Answer: <letter>` giving the single best choice.")


def parse(pred: str, k: int) -> str | None:
    """Format-neutral committed letter, copied from mcq_math/evaluate_vllm_mcq.py."""
    valid = LETTERS[:k]
    commits = re.findall(
        rf"(?:Answer:\s*(?:<(?:answer|letter)>)?|<(?:answer|letter)>)\s*\**\(?([{valid}])\b(?!\w)", pred, re.I)
    if commits:
        return commits[-1].upper()
    for line in reversed([l.strip() for l in pred.strip().split("\n") if l.strip()]):
        m = re.fullmatch(rf"\**\(?([{valid}])\)?\.?\**", line, re.I)
        return m.group(1).upper() if m else None
    return None


def rows_for(bench: str, split: str) -> list[dict]:
    rows = [json.loads(l) for l in open(f"{MQ}/data/{bench}.jsonl")]
    P = f"{MQ}/protocol/{bench}"
    dev, test = set(json.load(open(f"{P}/ids_val.json"))), set(json.load(open(f"{P}/ids_test.json")))
    keep = {"train": lambda i: i not in dev and i not in test,
            "dev": lambda i: i in dev, "test": lambda i: i in test}[split]
    return [r for r in rows if keep(r["id"])]


# ------------------------------------------------------- generation --------

def _decode(torch, tok, model, prompts, max_new, bs):
    from src import qwen
    dev = qwen.first_param_device(model)
    outs = []
    for i in range(0, len(prompts), bs):
        chunk = prompts[i:i + bs]
        oom = False
        try:
            enc = tok(chunk, return_tensors="pt", padding=True, padding_side="left").to(dev)
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=max_new, do_sample=False, temperature=None,
                                     top_p=None, top_k=None, pad_token_id=tok.pad_token_id)
            new = tok.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        except torch.OutOfMemoryError:
            oom = True
        # Retry OUTSIDE the except block: inside it, the live exception keeps the failed
        # attempt's activations referenced, so the retry starts with the card still full
        # (2026-10-26: SuperGPQA 27B forcing pass OOMed down to batch 1 this way).
        enc = gen = None
        if oom:
            torch.cuda.empty_cache()
            if len(chunk) == 1:
                raise RuntimeError("OOM at batch size 1")
            h = len(chunk) // 2
            print(f"[vec] oom: batch {len(chunk)} -> {h}", flush=True)
            outs += _decode(torch, tok, model, chunk[:h], max_new, h) + _decode(torch, tok, model, chunk[h:], max_new, h)
            continue
        outs += new
        print(f"[vec]   {min(i + bs, len(prompts))}/{len(prompts)}", flush=True)
    return outs


def generate(torch, tok, model, prompts, max_new, bs, k):
    """Kit evaluate.generate: decode, then force an answer out of replies that never committed."""
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))   # less padding per batch
    outs = [None] * len(prompts)
    for i, o in zip(order, _decode(torch, tok, model, [prompts[i] for i in order], max_new, bs)):
        outs[i] = o
    idx = [i for i, o in enumerate(outs) if parse(o, k) is None]
    if idx:
        # forcing re-reads prompt + a full reply, far longer than the original prompts: smaller batches
        cont = _decode(torch, tok, model, [prompts[i] + outs[i] + ANSWER_CUE for i in idx], 12, max(1, bs // 4))
        for j, i in enumerate(idx):
            outs[i] += ANSWER_CUE + cont[j]
    return outs, set(idx)


# ------------------------------------------------------------ steps --------

def cmd_extract(a):
    import torch
    from src import hooks, qwen
    tok, model, layers = qwen.load()
    skill, placebo = open(SKILL).read(), open(PLACEBO).read()
    pool = [render(r) for r in rows_for(a.bench, "train")]
    print(f"[vec] extract {a.bench} {qwen.model_tag()} pool={len(pool)} layers={len(layers)}", flush=True)
    dev = qwen.first_param_device(model)

    def read(q, sysmsg):
        ids = tok(qwen.build_prompt(tok, q, system_msg=sysmsg), return_tensors="pt").to(dev)
        with torch.no_grad(), hooks.capture(layers) as store:
            model(**ids)
        return torch.stack([store[l][0] for l in range(len(layers))])

    d = {"B1": [], "B2": [], "CONTROL": []}
    for q in pool:
        hs, hp, hn = read(q, skill), read(q, placebo), read(q, None)
        d["B1"].append(hs - hp); d["B2"].append(hs - hn); d["CONTROL"].append(hp - hn)
    for name, diffs in d.items():
        st = torch.stack(diffs)
        mean = st.mean(0)
        coh = torch.nn.functional.cosine_similarity(st, mean.unsqueeze(0).expand_as(st), dim=-1).mean(0)
        out = f"{a.out_dir}/vectors/v_{qwen.model_tag()}_{a.bench}_{name}.pt"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        torch.save({"vectors": {l: mean[l].clone() for l in range(len(layers))}, "norm": mean.norm(dim=-1),
                    "coherence": coh, "meta": {"bench": a.bench, "arm": name, "pool": "train", "n": len(pool),
                                               "n_layers": len(layers), "model": qwen.MODEL_ID}}, out)
        L = DEFAULT_LAYER.get(qwen.model_tag())
        print(f"[vec] saved {out}  coherence@L{L}={coh[L]:+.3f} norm@L{L}={mean[L].norm():.2f}", flush=True)


def cmd_fidelity(a):
    """Kit fidelity.py on 16 dev items: 1 - KL(text||steered)/KL(text||plain). Diagnostic only;
    the operating point is fixed in advance. Each vector is measured from the base it was
    extracted against (B1 from the placebo; B2 and CONTROL from no system message)."""
    import torch
    import torch.nn.functional as F
    from src import hooks, qwen
    tok, model, layers = qwen.load()
    dev = qwen.first_param_device(model)
    qs = [render(r) for r in rows_for(a.bench, "dev")[:16]]
    skill, placebo = open(SKILL).read(), open(PLACEBO).read()
    tag = qwen.model_tag()
    L = a.layer or DEFAULT_LAYER[tag]

    def lp(p, y, ctx=None):
        ids = torch.cat([p, y], 1)
        with torch.no_grad():
            if ctx is None:
                logits = model(input_ids=ids).logits
            else:
                with ctx:
                    logits = model(input_ids=ids).logits
        s = p.shape[1] - 1
        return F.log_softmax(logits[0, s:s + y.shape[1]].float(), -1)

    kl = lambda P, Q: (P.exp() * (P - Q)).sum(-1).mean().item()
    res = {}
    for arm, target, base in [("B1", skill, placebo), ("B2", skill, None), ("CONTROL", placebo, None)]:
        blob = torch.load(f"{a.out_dir}/vectors/v_{tag}_{a.bench}_{arm}.pt", map_location="cpu")
        cases = []
        for q in qs:
            pt = tok(qwen.build_prompt(tok, q, system_msg=target), return_tensors="pt").input_ids.to(dev)
            pb = tok(qwen.build_prompt(tok, q, system_msg=base), return_tensors="pt").input_ids.to(dev)
            with torch.no_grad():
                y = model.generate(input_ids=pt, max_new_tokens=96, do_sample=False, temperature=None,
                                   top_p=None, top_k=None, pad_token_id=tok.pad_token_id)[:, pt.shape[1]:]
            t = lp(pt, y)
            cases.append((pb, y, t, kl(t, lp(pb, y))))
        floor = sum(c[3] for c in cases) / len(cases)
        res[arm] = {"floor": floor}
        for g in a.gammas:
            tot = sum(kl(t, lp(pb, y, hooks.inject(layers, {L: blob["vectors"][L]}, gamma=g, mode="relative")))
                      for pb, y, t, _ in cases)
            res[arm][f"L{L}_g{g}"] = 1 - (tot / len(cases)) / floor
        print(f"[vec] fidelity {a.bench} {tag} {arm}: " + json.dumps(res[arm]), flush=True)
    json.dump(res, open(f"{a.out_dir}/fidelity_{tag}_{a.bench}.json", "w"), indent=1)


def cmd_eval(a):
    import torch
    from src import hooks, qwen
    tag = qwen.model_tag()
    L, g = a.layer or DEFAULT_LAYER[tag], a.gamma
    out = f"{a.out_dir}/results/{a.bench}_{tag}_{a.cond}_test.json"
    if os.path.exists(out):
        print(f"[vec] exists, skipping: {out}", flush=True)
        return
    rows = rows_for(a.bench, "test")[:a.limit or None]
    tok, model, layers = qwen.load()
    sysmsg = {"text": open(SKILL).read(), "placebo": open(PLACEBO).read()}.get(a.cond)
    prompts = [qwen.build_prompt(tok, render(r), system_msg=sysmsg) for r in rows]
    k = max(len(r["options"]) for r in rows)
    meta = {}
    t0 = time.time()
    if a.cond in ("B1", "B2", "CONTROL"):
        blob = torch.load(f"{a.out_dir}/vectors/v_{tag}_{a.bench}_{a.cond}.pt", map_location="cpu")
        meta = {"layer": L, "gamma": g, "mode": "relative", "coherence": float(blob["coherence"][L])}
        with hooks.inject(layers, {L: blob["vectors"][L]}, gamma=g, mode="relative"):   # forcing steered too
            outs, forced = generate(torch, tok, model, prompts, a.max_new_tokens, a.batch_size, k)
    else:
        outs, forced = generate(torch, tok, model, prompts, a.max_new_tokens, a.batch_size, k)
    recs = []
    for i, (r, o) in enumerate(zip(rows, outs)):
        p = parse(o, len(r["options"]))
        recs.append({"id": r["id"], "gold": r["answer"], "pred": p, "em": float(p == r["answer"]),
                     "forced": i in forced, "centroid_right": r.get("centroid_right"), "raw": o})
    n = len(recs)
    summ = {"bench": a.bench, "model": qwen.MODEL_ID, "cond": a.cond, "n": n, "engine": "hf",
            "em": sum(r["em"] for r in recs) / n, "forced": len(forced),
            "mean_chars": sum(len(r["raw"]) for r in recs) / n, "max_new_tokens": a.max_new_tokens,
            "seconds": round(time.time() - t0, 1), "vector": meta}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"summary": summ, "records": recs}, open(out, "w"))
    print("[vec] " + json.dumps(summ), flush=True)


def mcnemar(a, b):
    up = sum(1 for i in a if not a[i] and b[i])
    dn = sum(1 for i in a if a[i] and not b[i])
    n = up + dn
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, j) for j in range(min(up, dn) + 1)) / 2 ** n)
    return up, dn, p


def cmd_report(a):
    CONDS = ["baseline", "placebo", "text", "B1", "B2", "CONTROL"]
    PAIRS = [("text", "placebo"), ("B1", "CONTROL"), ("B2", "CONTROL"), ("B1", "text")]
    keys = sorted({tuple(os.path.basename(f).rsplit("_", 2)[0].rsplit("_", 1))
                   for f in glob.glob(f"{a.out_dir}/results/*_test.json")})
    for bench, tag in keys:
        load = lambda c: (lambda f: json.load(open(f)) if os.path.exists(f) else None)(
            f"{a.out_dir}/results/{bench}_{tag}_{c}_test.json")
        res = {c: load(c) for c in CONDS}
        if not res["baseline"]:
            continue
        em = {c: {r["id"]: r["em"] for r in d["records"]} for c, d in res.items() if d}
        print(f"\n== {bench}  {tag}  (HF engine, test n={len(em['baseline'])})")
        for c in CONDS:
            if c not in em:
                continue
            s = res[c]["summary"]
            acc = 100 * sum(em[c].values()) / len(em[c])
            extra = f"  chars={s['mean_chars']:.0f} forced={s['forced']}"
            if s.get("vector"):
                extra += f"  L{s['vector']['layer']} g{s['vector']['gamma']} coh={s['vector']['coherence']:+.2f}"
            if c == "baseline":
                print(f"  {c:9s} {acc:5.1f}{extra}")
            else:
                up, dn, p = mcnemar(em["baseline"], em[c])
                print(f"  {c:9s} {acc:5.1f}{'*' if p < .05 else ' '} ({acc - 100 * sum(em['baseline'].values()) / len(em['baseline']):+.1f}, +{up}/-{dn} p={p:.2g}){extra}")
        for x, y in PAIRS:
            if x in em and y in em:
                up, dn, p = mcnemar(em[y], em[x])
                print(f"  {x} vs {y}: +{up}/-{dn} p={p:.2g}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extract", "fidelity", "eval", "report"])
    ap.add_argument("--bench")
    ap.add_argument("--out-dir", default=os.path.expanduser("~/vec_arm"))
    ap.add_argument("--cond", choices=["baseline", "text", "placebo", "B1", "B2", "CONTROL"])
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--gamma", type=float, default=0.3)
    ap.add_argument("--gammas", type=float, nargs="+", default=[0.1, 0.2, 0.3, 0.5])
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0, help="eval: first N test items (smoke runs only)")
    a = ap.parse_args()
    {"extract": cmd_extract, "fidelity": cmd_fidelity, "eval": cmd_eval, "report": cmd_report}[a.cmd](a)
