"""Temperature-1.0 test runner for k-option MCQ math (GUIDE_T1_5RUNS.md section 5).

    MODEL_ID=Qwen/Qwen3-8B python evaluate_mcq_t1.py --data ~/mcq_math/data/mmlupro_math_tq_sb.jsonl \
        --skills none skills/4b_r1.md skills/8b_r1.md skills/14b_r1.md skills/27b_r1.md \
        --temperature 1.0 --seed 1 --attention-backend FLASHINFER --max-model-len 16384 \
        --max-new-tokens 2048 --out-dir results/r1

Prompt, answer forcing and parser are mcq_math/evaluate_vllm_mcq.py's (imported, not copied), which
is also what the mcqkit SkillOpt env sends during training. Changes: sampling at --temperature with
engine seed --seed (top_p 1), the cue sampled at the same temperature, and the guide's file layout:
<out-dir>/<bench>_<model tag>_<condition>_s0of1.json, condition = "baseline" or the skill file's stem
(e.g. 8b_r3). Every question is answered; held-out ids are chosen when the table is made.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/mcq_math"))
from evaluate_vllm_mcq import ANSWER_CUE, parse, render  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--skills", nargs="+", required=True, help="skill .md paths, or 'none'")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--attention-backend", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--max-model-len", type=int, default=16384)
    args = ap.parse_args()

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    model_id = os.environ.get("MODEL_ID", "Qwen/Qwen3-8B")
    tag = model_id.split("/")[-1].lower()
    bench = os.path.basename(args.data).replace(".jsonl", "")
    rows = [json.loads(l) for l in open(args.data)]
    os.makedirs(args.out_dir, exist_ok=True)
    todo = []
    for sk in args.skills:
        cond = "baseline" if sk == "none" else os.path.basename(sk)[:-3]
        out = os.path.join(args.out_dir, f"{bench}_{tag}_{cond}_s0of1.json")
        if os.path.exists(out):
            print(f"[skip] {out}", flush=True)
        else:
            todo.append((sk, cond, out))
    if not todo:
        return

    tok = AutoTokenizer.from_pretrained(model_id)
    llm = LLM(model=model_id, dtype="bfloat16", max_model_len=args.max_model_len,
              gpu_memory_utilization=float(os.environ.get("GPU_UTIL", "0.90")), enable_prefix_caching=True,
              seed=args.seed, max_num_seqs=256,
              **({"attention_backend": args.attention_backend} if args.attention_backend else {}))
    samp = SamplingParams(temperature=args.temperature, top_p=1.0, max_tokens=args.max_new_tokens)
    cue = SamplingParams(temperature=args.temperature, top_p=1.0, max_tokens=12)

    def prompt(row, skill):
        msgs = ([{"role": "system", "content": skill}] if skill else []) + [{"role": "user", "content": render(row)}]
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)

    for sk, cond, out in todo:
        skill = None if sk == "none" else open(sk).read()
        prompts = [prompt(r, skill) for r in rows]
        t0 = time.time()
        outs = [o.outputs[0].text for o in llm.generate(prompts, samp)]
        idx = [j for j, (o, r) in enumerate(zip(outs, rows)) if parse(o, len(r["options"])) is None]
        if idx:
            for c, j in zip(llm.generate([prompts[j] + outs[j] + ANSWER_CUE for j in idx], cue), idx):
                outs[j] = outs[j] + ANSWER_CUE + c.outputs[0].text
        forced = set(idx)
        recs = []
        for j, (r, o) in enumerate(zip(rows, outs)):
            p = parse(o, len(r["options"]))
            recs.append({"id": r["id"], "gold": r["answer"], "pred": p, "em": float(p == r["answer"]),
                         "forced": j in forced, "centroid_right": r["centroid_right"], "raw": o})
        n = len(recs)
        summary = {"bench": bench, "model": model_id, "model_tag": tag, "condition": cond,
                   "skill": None if sk == "none" else os.path.basename(sk), "n": n,
                   "em": sum(x["em"] for x in recs) / n, "forced": len(idx), "forced_rate": len(idx) / n,
                   "temperature": args.temperature, "seed": args.seed, "max_new_tokens": args.max_new_tokens,
                   "attention_backend": args.attention_backend, "seconds": round(time.time() - t0, 1)}
        json.dump({"summary": summary, "records": recs}, open(out, "w"), indent=1)
        print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
