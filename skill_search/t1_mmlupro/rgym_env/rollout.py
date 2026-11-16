"""Reasoning Gym rollout, matching rg_gepa/rg_eval.py: system prompt = the skill alone, user = question +
'End your reply with the final answer inside <answer></answer> tags.', scored by Reasoning Gym's own
score_answer (correct iff 1.0). A reply with no <answer> tag gets one short forcing turn (the chat backend
cannot continue a turn, so the reply is quoted back). Temperature = model.target_qwen_chat_temperature.
"""
from __future__ import annotations

import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import reasoning_gym as rg

from skillopt.model import chat_target

SUFFIX = "\n\nEnd your reply with the final answer inside <answer></answer> tags."
ANS = re.compile(r"<answer>(.*?)</answer>", re.S)
FORCE_CUE = ("Your reply above stopped before giving a final answer. Based on the work so far, give only the "
             "final answer now, as <answer>...</answer>, and nothing else.")
_DS: dict = {}
_LOCK = threading.Lock()


def _dataset(task: str, size: int, seed: int):
    key = (task, size, seed)
    with _LOCK:
        if key not in _DS:
            _DS[key] = rg.create_dataset(task, size=size, seed=seed)
        return _DS[key]


def extract(text: str):
    m = ANS.findall(text or "")
    return m[-1].strip() if m else None


def score(item: dict, answer):
    if answer is None:
        return 0.0
    d = _dataset(item["task"], item["size"], item["seed"])
    try:
        return float(d.score_answer(answer, d[item["idx"]]))
    except Exception:  # noqa: BLE001
        return 0.0


def process_one(item: dict, out_root: str, skill_content: str, *, exec_timeout: int | None = 600,
                max_completion_tokens: int = 2048, **_) -> dict:
    item_id = str(item["id"])
    result = {"id": item_id, "question": item["question"], "task_type": item["task"], "hard": 0, "soft": 0.0,
              "predicted_answer": "", "correct_answer": item["answer"], "response": "", "fail_reason": "",
              "agent_ok": False, "n_turns": 0, "forced": False}
    try:
        pred_dir = os.path.join(out_root, "predictions", item_id)
        os.makedirs(pred_dir, exist_ok=True)
        system = (skill_content or "").strip()
        user = item["question"] + SUFFIX
        timeout = int(exec_timeout) if exec_timeout and int(exec_timeout) > 0 else None
        response, _ = chat_target(system=system, user=user, max_completion_tokens=max_completion_tokens,
                                  retries=5, stage="rollout", timeout=timeout)
        if extract(response) is None:
            follow = f"{user}\n\n## Your reply so far\n{response[-6000:]}\n\n{FORCE_CUE}"
            forced, _ = chat_target(system=system, user=follow, max_completion_tokens=96, retries=5,
                                    stage="rollout", timeout=timeout)
            response = f"{response}\n\n[forced]\n{forced}"
            result["forced"] = True
        pred = extract(response)
        s = score(item, pred)
        ok = s >= 1.0
        result.update(response=response, agent_ok=True, n_turns=1, hard=int(ok), soft=float(s),
                      predicted_answer=pred or "")
        if not ok:
            result["fail_reason"] = ("no <answer> tag" if pred is None else
                                     f"predicted {pred!r} but expected {item['answer']!r}")
        with open(os.path.join(pred_dir, "target_system_prompt.txt"), "w", encoding="utf-8") as f:
            f.write(system)
        with open(os.path.join(pred_dir, "target_user_prompt.txt"), "w", encoding="utf-8") as f:
            f.write(user)
        conversation = [
            {"type": "message", "turn": 1, "content": response},
            {"role": "system", "content": (
                "[EVALUATION RESULT]\n"
                f"Problem: {item['question']}\n"
                f"Predicted final answer: {pred!r}\n"
                f"Correct final answer: {item['answer']!r}\n"
                f"Exact Match: {ok}")},
        ]
        with open(os.path.join(pred_dir, "conversation.json"), "w", encoding="utf-8") as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
    except Exception as e:  # noqa: BLE001
        result["fail_reason"] = f"error: {type(e).__name__}: {e}"
    return result


def run_batch(items: list[dict], out_root: str, skill_content: str, *, exec_timeout: int | None = 600,
              workers: int = 64, max_completion_tokens: int = 2048, **_) -> list[dict]:
    os.makedirs(out_root, exist_ok=True)
    results_path = os.path.join(out_root, "results.jsonl")
    existing: list[dict] = []
    if os.path.exists(results_path):
        for line in open(results_path):
            try:
                existing.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    done = {str(r["id"]) for r in existing}
    pending = [it for it in items if str(it["id"]) not in done]
    results, correct = list(existing), sum(1 for r in existing if r.get("hard"))
    with open(results_path, "a") as outf, ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(process_one, it, out_root, skill_content, exec_timeout=exec_timeout,
                          max_completion_tokens=max_completion_tokens) for it in pending]
        for k, fut in enumerate(futs, 1):
            res = fut.result()
            results.append(res)
            correct += bool(res.get("hard"))
            print(f"    [rollout] {len(existing) + k}/{len(items)} (acc={correct / len(results):.3f}) "
                  f"id={res['id']} hard={res['hard']}", flush=True)
            outf.write(json.dumps(res, ensure_ascii=False) + "\n")
            outf.flush()
    return results
