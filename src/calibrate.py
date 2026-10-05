"""Sweep (layer band, gamma) to find where injection steers without destroying.

The smoke test showed gamma=1.0 raw across layers 24-40 produces token salad,
so the usable operating point has to be found before the real matrix is run.
Loads the model once and sweeps in-process.

Reported per configuration:
  acc        GSM8K exact match on a small dev slice
  parses     fraction of outputs containing a parseable `Answer:` line
  distinct   distinct-token ratio of the output; collapses toward 0 when the
             model degenerates into repetition, which is the failure mode seen
             at gamma=1.0
A configuration is only usable if `parses` and `distinct` stay near baseline.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import evaluate, hooks, qwen  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def distinct_ratio(tok, text: str) -> float:
    ids = tok(text)["input_ids"]
    return len(set(ids)) / max(len(ids), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--domain", default="gsm8k",
                    choices=["gsm8k", "hotpotqa", "livemath", "math500"])
    ap.add_argument("--n", type=int, default=32)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=320)
    ap.add_argument("--mode", default="relative", choices=["relative", "raw"])
    ap.add_argument("--bands", default="32,40,48,24-40,40-56")
    ap.add_argument("--gammas", default="0.02,0.05,0.1,0.2,0.4")
    args = ap.parse_args()

    blob = torch.load(args.vectors, map_location="cpu")
    n_layers = blob["meta"]["n_layers"]

    # Calibrate on items the eval does not depend on. For gsm8k that is the
    # train split; for livemath there is none, so take the earliest months --
    # the same slice the in-domain extraction pool already consumed, which
    # keeps fresh evaluation items untouched.
    path = {"gsm8k": "data/gsm8k_train.jsonl", "hotpotqa": "data/hotpotqa_dev.jsonl",
            "livemath": "data/livemath.jsonl", "math500": "data/math500.jsonl"}[args.domain]
    rows = []
    with open(os.path.join(ROOT, path)) as f:
        for line in f:
            rows.append(json.loads(line))
            if len(rows) >= args.n:
                break

    scorer = {"gsm8k": evaluate.score_gsm8k, "livemath": evaluate.score_livemath,
              "math500": evaluate.score_math500,
              "hotpotqa": lambda p, g: evaluate.score_hotpot(p, g)[0]}[args.domain]
    committed = evaluate.has_answer(args.domain)

    tok, model, layers = qwen.load()
    prompts = [qwen.build_prompt(tok, evaluate.render_question(args.domain, r))
               for r in rows]

    def run(ctx):
        # No answer-forcing here on purpose: this check exists to SEE
        # degeneration, and forcing would paper over exactly the symptom.
        if ctx is None:
            preds, _ = evaluate.generate(tok, model, prompts, args.max_new_tokens,
                                         args.batch_size)
        else:
            with ctx:
                preds, _ = evaluate.generate(tok, model, prompts, args.max_new_tokens,
                                             args.batch_size)
        acc = sum(scorer(p, r["answer"]) for p, r in zip(preds, rows)) / len(rows)
        parses = sum(committed(p) for p in preds) / len(preds)
        dist = sum(distinct_ratio(tok, p) for p in preds) / len(preds)
        return acc, parses, dist, preds

    results = []
    print(f"\n{'config':<26} {'acc':>6} {'parses':>7} {'distinct':>9}", flush=True)
    print("-" * 52, flush=True)
    acc, par, dist, base_preds = run(None)
    print(f"{'baseline':<26} {acc:>6.3f} {par:>7.2f} {dist:>9.3f}", flush=True)
    results.append({"config": "baseline", "acc": acc, "parses": par, "distinct": dist})

    for band in args.bands.split(","):
        chosen = evaluate.parse_layers(band, n_layers)
        vecs = {l: blob["vectors"][l] for l in chosen}
        for g in (float(x) for x in args.gammas.split(",")):
            ctx = hooks.inject(layers, vecs, gamma=g, mode=args.mode)
            acc, par, dist, preds = run(ctx)
            tag = f"L{band} g{g}"
            print(f"{tag:<26} {acc:>6.3f} {par:>7.2f} {dist:>9.3f}", flush=True)
            results.append({"config": tag, "band": band, "gamma": g,
                            "acc": acc, "parses": par, "distinct": dist,
                            "sample": preds[0][:400]})

    out = os.path.join(ROOT, "results",
                       f"calib_{os.path.basename(args.vectors).replace('.pt','')}"
                       f"_{args.domain}_{args.mode}.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[calibrate] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
