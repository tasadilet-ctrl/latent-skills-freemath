"""Optimize one skill (system prompt) per math-suite benchmark with GEPA.

usage: gepa_math.py --bench B --model HF_ID --out_dir DIR [--budget 1200] [--port 8100]

Same prompt, decoding and forcing as mcq_math/evaluate_vllm_mcq.py and
kit_v4/freemath/evaluate_vllm_freemath.py (prompts are built with the model's chat template and sent
to the vLLM server's completions endpoint, so they are byte-identical). Free-form scoring = the kit's
env/evaluator.py with math_verify installed. Train split feeds reflection, val split selects;
test is never touched here. Reflection LM = the target model itself, thinking off.
"""
import argparse, asyncio, importlib.util, json, os, re, sys
import gepa
from gepa.core.adapter import EvaluationBatch
from openai import OpenAI, AsyncOpenAI
from transformers import AutoTokenizer

H = os.path.expanduser("~")
MCQ = ("mmlupro_math_tq_sb", "supergpqa_math_hard")
MAX_WORDS = 300
MAX_NEW = 2048
SEED_SKILL = "Solve the task step by step and check your work before answering."

# import the kit evaluator under its real module name and put its folder on the path for child
# processes too: its process pool pickles functions by module name, and a module loaded under a
# made-up name cannot be found in the workers (every check then fails and counts as wrong)
_EVDIR = os.path.expanduser("~/skillopt_work/kit_v4/freemath/env")
sys.path.insert(0, _EVDIR); os.environ["PYTHONPATH"] = _EVDIR + os.pathsep + os.environ.get("PYTHONPATH", "")
import evaluator as ev

# ---- copied from the runners (kept identical) ----
LETTERS = "ABCDEFGHIJ"
ANSWER_CUE = "\n\nAnswer:"
FM_SUFFIX = ("\n\nEnd your reply with a line of the form `Answer: $\\boxed{<answer>}$` "
             "containing the final answer only.")
FM_CUE = "\n\nAnswer: $\\boxed{"

def mcq_render(row):
    opts = "\n".join(f"{LETTERS[i]}. {t}" for i, t in enumerate(row["options"]))
    return (f"{row['question']}\n\n{opts}\n\nEnd your reply with a line of the form "
            f"`Answer: <letter>` giving the single best choice.")

def mcq_parse(pred, k):
    valid = LETTERS[:k]
    commits = re.findall(
        rf"(?:Answer:\s*(?:<(?:answer|letter)>)?|<(?:answer|letter)>)\s*\**\(?([{valid}])\b(?!\w)", pred, re.I)
    if commits:
        return commits[-1].upper()
    for line in reversed([l.strip() for l in pred.strip().split("\n") if l.strip()]):
        m = re.fullmatch(rf"\**\(?([{valid}])\)?\.?\**", line, re.I)
        return m.group(1).upper() if m else None
    return None

def close_braces(text):
    i = text.rfind("\\boxed{")
    depth = sum((c == "{") - (c == "}") for c in text[i + 7:]) + 1 if i >= 0 else 0
    return text + "}" * max(depth, 0)
# ---------------------------------------------------

def score_ff(text, gold):
    """Score off the main thread: the kit evaluator then uses its process pool with a hard 20 s deadline
    (in the main thread it relies on signal.alarm, which cannot interrupt sympy stuck in C code)."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(1) as tp:
        return tp.submit(ev.evaluate, text, gold).result()

def load(bench):
    """train, val rows. MCQ train = the items in neither the val nor the test split."""
    if bench in MCQ:
        rows = [json.loads(l) for l in open(f"{H}/mcq_math/data/{bench}.jsonl")]
        p = f"{H}/mcq_math/protocol/{bench}"
        val_ids, test_ids = set(json.load(open(f"{p}/ids_val.json"))), set(json.load(open(f"{p}/ids_test.json")))
        train = [r for r in rows if r["id"] not in val_ids | test_ids]
        val = [r for r in rows if r["id"] in val_ids]
    else:
        s = f"{H}/skillopt_work/fm_split/{bench}"
        train, val = json.load(open(f"{s}/train/items.json")), json.load(open(f"{s}/val/items.json"))
    return train, val

class MathAdapter:
    propose_new_texts = None
    def __init__(self, bench, tok, port, conc=64):
        self.bench, self.tok, self.port, self.conc, self.mcq = bench, tok, port, conc, bench in MCQ

    def user_text(self, row):
        return mcq_render(row) if self.mcq else row["question"] + FM_SUFFIX

    def prompt(self, row, skill):
        msgs = ([{"role": "system", "content": skill}] if skill else []) + [{"role": "user", "content": self.user_text(row)}]
        return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)

    def committed(self, row, text):
        return mcq_parse(text, len(row["options"])) is not None if self.mcq else ev.extract_final(text) is not None

    async def one(self, cli, sem, row, skill):
        async with sem:
            p = self.prompt(row, skill)
            r = await cli.completions.create(model="target", prompt=p, temperature=0.0, max_tokens=MAX_NEW)
            text, fin = r.choices[0].text, r.choices[0].finish_reason
            if not self.committed(row, text):
                cue = ANSWER_CUE if self.mcq else FM_CUE
                c = await cli.completions.create(model="target", prompt=p + text + cue, temperature=0.0,
                                                 max_tokens=12 if self.mcq else 96)
                text = text + cue + c.choices[0].text
                if not self.mcq:
                    text = close_braces(text)
            return text, fin

    def evaluate(self, batch, candidate, capture_traces=False):
        skill = candidate["skill"]
        if len(skill.split()) > MAX_WORDS:
            fb = f"The skill is {len(skill.split())} words; it must be at most {MAX_WORDS} words."
            return EvaluationBatch(outputs=[None] * len(batch), scores=[0.0] * len(batch),
                                   trajectories=[dict(feedback=fb)] * len(batch) if capture_traces else None)
        async def go():
            async with AsyncOpenAI(base_url=f"http://localhost:{self.port}/v1", api_key="x", timeout=3600) as cli:
                sem = asyncio.Semaphore(self.conc)
                return await asyncio.gather(*[self.one(cli, sem, r, skill) for r in batch])
        outs = asyncio.run(go())
        scores, trajs = [], []
        for row, (text, fin) in zip(batch, outs):
            if self.mcq:
                pred = mcq_parse(text, len(row["options"])); s = float(pred == row["answer"])
            else:
                e = score_ff(text, row["answer"]); pred, s = e["predicted_answer"], float(e["em"])
            scores.append(s)
            fb = ("Correct." if s else f"Incorrect. Expected answer: {row['answer']}. Given: {pred}.") + \
                 (" The reply hit the length limit before finishing." if fin == "length" else "")
            trajs.append(dict(question=self.user_text(row)[:2500], reply=text[-1500:], feedback=fb))
        return EvaluationBatch(outputs=outs, scores=scores, trajectories=trajs if capture_traces else None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        return {"skill": [{"Inputs": t.get("question", ""), "Generated Outputs": t.get("reply", ""),
                           "Feedback": t["feedback"]} for t in eval_batch.trajectories]}

TEMPLATE = """I give a language model a short "skill" as its system prompt: general, reusable guidance for one kind of math problem.
Current skill:
```
<curr_param>
```
Below are problems, the model's replies (ends only), and feedback:
```
<side_info>
```
Write an improved skill. Requirements: describe general mathematical methods and working habits that make the model solve NEW problems of this kind correctly; at most 300 words; do NOT copy any specific problem, number, formula or answer from the examples; do not mention the examples; do not give rules for guessing an option from the wording or similarity of the answer choices. Return only the new skill inside ``` blocks."""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True); ap.add_argument("--model", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--budget", type=int, default=1200); ap.add_argument("--port", type=int, default=8100)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    train, val = load(a.bench)
    tok = AutoTokenizer.from_pretrained(a.model)
    cli = OpenAI(base_url=f"http://localhost:{a.port}/v1", api_key="x", timeout=3600)
    def reflect(prompt):
        r = cli.chat.completions.create(model="target", messages=[{"role": "user", "content": prompt}], temperature=0.7,
                                        max_tokens=2048, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
        return r.choices[0].message.content or ""
    res = gepa.optimize(seed_candidate={"skill": SEED_SKILL}, trainset=train, valset=val,
                        adapter=MathAdapter(a.bench, tok, a.port), reflection_lm=reflect,
                        reflection_prompt_template=TEMPLATE, reflection_minibatch_size=4,
                        max_metric_calls=a.budget, run_dir=os.path.join(a.out_dir, "gepa_run"), seed=0,
                        display_progress_bar=False)
    best = res.best_candidate["skill"]
    open(os.path.join(a.out_dir, "skill.md"), "w").write(best)
    json.dump(dict(bench=a.bench, n_train=len(train), n_val=len(val), val_scores=list(res.val_aggregate_scores),
                   best_idx=res.best_idx, candidates=[c["skill"] for c in res.candidates]),
              open(os.path.join(a.out_dir, "history.json"), "w"), indent=1)
    print(f"{a.bench}: seed val={res.val_aggregate_scores[0]:.3f} best val={res.val_aggregate_scores[res.best_idx]:.3f} "
          f"({len(res.candidates)} candidates, {len(best.split())} words)")

if __name__ == "__main__":
    main()
