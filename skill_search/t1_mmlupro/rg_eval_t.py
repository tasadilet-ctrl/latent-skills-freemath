"""Evaluate a model (vLLM OpenAI server) on Reasoning Gym tasks, optionally with a skill as system prompt.

usage: rg_eval_t.py --tasks a,b --n 60 --seed 1 [--skill file.md] --out out.jsonl [--temperature 1.0 --req-seed 1]
rg_eval.py with sampling: --temperature (default 0 = greedy, as rg_eval.py) and a per-request vLLM seed
(req-seed * 1000003 + item index) so a run is reproducible on the same server.
Items are regenerated from (task, seed, index), so gold answers never leave Reasoning Gym.
"""
import argparse, asyncio, json, re, sys
import reasoning_gym as rg
from openai import AsyncOpenAI

SUFFIX = "\n\nEnd your reply with the final answer inside <answer></answer> tags."
ANS = re.compile(r"<answer>(.*?)</answer>", re.S)

def items(task, n, seed, config=None):
    d = rg.create_dataset(task, size=n, seed=seed, **(config or {}))
    return d, [d[i] for i in range(n)]

def extract(text):
    m = ANS.findall(text or "")
    return m[-1].strip() if m else None

async def ask(cli, sem, system, q, max_tokens, temp=0.0, rseed=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": q + SUFFIX}]
    async with sem:
        eb = {"chat_template_kwargs": {"enable_thinking": False}}
        if rseed is not None:
            eb["seed"] = rseed
        r = await cli.chat.completions.create(model="target", messages=msgs, temperature=temp, max_tokens=max_tokens,
                                             extra_body=eb)
        text, fin = r.choices[0].message.content or "", r.choices[0].finish_reason
        forced = False
        if extract(text) is None and fin == "length":  # same forcing as the paper: ask for the answer
            r2 = await cli.chat.completions.create(model="target", temperature=temp, max_tokens=200, stop=["</answer>"],
                messages=msgs + [{"role": "assistant", "content": text + "\n\n<answer>"}],
                extra_body={"chat_template_kwargs": {"enable_thinking": False}, **({"seed": rseed} if rseed is not None else {}),
                            "continue_final_message": True, "add_generation_prompt": False})
            text, forced = text + "\n\n<answer>" + (r2.choices[0].message.content or "") + "</answer>", True
        return text, fin, forced

async def run(tasks, n, seed, system, max_tokens, port, conc, config=None, temp=0.0, req_seed=None):
    cli = AsyncOpenAI(base_url=f"http://localhost:{port}/v1", api_key="x", timeout=3600)
    sem = asyncio.Semaphore(conc)
    jobs, meta = [], []
    for t in tasks:
        d, es = items(t, n, seed, (config or {}).get(t))
        for i, e in enumerate(es):
            jobs.append(ask(cli, sem, system, e["question"], max_tokens, temp, None if req_seed is None else req_seed * 1000003 + i)); meta.append((t, i, d, e))
    outs = await asyncio.gather(*jobs)
    rows = []
    for (t, i, d, e), (text, fin, forced) in zip(meta, outs):
        a = extract(text)
        try: s = float(d.score_answer(a, e)) if a is not None else 0.0
        except Exception: s = 0.0
        rows.append(dict(task=t, idx=i, seed=seed, score=s, correct=s >= 1.0, pred=a, gold=e["answer"],
                         truncated=fin == "length", forced=forced, chars=len(text), reply=text))
    return rows

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True); ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--skill"); ap.add_argument("--out", required=True)
    ap.add_argument("--max_tokens", type=int, default=2048); ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--conc", type=int, default=128); ap.add_argument("--config")
    ap.add_argument("--temperature", type=float, default=0.0); ap.add_argument("--req-seed", type=int, default=None)
    a = ap.parse_args()
    system = open(a.skill).read() if a.skill else None
    cfg = json.load(open(a.config)) if a.config else None
    rows = asyncio.run(run(a.tasks.split(","), a.n, a.seed, system, a.max_tokens, a.port, a.conc, cfg, a.temperature, a.req_seed))
    with open(a.out, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    from collections import defaultdict
    g = defaultdict(list)
    for r in rows: g[r["task"]].append(r)
    for t, rs in g.items():
        print(f"{t:28s} acc={100*sum(r['correct'] for r in rs)/len(rs):5.1f} trunc={100*sum(r['truncated'] for r in rs)/len(rs):4.0f}% chars={sum(r['chars'] for r in rs)//len(rs)}")
