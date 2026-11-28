"""WikiSkill on ALFWorld: Adil's runner.py (wiki_skill branch, wikiskill/runner.py) plus an `alf` inference domain.

    python runner_alf.py <workspace> --iters 8                  # evolve (repo's harness.evolve, unchanged)
    python runner_alf.py <workspace> --eval <skills.md|none> --out <dir> [--split test]   # test a skill file

Everything except inference is Adil's runner: the repo's evolution loop (train rollouts, <=5 fail / <=3 pass
trace sample, Wiki Maintainer, Skill Proposer, strict validation gate, git rollback of skills), his tool loop
for the maintainer and proposer on OPT, his chat() (no temperature sent: the model's generation_config), his
thinking switch (target off unless TARGET_THINKING=1; optimizer on with OPT_THINKING=1).

Inference (`alf`): one ALFWorld game per task, played with SkillOpt's ALFWorld code (build_alfworld_env +
run_alfworld_batch: SkillOpt's prompt with the last 2 observations/actions, admissible actions,
<think>/<action> format, up to 50 actions). All active SKILL.md files are injected where SkillOpt injects its
skill (the paper's full-injection setting, as runner.py does for LiveMath and SpreadsheetBench). The game's
SkillOpt chat call is redirected to TARGET via runner.chat. The trace given to the maintainer is the
episode: the prompt the agent saw at each step (without the skill section) and its full reply.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

WK = os.path.expanduser(os.environ.get("WK_DIR", "~/wikiskill_adil/wikiskill"))
sys.path.insert(0, WK)
import runner as R  # noqa: E402  Adil's runner (also puts the patched repo on sys.path)
from wikiskill import gating, harness, tasks as T  # noqa: E402

sys.path.insert(0, R.SKILLOPT)
os.environ.setdefault("ALFWORLD_DATA", os.path.expanduser("~/.cache/alfworld"))
MAX_STEPS = 50
MAX_TOKENS = 16384   # SkillOpt's ALFWorld max_completion_tokens


def skills_text(ws):
    f = os.environ.get("WK_SKILL_FILE", "")
    if f:   # --eval: a fixed skill file ("none" = no skill)
        return "" if f == "none" else open(f, encoding="utf-8").read().strip()
    return R.active_skills_text(ws)


def _chat_target(system, user, max_completion_tokens=MAX_TOKENS, **_):
    url, model = os.environ["TARGET_URL"], os.environ["TARGET_MODEL"]
    think = os.environ.get("TARGET_THINKING", "0") == "1"
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    m = R.chat(url, model, msgs, thinking=think, max_tokens=R.ctx_room(url, model, msgs, want=max_completion_tokens))
    text = m.content or ""
    rc = getattr(m, "reasoning_content", None) or getattr(m, "reasoning", None)
    if rc and "<think>" not in text:   # thinking on: vLLM's reasoning parser splits it off; SkillOpt reads <think>
        text = f"<think>{rc}</think>{text}"
    return text, None


def alf_infer(ws, task, sandbox, run_dir):
    from skillopt.envs.alfworld import rollout as A
    A.chat_target = _chat_target
    gf = task["gamefile"]
    dataset = "eval_in_distribution" if "/valid_seen/" in gf else \
        "eval_out_of_distribution" if "/valid_unseen/" in gf else "train"
    skill = skills_text(ws)
    env = A.build_alfworld_env(env_num=1, eval_dataset=dataset, seed=42, is_train=dataset == "train",
                               specific_gamefiles=[gf])
    out = os.path.join(sandbox, "rollout")
    try:
        res = A.run_alfworld_batch(env, skill_content=skill, max_steps=MAX_STEPS, out_root=out, max_api_workers=1,
                                   max_completion_tokens=MAX_TOKENS, result_ids=[task["id"]])[0]
    finally:
        close = getattr(env, "close", None)
        if callable(close):
            close()
    with open(os.path.join(sandbox, "result.txt"), "w") as f:
        f.write("1" if res["hard"] else "0")
    conv = json.load(open(os.path.join(out, "predictions", task["id"], "conversation.json")))
    msgs = [{"role": "system", "content": "You are an expert agent operating in the ALFRED Embodied Environment."
             + (f"\n\n[{len(skill)} characters of active skills were injected into every step's prompt]" if skill else "")},
            {"role": "user", "content": f"Task: {res['task_description']} (task type {res['task_type']})"}]
    for s in conv:
        msgs.append({"role": "assistant", "content": s["model_response"]})
        msgs.append({"role": "user", "content": f"[step {s['step']} observation] {s['env_feedback']}"})
    msgs.append({"role": "system", "content": f"RESULT: {'SUCCESS' if res['hard'] else 'FAILURE'} after "
                                              f"{res['n_turns']} actions. {res['fail_reason']}".strip()})
    return msgs


R.INFER["alf"] = alf_infer


def evaluate(ws, skill_file, out, split):
    """Score a fixed skill file on a split with the same inference agent (test cells of the table)."""
    os.environ["WK_SKILL_FILE"] = skill_file
    runner = R.make_runner("alf")
    todo = T.splits(ws)[split]
    res = gating.run_many(ws, todo, 99, runner=runner, overwrite=True)
    os.makedirs(out, exist_ok=True)
    rows = [{"id": r["id"], "task_type": r["task_type"], "score": r["score"]} for r in res]
    with open(os.path.join(out, "results.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    summ = {"skill": skill_file, "split": split, "n": len(rows), "target": os.environ["TARGET_MODEL"],
            "acc": round(100 * sum(r["score"] or 0 for r in rows) / len(rows), 1)}
    json.dump(summ, open(os.path.join(out, "summary.json"), "w"), indent=1)
    print("eval", summ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ws")
    ap.add_argument("--iters", type=int, default=8)
    ap.add_argument("--eval", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--split", default="test")
    a = ap.parse_args()
    ws = os.path.abspath(a.ws)
    if a.eval:
        return evaluate(ws, a.eval, a.out, a.split)
    state = harness.evolve(ws, iters=a.iters, runner=R.make_runner("alf"), verbose=True)
    print(f"done: baseline={state.get('baseline')} r_best={state.get('r_best')}")


if __name__ == "__main__":
    main()
