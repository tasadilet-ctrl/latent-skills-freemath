"""Free-form math rollout: one chat turn, final answer in \\boxed{}.

Follows skillopt/envs/livemathematicianbench/rollout.py (chat backend path
only): same result fields, same predictions/<id>/conversation.json that the
inherited reflect() reads, same resumable results.jsonl.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

from skillopt.envs.freemath.evaluator import evaluate, extract_final
from skillopt.model import chat_target
from skillopt.prompts import load_prompt


def _build_system(skill_content: str) -> str:
    skill_section = f"## Skill\n{skill_content.strip()}\n\n" if skill_content.strip() else ""
    return load_prompt("rollout_system", env="freemath").format(skill_section=skill_section)


def _build_user(item: dict, diagnostic_mode: bool = False, diagnostic_instruction: str = "") -> str:
    parts = [f"## Problem\n{item['question']}"]
    if diagnostic_mode and diagnostic_instruction.strip():
        parts.append(f"## Training Readout\n{diagnostic_instruction.strip()}")
    return "\n\n".join(parts)


FORCE_CUE = ("Your reply above ran out of space before giving a final answer. "
             "Based on the reasoning so far, state your final answer now, as a single line "
             "`Answer: $\\boxed{<answer>}$`, and nothing else.")


def _force_answer(system: str, user: str, response: str, timeout: int | None) -> str:
    """The kit's forcing pass (src/evaluate.py `generate`), for a chat-only backend.

    A reply that hits the token cap mid-reasoning would score 0 however close it
    was, so accuracy would partly measure how wordy a skill makes the model. As in
    the kit, the model is asked once, with a short budget, to commit to the answer
    its reasoning was heading for. The chat API cannot continue a turn, so the
    truncated reply is quoted back (its last 6000 characters) instead.
    """
    tail = response[-6000:]
    follow = f"{user}\n\n## Your reply so far (truncated)\n{tail}\n\n{FORCE_CUE}"
    text, _ = chat_target(system=system, user=follow, max_completion_tokens=96,
                          retries=5, stage="rollout", timeout=timeout)
    return text


def process_one(item: dict, out_root: str, skill_content: str, *, exec_timeout: int | None = 600,
                max_completion_tokens: int = 4096, diagnostic_mode: bool = False,
                diagnostic_instruction: str = "", force_answer: bool = False) -> dict:
    item_id = str(item["id"])
    result = {"id": item_id, "question": item["question"], "task_type": item.get("task_type", "freemath"),
              "hard": 0, "soft": 0.0, "predicted_answer": "", "correct_answer": item["answer"],
              "response": "", "fail_reason": "", "agent_ok": False, "n_turns": 0, "match_method": "",
              "forced": False}
    try:
        pred_dir = os.path.join(out_root, "predictions", item_id)
        os.makedirs(pred_dir, exist_ok=True)
        system = _build_system(skill_content)
        user = _build_user(item, diagnostic_mode, diagnostic_instruction)
        timeout = int(exec_timeout) if exec_timeout and int(exec_timeout) > 0 else None
        response, _ = chat_target(system=system, user=user, max_completion_tokens=max_completion_tokens,
                                  retries=5, stage="rollout", timeout=timeout)
        if force_answer and extract_final(response) is None:
            forced_text = _force_answer(system, user, response, timeout)
            response = f"{response}\n\n[forced]\n{forced_text}"
            result["forced"] = True
        ev = evaluate(response, item["answer"])
        result.update(response=response, agent_ok=True, n_turns=1, hard=int(ev["em"]), soft=float(ev["em"]),
                      predicted_answer=ev["predicted_answer"], match_method=ev["method"])
        if not result["hard"]:
            result["fail_reason"] = (f"no final \\boxed{{}} answer" if ev["method"] == "no_final_answer" else
                                     f"predicted {ev['predicted_answer']!r} but expected {item['answer']!r}")
        with open(os.path.join(pred_dir, "target_system_prompt.txt"), "w", encoding="utf-8") as f:
            f.write(system)
        with open(os.path.join(pred_dir, "target_user_prompt.txt"), "w", encoding="utf-8") as f:
            f.write(user)
        conversation = [
            {"type": "message", "turn": 1, "content": response},
            {"role": "system", "content": (
                "[EVALUATION RESULT]\n"
                f"Problem: {item['question']}\n"
                f"Predicted final answer: {ev['predicted_answer']!r}\n"
                f"Correct final answer: {item['answer']!r}\n"
                f"Exact Match: {ev['em']}")},
        ]
        with open(os.path.join(pred_dir, "conversation.json"), "w", encoding="utf-8") as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
    except Exception as e:  # noqa: BLE001
        result["fail_reason"] = f"error: {type(e).__name__}: {e}"
    return result


def run_batch(items: list[dict], out_root: str, skill_content: str, *, exec_timeout: int | None = 600,
              workers: int = 64, max_completion_tokens: int = 4096, diagnostic_mode: bool = False,
              diagnostic_instruction: str = "", force_answer: bool = False, **_) -> list[dict]:
    os.makedirs(out_root, exist_ok=True)
    results_path = os.path.join(out_root, "results.jsonl")
    existing: list[dict] = []
    if os.path.exists(results_path):
        for line in open(results_path):
            try:
                existing.append(json.loads(line))
            except Exception:
                pass
    done = {str(r["id"]) for r in existing}
    pending = [it for it in items if str(it["id"]) not in done]
    results, correct = list(existing), sum(1 for r in existing if r.get("hard"))
    with open(results_path, "a") as outf, ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(process_one, it, out_root, skill_content, exec_timeout=exec_timeout,
                          max_completion_tokens=max_completion_tokens, diagnostic_mode=diagnostic_mode,
                          diagnostic_instruction=diagnostic_instruction, force_answer=force_answer)
                for it in pending]
        for k, fut in enumerate(futs, 1):
            res = fut.result()
            results.append(res)
            correct += bool(res.get("hard"))
            print(f"    [rollout] {len(existing) + k}/{len(items)} (acc={correct / len(results):.3f}) "
                  f"id={res['id']} hard={res['hard']}", flush=True)
            outf.write(json.dumps(res, ensure_ascii=False) + "\n")
            outf.flush()
    return results
