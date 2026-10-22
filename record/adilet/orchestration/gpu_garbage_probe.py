"""Batch probe for silent GPU output corruption: 64 real MMLU-Pro prompts through vLLM Qwen3-8B.
A healthy card gives readable answers; the faulty GPU 0 (2026-10-22) gave locklocklock... for 64/64.
    CUDA_VISIBLE_DEVICES=<n> python gpu_garbage_probe.py"""
import json, re
from vllm import LLM, SamplingParams
rows = [json.loads(l) for l in open("/data/home/adilet_tasbolat/mcq_math/data/mmlupro_math_tq_sb.jsonl")][:64]
L = "ABCDEFGHIJ"
llm = LLM(model="Qwen/Qwen3-8B", max_model_len=8192, gpu_memory_utilization=0.85, seed=0, enable_prefix_caching=True)
tok = llm.get_tokenizer()
ps = [tok.apply_chat_template([{"role": "user", "content": r["question"] + "\n\n" + "\n".join(f"{L[i]}. {t}" for i, t in enumerate(r["options"])) + "\n\nEnd with Answer: <letter>."}],
      tokenize=False, add_generation_prompt=True, enable_thinking=False) for r in rows]
outs = [o.outputs[0].text for o in llm.generate(ps, SamplingParams(temperature=0, max_tokens=512))]
garb = sum(1 for o in outs if re.search(r"(\w{2,8})\1{6,}", o.replace(" ", "").lower()))
right = sum(1 for o, r in zip(outs, rows) if re.findall(r"Answer:\s*\**\(?([A-J])", o) and re.findall(r"Answer:\s*\**\(?([A-J])", o)[-1] == r["answer"])
print(f"PROBE garbage={garb}/64 correct={right}/64 sample={outs[0][-100:]!r}", flush=True)
