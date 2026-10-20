"""Rakhat's vector recipes (branch rakhat/step-vector-pilot), ported to LiveMath.

    MODEL_ID=Qwen/Qwen3-14B python src/rakhat_vectors.py --skill skills/livemath_ts.md
        -> vectors/v_<tag>_<stem>_replyA.pt, _replyB.pt, _stepA.pt, _stepB.pt

His recipes contrast the model's states while it WRITES a skill-style reply with
its states while it writes its own reply, on training questions. Ours (the kit's
extract_vectors.py) contrasts the last prompt token with and without the skill text.

  reply A  (record/pilot_qwen3-4b/pilot/hotpot_skill_dev/embed/behav_vec.py)
           mean over the reply tokens of h[question + skill reply]
           minus h[question + baseline reply]; no system prompt on either side.
  reply B  same, but the skill side also has the skill text as system prompt.
  step A/B (pilot/yesno_step/yesno_step.py, demo/make_step_vector.py)
           the same two contrasts read at ONE position, the `:` of the reply's
           final `Answer:` (the state that predicts the answer token).

Training questions: the 52 SkillOpt train+val items (skill_search/ids_skillopt_trainval.json),
which every LiveMath table here already leaves out of scoring. Replies come from
the vLLM runs (greedy, thinking off): baseline from results_vllm/full, skill from
results_vllm/ts. Step vectors use the pairs where both replies contain `Answer:`.
Rakhat also filtered pairs on a behaviour (skill one-word, baseline sentence) and
balanced yes/no; LiveMath has no such behaviour, and the answer letters vary,
so every pair is used.

Saved in the kit's vector format (one vector per layer) so evaluate.py can load them:
reply vectors with --condition embed, step vectors with --condition step.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import evaluate as E, qwen  # noqa: E402


def replies(folder, cond):
    out = {}
    for f in glob.glob(os.path.join(ROOT, "results_vllm", folder, f"livemath_{qwen.model_tag()}_{cond}_s*of*.json")):
        out.update({r["id"]: r["raw"] for r in json.load(open(f))["records"]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--base-folder", default="full")
    ap.add_argument("--skill-folder", default="ts")
    args = ap.parse_args()
    stem = os.path.basename(args.skill)[:-3]
    skill_text = open(args.skill).read()

    tv = set(json.load(open(os.path.join(ROOT, "skill_search", "ids_skillopt_trainval.json"))))
    rows = [r for r in E.load_domain("livemath", None) if r["id"] in tv]
    base, skl = replies(args.base_folder, "baseline"), replies(args.skill_folder, stem)
    rows = [r for r in rows if r["id"] in base and r["id"] in skl]
    assert rows, "no training replies found"

    tok, model, layers = qwen.load(device_map="auto")
    dev = qwen.first_param_device(model)
    n_layers = len(layers)
    ANS = {i for i in range(len(tok)) if tok.decode([i]).strip() == "Answer"}
    COLON = {i for i in range(len(tok)) if tok.decode([i]).strip() == ":"}
    sl, store = {}, {}

    def make(l):
        def fn(module, a, out):
            h = out[0] if isinstance(out, tuple) else out
            store[l] = (h[0, sl["s"]:sl["e"], :].float().mean(0).cpu(),     # reply span mean
                        h[0, sl["k"], :].float().cpu() if sl["k"] is not None else None)
        return fn
    handles = [layers[l].register_forward_hook(make(l)) for l in range(n_layers)]

    @torch.no_grad()
    def states(system, question, reply):
        p = tok(qwen.build_prompt(tok, question, system_msg=system), return_tensors="pt").input_ids
        y = tok(reply, return_tensors="pt", add_special_tokens=False).input_ids
        P, T, yl = p.shape[1], y.shape[1], y[0].tolist()
        ks = [j for j in range(1, T) if yl[j] in COLON and yl[j - 1] in ANS]
        # the states that PREDICT each reply token: last prompt token .. second-to-last reply token
        sl.update(s=P - 1, e=P + T - 1, k=P + ks[-1] if ks else None)
        model(input_ids=torch.cat([p, y], dim=1).to(dev))
        span = torch.stack([store[l][0] for l in range(n_layers)])
        step = torch.stack([store[l][1] for l in range(n_layers)]) if ks else None
        return span, step

    acc = {k: [] for k in ("neg", "A", "B")}
    step = {k: [] for k in ("neg", "A", "B")}
    for n, r in enumerate(rows, 1):
        q = E.render_question("livemath", r)
        trip = (states(None, q, base[r["id"]]), states(None, q, skl[r["id"]]),
                states(skill_text, q, skl[r["id"]]))
        for key, (span, st) in zip(("neg", "A", "B"), trip):
            acc[key].append(span)
        if all(st is not None for _, st in trip):
            for key, (_, st) in zip(("neg", "A", "B"), trip):
                step[key].append(st)
        print(f"[rakhat] {n}/{len(rows)}", flush=True)
    for h in handles:
        h.remove()

    cs = torch.nn.functional.cosine_similarity
    for kind, d in (("reply", acc), ("step", step)):
        d = {k: torch.stack(v) for k, v in d.items()}             # [n, n_layers, hidden]
        for side in ("A", "B"):
            diffs = d[side] - d["neg"]
            mean = diffs.mean(0)
            coh = cs(diffs, mean.unsqueeze(0).expand_as(diffs), dim=-1).mean(0)
            path = os.path.join(ROOT, "vectors", f"v_{qwen.model_tag()}_{stem}_{kind}{side}.pt")
            torch.save({"vectors": {l: mean[l].clone() for l in range(n_layers)},
                        "norm": mean.norm(dim=-1), "coherence": coh,
                        "hnorm": d["neg"].mean(0).norm(dim=-1),
                        "meta": {"pool": f"livemath_trainval_{kind}", "n": diffs.shape[0], "n_layers": n_layers,
                                 "skill": os.path.basename(args.skill), "model": qwen.MODEL_ID,
                                 "model_tag": qwen.model_tag(), "skill_position": "system",
                                 "baseline_skill": None,
                                 "recipe": f"Rakhat {kind} {side}: "
                                           + ("same prompt, reply differs" if side == "A"
                                              else "reply and skill context differ")}}, path)
            print(f"[rakhat] {os.path.basename(path)}  n={diffs.shape[0]}", flush=True)


if __name__ == "__main__":
    main()
