"""Train/val/test splits for BeyondAIME, HARDMath2, RealMath (and ArxivMath), in the freemath env's format.

    python make_split_freemath.py <work dir>
      -> <work>/fm_split/<bench>/{train,val,test}/items.json
      -> ids_freemath.json next to this file (ids only; commit this, not the data)

Splits are a deterministic hash of the item id, so re-running gives the same
split. Val is large on purpose: SkillOpt's gate compares val scores, and with
LiveMath's 17 val questions one question was 6 points (README section 9).

Filters (applied before splitting, decided before any model was run):
  RealMath   Math_arXiv only; drop multi-part / case-split answers and answers
             of 120+ characters, which the automatic checker cannot score
             reliably (the RealMath paper uses an LLM judge instead).
  HARDMath2  all items; graded numerically (see env/evaluator.py).
  BeyondAIME all items (integer answers).
  IMO-AnswerBench  single-expression answers only: drop answers listing several
             solutions (commas, \\cup, \\ldots), which the checker cannot score as sets.
  ArxivMath  all items. Split but not in the default run: Qwen3-8B (thinking
             off) scored 0/16 on its val split in the smoke run, so the gate
             had nothing to compare. Use it with a stronger target.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request

SIZES = {"beyondaime": (30, 30), "hardmath2": (40, 50), "realmath": (40, 60), "arxivmath": (30, 30),
         "imoanswer": (40, 100)}   # (train, val); rest = test
IMO_MULTI = re.compile(r",|\\cup|\\ldots|\\cdots|\\text")
MULTI = re.compile(r"\(a\)|\(b\)|\\begin\{cases\}|\\text\{\s*if|otherwise|\\\\", re.I)


def rows(ds: str, split: str, cfg: str = "default") -> list[dict]:
    out, off = [], 0
    while True:
        u = (f"https://datasets-server.huggingface.co/rows?dataset={ds}"
             f"&config={cfg}&split={split}&offset={off}&length=100")
        r = json.load(urllib.request.urlopen(u))["rows"]
        out += [x["row"] for x in r]
        if len(r) < 100:
            return out
        off += 100


def load() -> dict[str, list[dict]]:
    arx = [{"id": f"arxivmath-{x['competition'].split('/')[-1]}-{x['problem_idx']}",
            "question": x["problem"], "answer": str(x["answer"]),
            "task_type": x["competition"].split("/")[-1], "benchmark": "arxivmath"}
           for x in rows("MathArena/arxivmath", "train")]
    # HARDMath2's `index` repeats across problem types, so the id is type + index,
    # with the prompt hash as a tie-break for any remaining repeat
    hm = [{"id": f"hardmath2-{x['type']}-{x['index']}-{hashlib.sha256(x['prompt'].encode()).hexdigest()[:6]}",
           "question": x["prompt"], "answer": x["solution"],
           "task_type": x["type"], "benchmark": "hardmath2"}
          for x in rows("JVRoggeveen/HARDMath2", "train")]
    rm = []
    for x in rows("ethz-spylab/RealMath", "Math_arXiv"):
        a = x["answer"].strip()
        if MULTI.search(a) or len(a) >= 120:
            continue
        aid = re.search(r"abs/([\d.]+v?\d*)", x["link"]).group(1)
        rm.append({"id": f"realmath-{aid}-{hashlib.sha256(x['question'].encode()).hexdigest()[:8]}",
                   "question": x["question"], "answer": a,
                   "task_type": "20" + aid[:2], "benchmark": "realmath"})
    bey = [{"id": f"beyondaime-{i}", "question": x["problem"], "answer": str(x["answer"]),
            "task_type": "beyondaime", "benchmark": "beyondaime"}
           for i, x in enumerate(rows("ByteDance-Seed/BeyondAIME", "test"))]
    imo = [{"id": x["Problem ID"], "question": x["Problem"], "answer": x["Short Answer"].strip(),
            "task_type": x["Category"], "benchmark": "imoanswer"}
           for x in rows("Hwilner/imo-answerbench", "train") if not IMO_MULTI.search(x["Short Answer"])]
    return {"beyondaime": bey, "hardmath2": hm, "realmath": rm, "arxivmath": arx, "imoanswer": imo}


def split(items: list[dict], n_train: int, n_val: int) -> dict[str, list[dict]]:
    order = sorted(items, key=lambda it: hashlib.sha256(it["id"].encode()).hexdigest())
    return {"train": order[:n_train], "val": order[n_train:n_train + n_val],
            "test": order[n_train + n_val:]}


def main() -> None:
    work = os.path.abspath(sys.argv[1])
    manifest = {}
    for bench, items in load().items():
        ids = [it["id"] for it in items]
        assert len(ids) == len(set(ids)), f"duplicate ids in {bench}"
        parts = split(items, *SIZES[bench])
        manifest[bench] = {k: [it["id"] for it in v] for k, v in parts.items()}
        for k, v in parts.items():
            d = os.path.join(work, "fm_split", bench, k)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "items.json"), "w", encoding="utf-8") as f:
                json.dump(v, f, ensure_ascii=False, indent=1)
        print(bench, {k: len(v) for k, v in parts.items()})
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ids_freemath.json"), "w") as f:
        json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    main()
