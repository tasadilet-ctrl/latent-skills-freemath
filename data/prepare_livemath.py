"""LiveMathematicianBench -> flat jsonl with SHUFFLED options.

The raw files label the correct choice 'A' in all 608 questions -- the labels
encode canonical roles (A=correct, C=weaker-true, D=wildcard trap), not a
presentation order. Presenting them unshuffled makes "always answer A" a 100%
strategy, so options are shuffled with a per-question deterministic seed:
reproducible across runs and conditions, but not guessable.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
LETTERS = "ABCDE"


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(HERE, "lm_20*.json"))):
        for x in json.load(open(path)):
            m = x["mcq"]
            texts = [m["correct_choice"]["text"]] + [c["text"] for c in m["choices"]]
            qid = f"livemath-{x['month']}-{x['no']}"
            # Deterministic per-question shuffle: same order in every condition.
            seed = int(hashlib.sha256(qid.encode()).hexdigest()[:8], 16)
            order = list(range(len(texts)))
            random.Random(seed).shuffle(order)
            opts = [texts[i] for i in order]
            answer = LETTERS[order.index(0)]          # where the correct one landed
            rows.append({"id": qid, "month": x["month"],
                         "question": m["question"], "options": opts,
                         "answer": answer,
                         "theorem_type": x.get("theorem_type"),
                         "paper_link": x.get("paper_link")})

    rows.sort(key=lambda r: (r["month"], r["id"]))
    out = os.path.join(HERE, "livemath.jsonl")
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"wrote {len(rows)} -> {out}")
    print("answer distribution:", dict(sorted(Counter(r['answer'] for r in rows).items())))
    print("months:", dict(sorted(Counter(r['month'] for r in rows).items())))


if __name__ == "__main__":
    main()
