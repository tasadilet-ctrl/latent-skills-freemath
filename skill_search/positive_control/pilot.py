"""Positive-control pilot: procedural skills on tasks the model cannot do reliably in one step.

    MODEL_ID=Qwen/Qwen3-8B python pilot.py --out results.json --n 150

Tasks are generated with a fixed seed and exact gold answers. Conditions: no system prompt, the
task's skill, and placebo_notation (length-matched presentation advice). Greedy, thinking off,
2048 new tokens; replies that never commit get an answer cue, as in the main runners.
"""
import argparse, datetime, json, os, random, re

WORDS = ("strawberry banana committee mississippi bookkeeper occurrence parallel success embarrass "
         "accommodate possession millennium assessment tennessee referee balloon coffee giraffe "
         "letter hippopotamus seventeen necessary address recommend vacuum yesterday reverse").split()
DAYS = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()


def to7(n):
    s = ""
    while n: s = str(n % 7) + s; n //= 7
    return s or "0"


def gen(n, seed=0):
    rng = random.Random(seed); items = []
    for i in range(n):
        a, b = rng.randint(10000, 99999), rng.randint(10000, 99999)
        items.append(("mult", f"What is {a} × {b}?", str(a * b)))
    for i in range(n):
        ws = [rng.choice(WORDS) for _ in range(rng.randint(8, 12))]; ch = rng.choice("eorsnatlc")
        text = " ".join(ws)
        items.append(("count", f'How many times does the letter "{ch}" occur in the following text?\n\n{text}',
                      str(text.count(ch))))
    for i in range(n):
        d = datetime.date(1800, 1, 1) + datetime.timedelta(days=rng.randint(0, 146000))
        items.append(("weekday", f"What day of the week was {d.strftime('%B')} {d.day}, {d.year}?", DAYS[d.weekday()]))
    for i in range(n):
        x = rng.randint(3000, 99999)
        items.append(("base7", f"Write {x} (base 10) in base 7.", to7(x)))
    return items


def parse(text, task):
    m = re.findall(r"Answer:\s*\**\s*([^\n]*)", text)
    if not m: return None
    s = m[-1].replace(",", "").replace("*", "").strip()
    if task == "weekday":
        w = re.findall(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", s, re.I)
        return w[0].capitalize() if w else None
    if task == "base7":  # drop a written base marker: 1234_7, 1234_{7}, 1234 (base 7)
        s = re.sub(r"_\{?7\}?$|\(7\)$|\(?base\s*7\)?", "", s).strip()
    w = re.findall(r"\d+", s.replace(" ", ""))
    return w[0] if w else None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--n", type=int, default=150)
    args = ap.parse_args()
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    mid = os.environ.get("MODEL_ID", "Qwen/Qwen3-8B")
    tok = AutoTokenizer.from_pretrained(mid)
    llm = LLM(model=mid, dtype="bfloat16", max_model_len=8192, gpu_memory_utilization=0.85, seed=0)
    here = os.path.dirname(os.path.abspath(__file__))
    skills = {t: open(f"{here}/skills/{t}.md").read() for t in ["mult", "count", "weekday", "base7"]}
    placebo = open(os.path.expanduser("~/mcq_math/skills/placebo_notation.md")).read()
    items = gen(args.n)
    suffix = "\n\nEnd your reply with a line of the form `Answer: <answer>`."
    def prompt(q, sys):
        msgs = ([{"role": "system", "content": sys}] if sys else []) + [{"role": "user", "content": q + suffix}]
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    out = {}
    for cond in ["baseline", "skill", "placebo"]:
        ps = [prompt(q, None if cond == "baseline" else skills[t] if cond == "skill" else placebo) for t, q, g in items]
        gens = [o.outputs[0].text for o in llm.generate(ps, SamplingParams(temperature=0, max_tokens=2048))]
        miss = [j for j, (o, it) in enumerate(zip(gens, items)) if parse(o, it[0]) is None]
        if miss:
            for j, o in zip(miss, llm.generate([ps[j] + gens[j] + "\n\nAnswer:" for j in miss], SamplingParams(temperature=0, max_tokens=24))):
                gens[j] += "\n\nAnswer:" + o.outputs[0].text.split("\n")[0]
        out[cond] = [{"task": t, "gold": g, "pred": parse(o, t), "ok": parse(o, t) == g, "len": len(o), "raw": o[-600:]}
                     for (t, q, g), o in zip(items, gens)]
        for t in ["mult", "count", "weekday", "base7"]:
            R = [r for r in out[cond] if r["task"] == t]
            print(f"{mid} {cond:9s} {t:8s} acc={100*sum(r['ok'] for r in R)/len(R):5.1f}  mean_len={sum(r['len'] for r in R)//len(R)}", flush=True)
    json.dump(out, open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
