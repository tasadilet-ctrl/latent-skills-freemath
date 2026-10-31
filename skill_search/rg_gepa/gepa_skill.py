"""Optimize a per-task skill (system prompt) with GEPA on Reasoning Gym.

usage: gepa_skill.py --task T --out_dir DIR [--budget 1200]
Train seed 11 (n=60) feeds reflection, val seed 12 (n=40) selects; test seeds are never touched here.
The reflection LM is the target model itself (same vLLM server), thinking off.
"""
import argparse, asyncio, json, os
import gepa
from gepa.core.adapter import EvaluationBatch
from openai import OpenAI, AsyncOpenAI
import rg_eval

MAX_WORDS = 300
SEED_SKILL = "Solve the task step by step and check your work before answering."

class RGAdapter:
    propose_new_texts = None  # use GEPA's default reflective proposer
    def __init__(self, port, conc=64):
        self.port, self.conc = port, conc

    def evaluate(self, batch, candidate, capture_traces=False):
        skill = candidate["skill"]
        if len(skill.split()) > MAX_WORDS:
            fb = f"The skill is {len(skill.split())} words; it must be at most {MAX_WORDS} words."
            return EvaluationBatch(outputs=[None]*len(batch), scores=[0.0]*len(batch),
                                   trajectories=[dict(feedback=fb)]*len(batch) if capture_traces else None)
        async def go():
            async with AsyncOpenAI(base_url=f"http://localhost:{self.port}/v1", api_key="x", timeout=3600) as cli:
                sem = asyncio.Semaphore(self.conc)
                return await asyncio.gather(*[rg_eval.ask(cli, sem, skill, b["entry"]["question"], 2048) for b in batch])
        outs = asyncio.run(go())
        scores, trajs = [], []
        for b, (text, fin, forced) in zip(batch, outs):
            a = rg_eval.extract(text)
            try: s = float(b["ds"].score_answer(a, b["entry"])) if a is not None else 0.0
            except Exception: s = 0.0
            s = 1.0 if s >= 1.0 else 0.0
            scores.append(s)
            fb = ("Correct." if s else f"Incorrect. Expected answer: {b['entry']['answer']}. Given: {a}.") + \
                 (" The reply hit the length limit before finishing." if fin == "length" else "")
            trajs.append(dict(question=b["entry"]["question"], reply=text[-1500:], feedback=fb))
        return EvaluationBatch(outputs=outs, scores=scores, trajectories=trajs if capture_traces else None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        recs = [{"Inputs": t.get("question", ""), "Generated Outputs": t.get("reply", ""), "Feedback": t["feedback"]}
                for t in eval_batch.trajectories]
        return {"skill": recs}

TEMPLATE = """I give a language model a short "skill" as its system prompt: general, reusable guidance for one kind of task.
Current skill:
```
<curr_param>
```
Below are task instances, the model's replies (ends only), and feedback:
```
<side_info>
```
Write an improved skill. Requirements: describe a general step-by-step procedure that makes the model solve NEW instances of this kind correctly; at most 300 words; do NOT copy any specific instance, number or answer from the examples; do not mention the examples. Return only the new skill inside ``` blocks."""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True); ap.add_argument("--out_dir", required=True)
    ap.add_argument("--budget", type=int, default=1200); ap.add_argument("--port", type=int, default=8100)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    def mk(seed, n):
        d, es = rg_eval.items(a.task, n, seed)
        return [dict(ds=d, entry=e) for e in es]
    train, val = mk(11, 60), mk(12, 40)
    cli = OpenAI(base_url=f"http://localhost:{a.port}/v1", api_key="x", timeout=3600)
    def reflect(prompt):
        r = cli.chat.completions.create(model="target", messages=[{"role": "user", "content": prompt}], temperature=0.7,
                                        max_tokens=2048, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
        return r.choices[0].message.content or ""
    res = gepa.optimize(seed_candidate={"skill": SEED_SKILL}, trainset=train, valset=val, adapter=RGAdapter(a.port),
                        reflection_lm=reflect, reflection_prompt_template=TEMPLATE, reflection_minibatch_size=4,
                        max_metric_calls=a.budget, run_dir=os.path.join(a.out_dir, "gepa_run"), seed=0,
                        display_progress_bar=False)
    best = res.best_candidate["skill"]
    open(os.path.join(a.out_dir, "skill.md"), "w").write(best)
    json.dump(dict(task=a.task, val_scores=list(res.val_aggregate_scores), best_idx=res.best_idx,
                   candidates=[c["skill"] for c in res.candidates]), open(os.path.join(a.out_dir, "history.json"), "w"), indent=1)
    print(f"{a.task}: seed val={res.val_aggregate_scores[0]:.3f} best val={res.val_aggregate_scores[res.best_idx]:.3f} "
          f"({len(res.candidates)} candidates, {len(best.split())} words)")

if __name__ == "__main__":
    main()
