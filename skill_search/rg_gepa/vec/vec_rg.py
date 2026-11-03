"""Vector arm on the GEPA skills (Reasoning Gym). vec_mcq.py's design unchanged (B1 = skill - placebo,
B2 = skill - nothing, CONTROL = placebo - nothing; diff-in-means at the last prompt token over 40
train items; h += 0.3*||h||*v_hat at 8B L34 / 14B L37; all cells on the HF engine). Prompt = the
GEPA test prompt (question + <answer> suffix). `em` here is only a placeholder: rescore_rg.py
scores replies with Reasoning Gym's checker.

    python vec_rg.py extract|fidelity|eval --bench <task> [...]   (MODEL_ID picks the model's skill)
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/posctl/code/vector_mcq"))
import vec_mcq as V  # noqa: E402

SUFFIX = "\n\nEnd your reply with the final answer inside <answer></answer> tags."
CUE = "\n\n<answer>"

def rows_for(bench, split):
    return json.load(open(os.path.join(HERE, "items", f"{bench}_{split}.json")))

def parse(pred, k):
    m = re.findall(r"<answer>(.*?)(?:</answer>|$)", pred or "", re.S)
    m = [x.strip() for x in m if x.strip()]
    return m[-1] if m and "</answer>" in (pred or "")[(pred or "").rfind("<answer>"):] else None

def generate(torch, tok, model, prompts, max_new, bs, k):
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    outs = [None] * len(prompts)
    for i, o in zip(order, V._decode(torch, tok, model, [prompts[i] for i in order], max_new, bs)):
        outs[i] = o
    idx = [i for i, o in enumerate(outs) if parse(o, k) is None]
    if idx:  # forced answer, 200 tokens (polynomials / word lists need more than vec_mcq's 12)
        cont = V._decode(torch, tok, model, [prompts[i] + outs[i] + CUE for i in idx], 200, max(1, bs // 4))
        for j, i in enumerate(idx):
            c = cont[j]; c = c[:c.find("</answer>")] if "</answer>" in c else c
            outs[i] += CUE + c + "</answer>"
    return outs, set(idx)

V.rows_for, V.render, V.parse, V.generate, V.ANSWER_CUE = rows_for, (lambda r: r["question"] + SUFFIX), parse, generate, CUE

if __name__ == "__main__":
    b = sys.argv[sys.argv.index("--bench") + 1]
    tag = os.environ["MODEL_ID"].split("/")[-1].lower()
    V.SKILL = os.path.expanduser(f"~/rg_gepa/gepa/{tag}/{b}/skill.md")
    V.PLACEBO = os.path.expanduser("~/rg_gepa/placebo_notation.md")
    sys.argv[0] = "vec_mcq.py"
    ns = vars(V)
    main = open(V.__file__).read().split('if __name__ == "__main__":', 1)[1]
    exec(compile("import argparse, os\n" + __import__("textwrap").dedent(main), V.__file__, "exec"), ns)
