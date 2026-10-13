"""LiveMath text-skill runner on vLLM -- for searching over many skill drafts.

Same prompt, same answer forcing and same scorer as src/evaluate.py (they are
imported, not copied), only the inference engine differs: greedy decoding in
vLLM instead of HF `generate`. Greedy outputs are NOT bit-identical across the
two engines, so cells from this runner are compared only with cells from this
runner. Results go to results_vllm/, never results/, so report.py and the
existing tables cannot merge them with the transformers cells.

One process loads the model once and runs every condition passed to --skills
("none" = baseline), which saves a model load per condition.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import qwen  # noqa: E402
from src.evaluate import (ANSWER_CUE, has_answer, load_domain,  # noqa: E402
                          parse_livemath, render_question, score_livemath)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills", nargs="+", required=True,
                    help="skill .md paths, or 'none' for the baseline")
    ap.add_argument("--ids", default=None, help="json list/dict of question ids to keep")
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "results_vllm"))
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--max-num-seqs", type=int, default=256)
    args = ap.parse_args()

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    rows = load_domain("livemath", None)
    if args.ids:
        keep = set(json.load(open(args.ids)))
        rows = [r for r in rows if r["id"] in keep]
    i, k = (int(x) for x in args.shard.split("/"))
    rows = rows[i::k]

    model_id = qwen.MODEL_ID
    tag = qwen.model_tag()
    tok = AutoTokenizer.from_pretrained(model_id)
    llm = LLM(model=model_id, dtype="bfloat16", max_model_len=args.max_model_len,
              gpu_memory_utilization=0.90, enable_prefix_caching=True, seed=0,
              max_num_seqs=args.max_num_seqs)
    greedy = SamplingParams(temperature=0.0, max_tokens=args.max_new_tokens)
    cue = SamplingParams(temperature=0.0, max_tokens=12)
    ok = has_answer("livemath")
    os.makedirs(args.out_dir, exist_ok=True)

    for sk in args.skills:
        skill_txt = None if sk == "none" else open(sk).read()
        name = "baseline" if sk == "none" else os.path.basename(sk)[:-3]
        prompts = [qwen.build_prompt(tok, render_question("livemath", r), system_msg=skill_txt)
                   for r in rows]
        t0 = time.time()
        res = llm.generate(prompts, greedy)
        outs = [o.outputs[0].text for o in res]
        ntok = [len(o.outputs[0].token_ids) for o in res]
        idx = [j for j, o in enumerate(outs) if not ok(o)]
        if idx:
            cont = llm.generate([prompts[j] + outs[j] + ANSWER_CUE for j in idx], cue)
            for c, j in zip(cont, idx):
                outs[j] = outs[j] + ANSWER_CUE + c.outputs[0].text
        dt = time.time() - t0

        recs = []
        for r, p, nt in zip(rows, outs, ntok):
            recs.append({"id": r["id"], "gold": r["answer"], "pred": parse_livemath(p),
                         "em": score_livemath(p, r["answer"]), "gen_tokens": nt, "raw": p})
        n = len(recs)
        summ = {"domain": "livemath", "engine": f"vllm", "condition": name,
                "model": model_id, "model_tag": tag, "skill": None if sk == "none" else os.path.basename(sk),
                "n": n, "em": sum(x["em"] for x in recs) / max(n, 1),
                "parse_rate": sum(parse_livemath(x["raw"]) is not None for x in recs) / max(n, 1),
                "forced": len(idx), "forced_rate": len(idx) / max(n, 1),
                "max_new_tokens": args.max_new_tokens, "seconds": round(dt, 1), "shard": args.shard}
        out = os.path.join(args.out_dir,
                           f"livemath_{tag}_{name}_s{i}of{k}.json")
        json.dump({"summary": summ, "records": recs}, open(out, "w"), indent=1)
        print(json.dumps(summ), flush=True)


if __name__ == "__main__":
    main()
