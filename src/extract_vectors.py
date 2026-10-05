"""Build v_skill = E[h_l | S_text] - E[h_l | vanilla] at every decoder layer.

For each prompt in the pool the model is run twice -- once with the skill
markdown as the system message, once with no system message -- and the hidden
state at the FINAL PROMPT TOKEN is read from every layer. v_skill is the mean
of the (with - without) differences.

Two pools are supported, and the difference between them is the ablation:
  --pool neutral  domain-neutral everyday tasks; domain signal cancels, so
                  what survives the mean should be the procedure alone
  --pool source   GSM8K training questions; the literal reading of the plan,
                  but the vector may carry math content as well as procedure

Diagnostics saved alongside each vector:
  norm        L2 norm of the mean difference at that layer
  coherence   mean cosine(per-example diff, mean diff). High => the skill has a
              single consistent direction. Low => the mean is averaging away
              inconsistent effects and injection will not reproduce the skill.
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


def load_pool(name: str, n: int) -> list[str]:
    if name == "neutral":
        path = os.path.join(ROOT, "pools", "neutral_tasks.jsonl")
        key = "prompt"
    elif name == "source":
        path = os.path.join(ROOT, "data", "gsm8k_train.jsonl")
        key = "question"
    elif name == "spreadsheet":
        # In-domain pool for SpreadsheetBench, rendered exactly as the eval
        # renders it (instruction + workbook dump + answer location).
        from src import evaluate_spreadsheet as ES
        from src import grade_spreadsheet as GS
        tasks = [t for t in json.load(open(os.path.join(ES.DATA, "dataset.json")))
                 if "exclude" not in t]
        out = []
        for t in tasks:
            init, golden = GS.task_files(ES.DATA, t)
            if init and golden:
                out.append(ES.build_question(t, init))
            if len(out) >= n:
                break
        return out
    elif name == "livemath":
        # In-domain pool, drawn from the EARLIEST months only. The file is
        # sorted by month, so the first n rows are 202511/202512 -- 81 of the
        # 608 evaluated questions. Extraction reads activations on the prompt
        # and never the answer or a generation, but the overlap is real and
        # report.py reports accuracy on the disjoint remainder as well.
        path = os.path.join(ROOT, "data", "livemath.jsonl")
        key = None          # rendered below, not read as a bare field
    else:
        raise ValueError(name)
    out = []
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            # The in-domain pool must present the SAME prompt shape the
            # benchmark does -- question plus the five options plus the answer
            # cue. Extracting on a bare question would build the vector from a
            # context the skill never sees at evaluation time.
            out.append(evaluate.render_question("livemath", row)
                       if key is None else row[key])
            if len(out) >= n:
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", choices=["neutral", "source", "livemath", "spreadsheet"],
                    required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--skill", default=os.path.join(ROOT, "skills", "decompose_verify.md"))
    ap.add_argument("--baseline-skill", default=None, nargs="+",
                    help="length-matched placebo system prompt(s) to contrast "
                         "against instead of no system message at all; removes "
                         "'a long system prompt exists' from the direction. "
                         "Give SEVERAL and the contrast is against their mean, "
                         "which is the robust form: what diverse placebos share "
                         "is prompt-presence, while each one's own idiosyncratic "
                         "direction averages out. A single placebo subtracts its "
                         "idiosyncrasies too -- measured on placebo_matched.md, "
                         "whose brevity instructions sit on the same axis as a "
                         "deliberation skill and cancel much of it.")
    ap.add_argument("--skill-position", default="system", choices=["system", "user"],
                    help="Where the skill text goes. 'system' is the classic "
                         "contrast, but going from NO system message to HAVING "
                         "one is a categorical change in the chat template, and "
                         "a control vector carrying only that change scored "
                         "+3.62 on LiveMath-27B with no skill in it. 'user' "
                         "prepends the skill to the user turn instead, so both "
                         "arms have no system message at all and that jump "
                         "never enters the contrast.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    skill_text = open(args.skill).read()
    base_texts = [open(b).read() for b in (args.baseline_skill or [])] or [None]
    prompts = load_pool(args.pool, args.n)
    print(f"[extract] pool={args.pool} n={len(prompts)} skill={os.path.basename(args.skill)}",
          flush=True)

    tok, model, layers = qwen.load()
    n_layers = len(layers)
    print(f"[extract] model loaded, {n_layers} decoder layers", flush=True)

    diffs = []  # list of Tensor[n_layers, hidden]
    for i, p in enumerate(prompts):
        def read(extra):
            if args.skill_position == "user":
                body = f"{extra}\n\n---\n\n{p}" if extra else p
                text = qwen.build_prompt(tok, body, system_msg=None)
            else:
                text = qwen.build_prompt(tok, p, system_msg=extra)
            ids = tok(text, return_tensors="pt").to(qwen.first_param_device(model))
            with torch.no_grad(), hooks.capture(layers) as store:
                model(**ids)
            return torch.stack([store[l][0] for l in range(n_layers)])
        h_skill = read(skill_text)
        h_base = torch.stack([read(b) for b in base_texts]).mean(dim=0)
        diffs.append(h_skill - h_base)
        if (i + 1) % 10 == 0:
            print(f"[extract]   {i + 1}/{len(prompts)}", flush=True)

    stack = torch.stack(diffs)                 # [n_prompts, n_layers, hidden]
    mean = stack.mean(dim=0)                   # [n_layers, hidden]

    cos = torch.nn.functional.cosine_similarity(
        stack, mean.unsqueeze(0).expand_as(stack), dim=-1)   # [n_prompts, n_layers]
    coherence = cos.mean(dim=0)

    if not args.baseline_skill:
        suffix = "_plain"
    elif len(args.baseline_skill) == 1:
        suffix = "_placebo"
    else:
        suffix = f"_placebo{len(args.baseline_skill)}"
    stem = os.path.basename(args.skill).replace(".md", "")
    out = args.out or os.path.join(
        ROOT, "vectors",
        f"v_{qwen.model_tag()}_{stem}_{args.pool}_n{len(prompts)}"
        f"{'_usr' if args.skill_position == 'user' else ''}{suffix}.pt")
    torch.save({
        "vectors": {l: mean[l].clone() for l in range(n_layers)},
        "norm": mean.norm(dim=-1),
        "coherence": coherence,
        "meta": {"pool": args.pool, "n": len(prompts), "n_layers": n_layers,
                 "skill": os.path.basename(args.skill), "model": qwen.MODEL_ID,
                 "model_tag": qwen.model_tag(),
                 "skill_position": args.skill_position,
                 "baseline_skill": [os.path.basename(x) for x in args.baseline_skill]
                                   if args.baseline_skill else None},
    }, out)
    print(f"[extract] saved {out}", flush=True)
    print("[extract] layer  norm    coherence")
    for l in range(0, n_layers, 4):
        print(f"[extract]  {l:3d}  {mean[l].norm():8.3f}  {coherence[l]:+.3f}")


if __name__ == "__main__":
    main()
