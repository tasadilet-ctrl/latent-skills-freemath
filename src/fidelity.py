"""How faithfully does an embedding skill reproduce its text skill?

Accuracy is too blunt an instrument for tuning an activation vector: if the
skill is worth two points on a benchmark, accuracy cannot separate "the vector
works" from noise. This measures the thing directly.

For each probe prompt:
  1. generate a continuation y under the TEXT skill (system message present) --
     this is the behaviour we are trying to reproduce without the tokens
  2. teacher-force y and read the next-token distribution under three conditions
        text     prompt WITH the skill text            (the target)
        plain    prompt WITHOUT it, no steering        (the floor)
        steered  prompt WITHOUT it, h_l += gamma*v     (what we are testing)
  3. fidelity = 1 - KL(text || steered) / KL(text || plain)

     1.0  steering reproduces the text skill's distribution exactly
     0.0  steering achieves nothing the plain model did not already do
     <0   steering moves AWAY from the skill

Sweeping (layer band, gamma) against this gives an operating point chosen by
how well the vector carries the skill, not by a benchmark score that may be
dominated by whether the model could already do the task.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import evaluate, hooks, qwen  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@torch.no_grad()
def logprobs_for(model, prompt_ids, y_ids, ctx=None):
    """log P(y_t | prompt, y_<t) for every t, as [len(y), vocab]."""
    ids = torch.cat([prompt_ids, y_ids], dim=1)
    if ctx is None:
        logits = model(input_ids=ids).logits
    else:
        with ctx:
            logits = model(input_ids=ids).logits
    n = y_ids.shape[1]
    start = prompt_ids.shape[1] - 1              # logits[i] predicts token i+1
    return F.log_softmax(logits[0, start:start + n].float(), dim=-1)


def mean_kl(log_p, log_q):
    """KL(P || Q) averaged over positions, with P the target distribution."""
    return (log_p.exp() * (log_p - log_q)).sum(-1).mean().item()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--skill", default=os.path.join(ROOT, "skills", "decompose_verify.md"))
    ap.add_argument("--baseline-skill", default=None,
                    help="system prompt for the plain/steered arms; MUST match "
                         "the --baseline-skill the vector was extracted against, "
                         "or steering starts from a different state than the "
                         "one the subtraction was measured from")
    ap.add_argument("--probe", default="gsm8k_train",
                    choices=["gsm8k_train", "hotpotqa_dev", "neutral", "livemath",
                             "spreadsheet"],
                    help="which prompts to measure fidelity on; hotpotqa_dev "
                         "measures whether the vector carries OUT of domain")
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--y-tokens", type=int, default=96)
    ap.add_argument("--mode", default="relative", choices=["relative", "raw"])
    ap.add_argument("--bands", default="32,40,48,24-40,36-52")
    ap.add_argument("--gammas", default="0.02,0.05,0.1,0.2,0.4")
    args = ap.parse_args()

    blob = torch.load(args.vectors, map_location="cpu")
    n_layers = blob["meta"]["n_layers"]
    skill_text = open(args.skill).read()
    base_text = open(args.baseline_skill).read() if args.baseline_skill else None
    if blob["meta"].get("baseline_skill") and not args.baseline_skill:
        print(f"[fidelity] WARNING: vector was extracted against "
              f"{blob['meta']['baseline_skill']} but no --baseline-skill given",
              flush=True)

    # ---- probe prompts -----------------------------------------------------
    questions = []
    if args.probe == "spreadsheet":
        # Same prompt shape the benchmark uses, drawn from the LATE tasks so the
        # probe does not reuse the ones the in-domain extraction pool consumed.
        import json as _json
        from src import evaluate_spreadsheet as ES
        from src import grade_spreadsheet as GS
        _tasks = [t for t in _json.load(open(os.path.join(ES.DATA, "dataset.json")))
                  if "exclude" not in t]
        for t in reversed(_tasks):
            init, golden = GS.task_files(ES.DATA, t)
            if init and golden:
                questions.append(ES.build_question(t, init))
            if len(questions) >= args.n:
                break
    elif args.probe == "neutral":
        with open(os.path.join(ROOT, "pools", "neutral_tasks.jsonl")) as f:
            for line in f:
                questions.append(json.loads(line)["prompt"])
                if len(questions) >= args.n:
                    break
    else:
        path = {"gsm8k_train": "data/gsm8k_train.jsonl",
                "hotpotqa_dev": "data/hotpotqa_dev.jsonl",
                "livemath": "data/livemath.jsonl"}[args.probe]
        dom = {"gsm8k_train": "gsm8k", "hotpotqa_dev": "hotpotqa",
               "livemath": "livemath"}[args.probe]
        rows = [json.loads(l) for l in open(os.path.join(ROOT, path))]
        if args.probe == "livemath":
            # Probe the LATE months. The in-domain extraction pool takes the
            # earliest ones, so measuring fidelity there would score the vector
            # on the very prompts it was built from.
            rows = rows[::-1]
        for r in rows[:args.n]:
            questions.append(evaluate.render_question(dom, r))

    tok, model, layers = qwen.load()
    dev = qwen.first_param_device(model)
    print(f"[fidelity] probe={args.probe} n={len(questions)} "
          f"vec={os.path.basename(args.vectors)} mode={args.mode}", flush=True)

    # ---- targets: what the TEXT skill actually does -------------------------
    cases = []
    for q in questions:
        p_text = tok(qwen.build_prompt(tok, q, system_msg=skill_text),
                     return_tensors="pt").input_ids.to(dev)
        p_plain = tok(qwen.build_prompt(tok, q, system_msg=base_text),
                      return_tensors="pt").input_ids.to(dev)
        with torch.no_grad():
            gen = model.generate(input_ids=p_text, max_new_tokens=args.y_tokens,
                                 do_sample=False, temperature=None, top_p=None,
                                 top_k=None, pad_token_id=tok.pad_token_id)
        y = gen[:, p_text.shape[1]:]
        if y.shape[1] == 0:
            continue
        lp_text = logprobs_for(model, p_text, y)
        lp_plain = logprobs_for(model, p_plain, y)
        cases.append({"p_plain": p_plain, "y": y, "lp_text": lp_text,
                      "kl_floor": mean_kl(lp_text, lp_plain)})
    floor = sum(c["kl_floor"] for c in cases) / len(cases)
    print(f"[fidelity] KL(text || plain) = {floor:.4f}   <- the gap to close\n", flush=True)

    # ---- sweep --------------------------------------------------------------
    rows = []
    print(f"{'config':<20} {'KL(text||steer)':>16} {'fidelity':>10}", flush=True)
    print("-" * 48, flush=True)
    for band in args.bands.split(","):
        chosen = evaluate.parse_layers(band, n_layers)
        vecs = {l: blob["vectors"][l] for l in chosen}
        for g in (float(x) for x in args.gammas.split(",")):
            tot = 0.0
            for c in cases:
                ctx = hooks.inject(layers, vecs, gamma=g, mode=args.mode)
                lp_steer = logprobs_for(model, c["p_plain"], c["y"], ctx=ctx)
                tot += mean_kl(c["lp_text"], lp_steer)
            kl = tot / len(cases)
            fid = 1.0 - kl / floor
            tag = f"L{band} g{g}"
            print(f"{tag:<20} {kl:>16.4f} {fid:>10.3f}", flush=True)
            rows.append({"band": band, "gamma": g, "kl": kl, "fidelity": fid})

    best = max(rows, key=lambda r: r["fidelity"])
    print(f"\n[fidelity] best: L{best['band']} gamma={best['gamma']} "
          f"fidelity={best['fidelity']:.3f}", flush=True)
    out = os.path.join(ROOT, "results",
                       f"fidelity_{os.path.basename(args.vectors).replace('.pt','')}_{args.probe}.json")
    with open(out, "w") as f:
        json.dump({"floor_kl": floor, "probe": args.probe, "rows": rows,
                   "best": best}, f, indent=2)
    print(f"[fidelity] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
