"""Text-skill runner for free-form final-answer math on vLLM: PROTOCOL.md's "same stack" for free-form.

    MODEL_ID=Qwen/Qwen3-8B python evaluate_vllm_freemath.py --items <split>/items.json --bench realmath \
        --tag dev --skills none <skill.md> ... --out-dir <dir> --max-new-tokens 2048

The kit's free-form setup (src/evaluate.py, math500 domain): the question, then
"End your reply with a line of the form `Answer: $\\boxed{<answer>}$` containing the
final answer only.", greedy, thinking off, and the kit's forcing pass: a reply that
never gives a \\boxed{} answer is continued with an answer cue and a short budget.
Scored with env/evaluator.py (string, symbolic, right-hand side, numeric), in the
main thread. Output format matches mcq_math/evaluate_vllm_mcq.py, so
mcq_math/protocol_select.py selects and reports on it unchanged (centroid_right is
False everywhere: free-form questions have no options).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("fm_evaluator", os.path.join(HERE, "env", "evaluator.py"))
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

SUFFIX = ("\n\nEnd your reply with a line of the form `Answer: $\\boxed{<answer>}$` "
          "containing the final answer only.")
CUE = "\n\nAnswer: $\\boxed{"


def close_braces(text: str) -> str:
    """A forced continuation may stop before closing \\boxed{...}; close it so it can be read."""
    i = text.rfind("\\boxed{")
    depth = sum((c == "{") - (c == "}") for c in text[i + 7:]) + 1 if i >= 0 else 0
    return text + "}" * max(depth, 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True, help="fm_split/<bench>/<split>/items.json")
    ap.add_argument("--bench", required=True)
    ap.add_argument("--tag", required=True, help="dev / test")
    ap.add_argument("--skills", nargs="+", required=True, help="skill .md paths, or 'none'")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--max-model-len", type=int, default=8192)
    args = ap.parse_args()

    from vllm import LLM, SamplingParams

    model_id = os.environ.get("MODEL_ID", "Qwen/Qwen3-8B")
    tag = model_id.split("/")[-1].lower()
    rows = json.load(open(args.items))
    llm = LLM(model=model_id, dtype="bfloat16", max_model_len=args.max_model_len,
              gpu_memory_utilization=float(os.environ.get("GPU_UTIL", "0.90")),
              enable_prefix_caching=True, seed=0, max_num_seqs=256)
    tok = llm.get_tokenizer()
    greedy = SamplingParams(temperature=0.0, max_tokens=args.max_new_tokens)
    cue = SamplingParams(temperature=0.0, max_tokens=96)
    os.makedirs(args.out_dir, exist_ok=True)

    def prompt(row, skill):
        msgs = ([{"role": "system", "content": skill}] if skill else []) + \
               [{"role": "user", "content": row["question"] + SUFFIX}]
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)

    for sk in args.skills:
        skill = None if sk == "none" else open(sk).read()
        name = "baseline" if sk == "none" else os.path.basename(sk)[:-3]
        out_path = os.path.join(args.out_dir, f"{args.bench}_{tag}_{name}_{args.tag}.json")
        if os.path.exists(out_path):
            print(f"[skip] {out_path}", flush=True)
            continue
        prompts = [prompt(r, skill) for r in rows]
        t0 = time.time()
        outs = [o.outputs[0].text for o in llm.generate(prompts, greedy)]
        idx = [j for j, o in enumerate(outs) if ev.extract_final(o) is None]
        if idx:
            for c, j in zip(llm.generate([prompts[j] + outs[j] + CUE for j in idx], cue), idx):
                outs[j] = close_braces(outs[j] + CUE + c.outputs[0].text)
        forced = set(idx)
        recs = []
        for j, (r, o) in enumerate(zip(rows, outs)):
            e = ev.evaluate(o, r["answer"])
            recs.append({"id": r["id"], "gold": r["answer"], "pred": e["predicted_answer"], "em": e["em"],
                         "method": e["method"], "forced": j in forced, "centroid_right": False,
                         "source": r.get("task_type", ""), "raw": o})
        n = len(recs)
        summary = {"bench": args.bench, "model": model_id, "skill": name, "split": args.tag, "n": n,
                   "em": sum(x["em"] for x in recs) / n, "forced": len(idx),
                   "no_answer": sum(x["method"] == "no_final_answer" for x in recs),
                   "seconds": round(time.time() - t0, 1), "max_new_tokens": args.max_new_tokens}
        json.dump({"summary": summary, "records": recs}, open(out_path, "w"), indent=1)
        print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
