"""Text-skill runner for k-option MCQ math (MMLU-Pro math, SuperGPQA math) on vLLM.

    MODEL_ID=Qwen/Qwen3-8B python evaluate_vllm_mcq.py --data <set>.jsonl \
        --skills none skills/placebo_matched.md skills/strength_audit.md ... --out-dir <dir>

Mirrors src/evaluate_vllm.py: one model load serves every condition, greedy
decoding, thinking off, the same prompt shape as LiveMath (options lettered, then
"End your reply with a line of the form `Answer: <letter>`"), and the same answer
forcing for replies that never commit. The only change is the letter range
(A..J instead of A..E), so it is self-contained rather than importing the
LiveMath-only helpers. Cells from this runner are compared only with each other.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time

LETTERS = "ABCDEFGHIJ"
ANSWER_CUE = "\n\nAnswer:"


def render(row: dict) -> str:
    opts = "\n".join(f"{LETTERS[i]}. {t}" for i, t in enumerate(row["options"]))
    return (f"{row['question']}\n\n{opts}\n\nEnd your reply with a line of the form "
            f"`Answer: <letter>` giving the single best choice.")


def parse(pred: str, k: int) -> str | None:
    """The committed letter or None. Strict, as parse_livemath: no 'last capital anywhere'.

    Format-neutral. A skill may tell the model to answer as <answer>X</answer>
    (SkillOpt's format) while the kit prompt asks for `Answer: <letter>`; the model
    then writes hybrids such as `Answer: <answer>G</answer>` or takes the
    placeholder literally, `Answer: <letter>H</letter>`. Reading only `Answer: X`
    scored those as unparsed and forced them, which cost SkillOpt drafts up to ~30
    points on Qwen3-8B dev for a format clash, not maths. Every committed form
    counts; the last one wins (a forcing cue's continuation repeats the model's own).
    """
    valid = LETTERS[:k]
    commits = re.findall(
        rf"(?:Answer:\s*(?:<(?:answer|letter)>)?|<(?:answer|letter)>)\s*\**\(?([{valid}])\b(?!\w)", pred, re.I)
    if commits:
        return commits[-1].upper()
    for line in reversed([l.strip() for l in pred.strip().split("\n") if l.strip()]):
        m = re.fullmatch(rf"\**\(?([{valid}])\)?\.?\**", line, re.I)
        return m.group(1).upper() if m else None
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--skills", nargs="+", required=True, help="skill .md paths, or 'none'")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--ids", default=None, help="json list of question ids to keep (dev or test split)")
    ap.add_argument("--tag", default="", help="suffix for output names, e.g. dev / test")
    args = ap.parse_args()

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    model_id = os.environ.get("MODEL_ID", "Qwen/Qwen3-8B")
    tag = model_id.split("/")[-1].lower()
    bench = os.path.basename(args.data).replace(".jsonl", "")
    rows = [json.loads(l) for l in open(args.data)]
    if args.ids:
        keep = set(json.load(open(args.ids)))
        rows = [r for r in rows if r["id"] in keep]
        assert len(rows) == len(keep), f"{len(keep) - len(rows)} ids not found in {args.data}"
    tok = AutoTokenizer.from_pretrained(model_id)
    llm = LLM(model=model_id, dtype="bfloat16", max_model_len=args.max_model_len,
              gpu_memory_utilization=float(os.environ.get("GPU_UTIL", "0.90")), enable_prefix_caching=True,
              seed=0, max_num_seqs=256)
    greedy = SamplingParams(temperature=0.0, max_tokens=args.max_new_tokens)
    cue = SamplingParams(temperature=0.0, max_tokens=12)
    os.makedirs(args.out_dir, exist_ok=True)

    def prompt(row, skill):
        msgs = ([{"role": "system", "content": skill}] if skill else []) + [{"role": "user", "content": render(row)}]
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)

    for sk in args.skills:
        skill = None if sk == "none" else open(sk).read()
        name = "baseline" if sk == "none" else os.path.basename(sk)[:-3]
        out_path = os.path.join(args.out_dir, f"{bench}_{tag}_{name}{'_' + args.tag if args.tag else ''}.json")
        if os.path.exists(out_path):
            print(f"[skip] {out_path}", flush=True)
            continue
        prompts = [prompt(r, skill) for r in rows]
        t0 = time.time()
        outs = [o.outputs[0].text for o in llm.generate(prompts, greedy)]
        idx = [j for j, (o, r) in enumerate(zip(outs, rows)) if parse(o, len(r["options"])) is None]
        if idx:
            for c, j in zip(llm.generate([prompts[j] + outs[j] + ANSWER_CUE for j in idx], cue), idx):
                outs[j] = outs[j] + ANSWER_CUE + c.outputs[0].text
        recs = []
        for r, o in zip(rows, outs):
            p = parse(o, len(r["options"]))
            recs.append({"id": r["id"], "gold": r["answer"], "pred": p, "em": float(p == r["answer"]),
                         "centroid_right": r["centroid_right"], "source": r.get("source", ""), "raw": o})
        n = len(recs)
        summary = {"bench": bench, "model": model_id, "skill": name, "n": n,
                   "em": sum(x["em"] for x in recs) / n,
                   "parse_rate": sum(x["pred"] is not None for x in recs) / n,
                   "forced": len(idx), "seconds": round(time.time() - t0, 1),
                   "max_new_tokens": args.max_new_tokens}
        json.dump({"summary": summary, "records": recs}, open(out_path, "w"), indent=1)
        print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
