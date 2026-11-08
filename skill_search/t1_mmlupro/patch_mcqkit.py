"""Patch the copied mcqkit env so rollouts use the kit runner's prompt, forcing and parser."""
import os

D = os.path.expanduser("~/skillopt_work/SkillOpt/skillopt/envs/mcqkit")
p = os.path.join(D, "rollout.py")
s = open(p).read()

HEAD = '''"""MCQ math rollout with the kit runner's prompt (mcq_math/evaluate_vllm_mcq.py), byte for byte.

System = the skill alone (no system message when empty), user = question + lettered options +
"End your reply with a line of the form `Answer: <letter>`", the model's chat template with thinking
off, sent to the vLLM completions endpoint; a reply with no committed letter gets the runner's
"\\n\\nAnswer:" cue (12 tokens). Scored with the runner's format-neutral parser. Temperature = the
target's configured temperature (model.target_qwen_chat_temperature). Options are not shuffled
(env.shuffle_choices=false), so the letters are the runner's.
"""'''
first = s.index('"""', 0)
end = s.index('"""', first + 3) + 3
s = HEAD + s[end:]

HELPERS = r'''from skillopt.envs.mcqkit.evaluator import evaluate as _evaluate_tags  # noqa: F401 (exec path only)
import re as _re
import threading as _threading

# imported here, in the main thread: transformers' lazy import is not thread-safe, and importing it
# inside 64 rollout threads at once failed ("cannot import name AutoTokenizer") and scored those items wrong
from openai import OpenAI
from transformers import AutoTokenizer
from skillopt.model import qwen_backend as qb

_LETTERS = "ABCDEFGHIJ"
_ANSWER_CUE = "\n\nAnswer:"
_lock = _threading.Lock()
_tok_cache: dict = {}
_cli_cache: dict = {}


def _kit_render(item: dict) -> str:
    opts = "\n".join(f"{_LETTERS[i]}. {c['text']}" for i, c in enumerate(item["choices"]))
    return (f"{item['question']}\n\n{opts}\n\nEnd your reply with a line of the form "
            f"`Answer: <letter>` giving the single best choice.")


def _kit_parse(pred: str, k: int):
    valid = _LETTERS[:k]
    commits = _re.findall(
        rf"(?:Answer:\s*(?:<(?:answer|letter)>)?|<(?:answer|letter)>)\s*\**\(?([{valid}])\b(?!\w)", pred, _re.I)
    if commits:
        return commits[-1].upper()
    for line in reversed([l.strip() for l in pred.strip().split("\n") if l.strip()]):
        m = _re.fullmatch(rf"\**\(?([{valid}])\)?\.?\**", line, _re.I)
        return m.group(1).upper() if m else None
    return None


def evaluate(prediction_text: str, correct_choice: dict, choices: list[dict]) -> dict:
    """Same fields as the tag evaluator, scored with the kit parser."""
    lab = _kit_parse(prediction_text, len(choices))
    gold = str(correct_choice.get("label", "")).strip().upper()
    em = float(lab == gold)
    txt = next((str(c.get("text", "")).strip() for c in choices if c.get("label") == lab), "")
    return {"em": em, "f1": em, "sub_em": em, "predicted_answer": lab or "", "predicted_label": lab or "",
            "predicted_text": txt, "correct_label": gold, "correct_text": str(correct_choice.get("text", "")).strip()}


def _target():
    cfg = qb.TARGET_CONFIG
    with _lock:
        if cfg.deployment not in _tok_cache:
            _tok_cache[cfg.deployment] = AutoTokenizer.from_pretrained(cfg.deployment)
        if cfg.base_url not in _cli_cache:
            _cli_cache[cfg.base_url] = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key or "x", timeout=3600)
    temp = 0.0 if cfg.temperature is None else float(cfg.temperature)
    return _tok_cache[cfg.deployment], _cli_cache[cfg.base_url], cfg.deployment, temp


def _kit_generate(skill: str, user: str, max_tokens: int, k: int):
    """One reply exactly as the kit runner makes it; returns (reply, forced)."""
    tok, cli, model, temp = _target()
    msgs = ([{"role": "system", "content": skill}] if skill.strip() else []) + [{"role": "user", "content": user}]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    text = cli.completions.create(model=model, prompt=prompt, temperature=temp, top_p=1.0,
                                  max_tokens=max_tokens).choices[0].text
    if _kit_parse(text, k) is not None:
        return text, False
    c = cli.completions.create(model=model, prompt=prompt + text + _ANSWER_CUE, temperature=temp, top_p=1.0,
                               max_tokens=12).choices[0].text
    return text + _ANSWER_CUE + c, True
'''
s = s.replace("from skillopt.envs.mcqkit.evaluator import evaluate\n", HELPERS, 1)
assert "_kit_generate" in s

a = s.index("        system = _build_system(skill_content)\n        user = _build_user(")
stop = '            if "<answer>" in resp_text.lower():\n                break\n'
b = s.index(stop, a) + len(stop)
NEW = '''        system = skill_content
        user = _kit_render(item)
        if diagnostic_trace_context.strip():
            user += "\\n\\n## Previous attempt (partial)\\n" + diagnostic_trace_context.strip()
        if diagnostic_mode and diagnostic_instruction.strip():
            user += "\\n\\n## Training Readout\\n" + diagnostic_instruction.strip()
        response, forced = _kit_generate(system, user, max_completion_tokens, len(item["choices"]))
        result["forced"] = forced
        conversation: list[dict] = [{"type": "message", "turn": 1, "content": response}]
'''
s = s[:a] + NEW + s[b:]
open(p, "w").write(s)

# config: no option shuffling, runner's token budget
cfgdir = os.path.expanduser("~/skillopt_work/SkillOpt/configs/mcqkit")
os.makedirs(cfgdir, exist_ok=True)
c = open(os.path.expanduser("~/skillopt_work/SkillOpt/configs/mcqmath/default.yaml")).read()
c = c.replace("name: mcqmath", "name: mcqkit").replace("skillopt/envs/mcqmath/", "skillopt/envs/mcqkit/")
c = c.replace("max_completion_tokens: 4096", "max_completion_tokens: 2048").replace("shuffle_choices: true", "shuffle_choices: false")
open(os.path.join(cfgdir, "default.yaml"), "w").write(c)

# register in train.py and eval_only.py next to mcqmath
for f in ("scripts/train.py", "scripts/eval_only.py"):
    fp = os.path.expanduser(f"~/skillopt_work/SkillOpt/{f}")
    t = open(fp).read()
    if "mcqkit" in t:
        continue
    old = ('        from skillopt.envs.mcqmath.adapter import McqMathAdapter\n'
           '        _ENV_REGISTRY["mcqmath"] = McqMathAdapter\n    except ImportError:\n        pass\n')
    assert old in t, f
    t = t.replace(old, old + old.replace("mcqmath", "mcqkit").replace("    try:", "").join(["    try:\n", ""]), 1)
    open(fp, "w").write(t)
print("ok")
