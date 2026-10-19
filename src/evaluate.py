"""The 4-quadrant benchmark runner.

Conditions (the rows of the matrix):
  baseline        no skill text, no injection            -- the control
  text            skill markdown as the system message   -- the text-skill arm
  embed           no skill text; h_l <- h_l + gamma*v    -- the embedding arm

Domains (the columns):
  gsm8k           source / intended domain
  hotpotqa        out-of-domain target

baseline and embed use byte-identical prompts, so any difference between them
is attributable to the vector alone.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import string
import sys
import time
from collections import Counter

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import hooks, qwen  # noqa: E402
from src.run_oqa_agent import BAD_FILES, grade as grade_officeqa  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GSM_SUFFIX = "\n\nEnd your reply with a line of the form `Answer: <number>`."
HOTPOT_SUFFIX = ("\n\nAnswer using a short span copied from the passages. "
                 "End your reply with a line of the form `Answer: <span>`.")
LIVEMATH_SUFFIX = ("\n\nEnd your reply with a line of the form "
                   "`Answer: <letter>` giving the single best choice.")
LETTERS = "ABCDE"
OFFICEQA_SUFFIX = ("\n\nEnd your reply with a line of the form `Answer: <value>`. For numeric "
                   "answers give a bare number: no units, no thousands separators, no currency symbol.")
MATH500_SUFFIX = ("\n\nEnd your reply with a line of the form `Answer: $\\boxed{<answer>}$` "
                  "containing the final answer only.")


# ---------------------------------------------------------------- data ------

def load_domain(name: str, limit: int | None):
    path = {"gsm8k": "data/gsm8k_test.jsonl",
            "hotpotqa": "data/hotpotqa_dev.jsonl",
            "livemath": "data/livemath.jsonl",
            "math500": "data/math500.jsonl",
            "officeqa": "data/officeqa_oracle.jsonl"}[name]
    rows = []
    with open(os.path.join(ROOT, path)) as f:
        for line in f:
            r = json.loads(line)
            # OfficeQA: drop the questions on bulletins that changed upstream (as the
            # agent arm does) and the one whose cited page has no parsed text
            if name == "officeqa" and (BAD_FILES & set(r["source_files"]) or not r["context"]):
                continue
            rows.append(r)
            if limit and len(rows) >= limit:
                break
    return rows


def render_question(domain: str, row: dict) -> str:
    if domain == "gsm8k":
        return row["question"] + GSM_SUFFIX
    if domain == "math500":
        return row["question"] + MATH500_SUFFIX
    if domain == "livemath":
        opts = "\n".join(f"{LETTERS[i]}. {t}" for i, t in enumerate(row["options"]))
        return f"{row['question']}\n\n{opts}" + LIVEMATH_SUFFIX
    if domain == "officeqa":
        return (f"The following pages are from US Treasury Bulletins.\n\n{row['context']}"
                f"\n\nQuestion: {row['question']}" + OFFICEQA_SUFFIX)
    passages = "\n\n".join(row["context"])
    return f"{passages}\n\nQuestion: {row['question']}" + HOTPOT_SUFFIX


# ------------------------------------------------------------- scoring ------

def _norm(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def extract_answer(text: str) -> str:
    m = re.findall(r"Answer:\s*(.+)", text)
    return m[-1].strip() if m else text.strip().split("\n")[-1].strip()


def score_gsm8k(pred: str, gold: str) -> float:
    nums = re.findall(r"-?\d[\d,]*\.?\d*", extract_answer(pred).replace(",", ""))
    if not nums:
        return 0.0
    try:
        return float(abs(float(nums[-1]) - float(gold)) < 1e-4)
    except ValueError:
        return 0.0


_TEX_JUNK = [r"\\left", r"\\right", r"\\!", r"\\,", r"\\;", r"\\ ",
             r"\\text\{([^}]*)\}", r"\\mbox\{([^}]*)\}"]


def norm_math(s: str) -> str:
    """Light LaTeX normalisation before comparison."""
    s = s.strip().strip("$").strip()
    s = re.sub(r"^\\boxed\{(.*)\}$", r"\1", s.strip())
    for pat in _TEX_JUNK:
        s = re.sub(pat, r"\1" if "(" in pat else "", s)
    s = s.replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")
    s = s.replace("\\%", "").replace("%", "").replace("\\$", "")
    s = re.sub(r"\s+", "", s)
    return s.rstrip(".")


def _boxed(text: str) -> str | None:
    """Extract the last \\boxed{...}, matching braces properly."""
    i = text.rfind("\\boxed{")
    if i < 0:
        return None
    j, depth = i + 7, 1
    while j < len(text) and depth:
        depth += (text[j] == "{") - (text[j] == "}")
        j += 1
    return text[i + 7:j - 1] if depth == 0 else None


def score_math500(pred: str, gold: str) -> float:
    a = _boxed(pred)
    if a is None:
        line = extract_answer(pred)
        a = _boxed(line) or line
    pa, pg = norm_math(a), norm_math(gold)
    if pa == pg:
        return 1.0
    try:                                    # numeric equality: 0.5 vs 1/2
        if abs(float(pa) - float(pg)) < 1e-6:
            return 1.0
    except (ValueError, TypeError):
        pass
    try:                                    # symbolic equality via sympy
        from sympy.parsing.latex import parse_latex
        if parse_latex(pa).equals(parse_latex(pg)):
            return 1.0
    except Exception:
        pass
    return 0.0


def parse_livemath(pred: str) -> str | None:
    """Extract the chosen letter, or None if the model never committed to one.

    Deliberately strict. An earlier version fell back to "last A-E anywhere in
    the reply", which on a page of LaTeX picks up incidental capitals and turned
    a 99% truncation failure into a plausible-looking 19.6% -- indistinguishable
    from a real at-chance result. Unparseable must stay visible, not become noise.
    """
    m = re.findall(r"Answer:\s*\**\(?([A-E])\b", pred, re.I)
    if m:
        return m[-1].upper()
    # a final line that is just the letter, optionally bolded/parenthesised
    for line in reversed([l.strip() for l in pred.strip().split("\n") if l.strip()]):
        m = re.fullmatch(r"\**\(?([A-E])\)?\.?\**", line, re.I)
        if m:
            return m.group(1).upper()
        break
    return None


def score_livemath(pred: str, gold: str) -> float:
    got = parse_livemath(pred)
    return 0.0 if got is None else float(got == gold)


def has_answer(domain: str):
    """Predicate: did this reply actually commit to an answer?

    Deliberately as strict as the scorer -- a reply that only the lenient
    fallback can read is one the forcing pass should be given a chance to fix.
    """
    if domain == "livemath":
        return lambda t: parse_livemath(t) is not None
    if domain == "math500":
        return lambda t: _boxed(t) is not None
    return lambda t: bool(re.search(r"Answer:\s*\S", t))


def score_hotpot(pred: str, gold: str) -> tuple[float, float]:
    p, g = _norm(extract_answer(pred)), _norm(gold)
    em = float(p == g)
    pt, gt = p.split(), g.split()
    common = Counter(pt) & Counter(gt)
    n = sum(common.values())
    if n == 0:
        return em, 0.0
    prec, rec = n / len(pt), n / len(gt)
    return em, 2 * prec * rec / (prec + rec)


# ---------------------------------------------------------- generation ------

@torch.no_grad()
def _decode(tok, model, prompts, max_new_tokens, batch_size):
    outs = []
    dev = qwen.first_param_device(model)
    for i in range(0, len(prompts), batch_size):
        outs.extend(_decode_chunk(tok, model, prompts[i:i + batch_size], max_new_tokens, dev))
    return outs


def _decode_chunk(tok, model, chunk, max_new_tokens, dev):
    # long OfficeQA pages (up to ~20k tokens) can OOM a batch; halve it and retry
    try:
        enc = tok(chunk, return_tensors="pt", padding=True,
                  padding_side="left").to(dev)
        gen = model.generate(**enc, max_new_tokens=max_new_tokens,
                             do_sample=False, temperature=None, top_p=None,
                             top_k=None, pad_token_id=tok.pad_token_id or tok.eos_token_id)
    except torch.OutOfMemoryError:
        if len(chunk) == 1:
            raise
        enc = gen = None
        torch.cuda.empty_cache()
        h = len(chunk) // 2
        print(f"[oom] batch {len(chunk)} -> {h}", flush=True)
        return (_decode_chunk(tok, model, chunk[:h], max_new_tokens, dev)
                + _decode_chunk(tok, model, chunk[h:], max_new_tokens, dev))
    new = gen[:, enc["input_ids"].shape[1]:]
    return tok.batch_decode(new, skip_special_tokens=True)


ANSWER_CUE = "\n\nAnswer:"


@torch.no_grad()
def generate(tok, model, prompts, max_new_tokens, batch_size,
             has_answer=None, cue_tokens: int = 12):
    """Generate, then force a decision out of any reply that never committed.

    Qwen3.6-27B on LiveMath spends its whole budget re-checking itself -- 29.4%
    of replies hit the 4096-token cap mid-deliberation, with half the lexical
    diversity of the replies that finish. Scoring those as wrong is not merely
    noisy, it is BIASED: truncation rate tracks verbosity, skills change
    verbosity, so accuracy would partly measure how wordy a condition makes the
    model rather than how correct it is.

    So the assistant turn is continued with an `Answer:` cue and a few tokens,
    which converts "ran out of room" into the decision the reasoning had
    already been circling. Applied identically in every condition, and the
    count is reported as `forced` so the rate stays visible.
    """
    outs = _decode(tok, model, prompts, max_new_tokens, batch_size)
    forced = 0
    if has_answer is not None:
        idx = [i for i, o in enumerate(outs) if not has_answer(o)]
        if idx:
            forced = len(idx)
            cont = _decode(tok, model,
                           [prompts[i] + outs[i] + ANSWER_CUE for i in idx],
                           cue_tokens, batch_size)
            for k, i in enumerate(idx):
                outs[i] = outs[i] + ANSWER_CUE + cont[k]
    return outs, forced


def parse_layers(spec: str, n_layers: int) -> list[int]:
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    bad = [l for l in out if not 0 <= l < n_layers]
    if bad:
        raise ValueError(f"layers out of range 0..{n_layers-1}: {bad}")
    return out


# --------------------------------------------------------------- main ------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=["gsm8k", "hotpotqa", "livemath", "math500", "officeqa"], required=True)
    ap.add_argument("--condition", choices=["baseline", "text", "embed"], required=True)
    ap.add_argument("--vectors", default=None, help="path to a .pt from extract_vectors.py")
    ap.add_argument("--layers", default="24-40", help="e.g. '32' or '24-40' or '20,30,40'")
    ap.add_argument("--gamma", type=float, default=0.1)
    ap.add_argument("--mode", default="relative", choices=["relative", "raw"])
    ap.add_argument("--skill", default=os.path.join(ROOT, "skills", "decompose_verify.md"))
    ap.add_argument("--skill-position", default="system", choices=["system", "user"],
                    help="see extract_vectors.py -- 'user' keeps every arm free "
                         "of a system message so prompt-presence cannot confound")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=None)
    ap.add_argument("--shard", default="0/1", help="i/k -- take every k-th row starting at i")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    if args.condition == "embed" and not args.vectors:
        ap.error("--condition embed requires --vectors")

    rows = load_domain(args.domain, args.limit)
    i, k = (int(x) for x in args.shard.split("/"))
    rows = rows[i::k]
    if args.domain == "officeqa":
        # contexts range from 1k to 20k tokens; batching similar lengths together
        # cuts padding (and memory) a lot. Records are keyed by id, so order is free.
        rows.sort(key=lambda r: len(r["context"]))
    max_new = args.max_new_tokens or {"gsm8k": 384, "hotpotqa": 128,
                                      "livemath": 2048,
                                      "math500": 1024, "officeqa": 2048}[args.domain]

    tok, model, layers = qwen.load(device_map="auto")
    skill_txt = open(args.skill).read() if args.condition == "text" else None
    if args.skill_position == "user":
        prompts = [qwen.build_prompt(
            tok, (f"{skill_txt}\n\n---\n\n{render_question(args.domain, r)}"
                  if skill_txt else render_question(args.domain, r)),
            system_msg=None) for r in rows]
    else:
        prompts = [qwen.build_prompt(tok, render_question(args.domain, r),
                                     system_msg=skill_txt) for r in rows]

    ctx = None
    vec_meta = {}
    if args.condition == "embed":
        blob = torch.load(args.vectors, map_location="cpu")
        chosen = parse_layers(args.layers, blob["meta"]["n_layers"])
        vecs = {l: blob["vectors"][l] for l in chosen}
        vec_meta = {"file": os.path.basename(args.vectors), "pool": blob["meta"]["pool"],
                    "layers": chosen, "gamma": args.gamma, "mode": args.mode}
        ctx = hooks.inject(layers, vecs, gamma=args.gamma, mode=args.mode)

    t0 = time.time()
    ha = has_answer(args.domain)
    if ctx is not None:
        # The forcing pass runs INSIDE the steering context, so the continuation
        # is steered exactly as the reply it continues.
        with ctx:
            preds, forced = generate(tok, model, prompts, max_new,
                                     args.batch_size, has_answer=ha)
    else:
        preds, forced = generate(tok, model, prompts, max_new,
                                 args.batch_size, has_answer=ha)
    dt = time.time() - t0

    records, em_sum, f1_sum = [], 0.0, 0.0
    for r, p in zip(rows, preds):
        if args.domain == "gsm8k":
            em = score_gsm8k(p, r["answer"]); f1 = em
        elif args.domain == "livemath":
            em = score_livemath(p, r["answer"]); f1 = em
        elif args.domain == "math500":
            em = score_math500(p, r["answer"]); f1 = em
        elif args.domain == "officeqa":
            em, _ = grade_officeqa(p, r["answer"], r.get("tolerance")); f1 = em
        else:
            em, f1 = score_hotpot(p, r["answer"])
        em_sum += em; f1_sum += f1
        records.append({"id": r["id"], "gold": r["answer"],
                        "pred": extract_answer(p), "em": em, "f1": f1,
                        "raw": p})

    n = len(records)
    n_parsed = sum(parse_livemath(x["raw"]) is not None for x in records) \
        if args.domain == "livemath" else n
    summary = {"domain": args.domain, "condition": args.condition, "n": n,
               "model": qwen.MODEL_ID, "model_tag": qwen.model_tag(),
               "skill": os.path.basename(args.skill) if args.condition == "text" else None,
               "skill_position": args.skill_position,
               "mean_prompt_tokens": sum(len(tok(x)["input_ids"]) for x in prompts) / len(prompts),
               "em": em_sum / n, "f1": f1_sum / n, "seconds": round(dt, 1),
               "mean_pred_chars": sum(len(x["raw"]) for x in records) / n,
               "parse_rate": n_parsed / n,
               "forced": forced, "forced_rate": forced / n,
               "max_new_tokens": max_new,
               "vector": vec_meta, "shard": args.shard}

    name = args.tag or f"{args.domain}_{qwen.model_tag()}_{args.condition}"
    if args.condition == "text":
        name += "_" + os.path.basename(args.skill).replace(".md", "")
        if args.skill_position == "user":
            name += "_usr"
    if args.condition == "embed":
        name += ("_" + os.path.basename(args.vectors).replace(".pt", "")
                 + f"_L{args.layers}_g{args.gamma}")
    name += f"_s{i}of{k}"
    out = os.path.join(ROOT, "results", f"{name}.json")
    with open(out, "w") as f:
        json.dump({"summary": summary, "records": records}, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"[eval] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
