"""Per-question method hints for the MMLU-Pro math test questions (diagnostic: is knowledge the bottleneck?).

Qwen3.6-27B, thinking on, sees each test question WITHOUT its options and WITHOUT the answer, and writes a hint
of at most 60 words naming the key theorem, formula or method. It must not compute the final result. A script
flags hints that contain the gold option's text or announce an answer; flagged ids are reported and excluded
when the hint column is analysed. The hint is then used as that question's system prompt (evaluate_mcq_t1.py
--skills hints:hints_27b.json).
    MODEL_ID=Qwen/Qwen3.6-27B python gen_hints.py --data ... --ids test_ids.json --out hints_27b.json
"""
import argparse, json, os, re, time

INSTR = ("Below is a math question. Do NOT solve it and do NOT state any final numerical result or final "
         "expression. Instead, write a hint of at most 60 words for a student: name the key theorem, formula, "
         "definition or method needed and the first step to take. Output only the hint.\n\nQuestion:\n")

def norm(s):
    return re.sub(r"[\s$\\{}()\[\]]", "", str(s)).lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--ids", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--max-tokens", type=int, default=8192)
    a = ap.parse_args()
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    mid = os.environ.get("MODEL_ID", "Qwen/Qwen3.6-27B")
    ids = set(json.load(open(a.ids)))
    rows = [r for r in (json.loads(l) for l in open(a.data)) if r["id"] in ids]
    tok = AutoTokenizer.from_pretrained(mid)
    llm = LLM(model=mid, dtype="bfloat16", max_model_len=16384, gpu_memory_utilization=0.90, seed=0, max_num_seqs=256,
              enable_prefix_caching=True, attention_backend="FLASHINFER")
    sp = SamplingParams(temperature=0.6, top_p=0.95, top_k=20, max_tokens=a.max_tokens)
    prompts = [tok.apply_chat_template([{"role": "user", "content": INSTR + r["question"]}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=True) for r in rows]
    t0 = time.time()
    outs = [o.outputs[0].text for o in llm.generate(prompts, sp)]
    hints, report = {}, {"model": mid, "n": len(rows), "flagged": {}, "no_hint": []}
    for r, o in zip(rows, outs):
        if "</think>" not in o:
            report["no_hint"].append(r["id"]); continue
        h = o.split("</think>", 1)[1].strip()
        h = " ".join(h.split()[:80])
        hints[r["id"]] = h
        gold = r["options"][ord(r["answer"]) - 65]
        why = []
        g = norm(gold)
        if len(g) >= 2 and g in norm(h):
            why.append("contains gold option text")
        if re.search(r"\b(answer|result)\s+(is|=|equals)\b", h, re.I):
            why.append("announces an answer")
        if why:
            report["flagged"][r["id"]] = why
    report.update(n_hints=len(hints), n_flagged=len(report["flagged"]), seconds=round(time.time() - t0),
                  mean_words=round(sum(len(h.split()) for h in hints.values()) / max(1, len(hints)), 1))
    json.dump(hints, open(a.out, "w"), indent=1, ensure_ascii=False)
    json.dump(report, open(a.out.replace(".json", "_report.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k not in ("flagged", "no_hint")}))

if __name__ == "__main__":
    main()
