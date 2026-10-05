"""Download and normalise the two evaluation domains.

Source domain : GSM8K            (grade-school math word problems)
Target domain : HotpotQA distractor (multi-hop reading comprehension)

Both are fetched as plain JSON so the project needs no pyarrow/pandas/datasets
dependency -- it runs inside the existing vLLM venv untouched.
Run on the login node (compute nodes have no outbound network).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
GSM_BASE = ("https://raw.githubusercontent.com/openai/grade-school-math/"
            "master/grade_school_math/data")
ROWS_API = "https://datasets-server.huggingface.co/rows"


def _write(name, records):
    path = os.path.join(HERE, name)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  wrote {len(records):5d} -> {path}")


def gsm8k(split: str):
    url = f"{GSM_BASE}/{split}.jsonl"
    print(f"[gsm8k] {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    out = []
    for i, line in enumerate(resp.text.strip().split("\n")):
        d = json.loads(line)
        # GSM8K puts the gold answer after a '#### ' marker in the rationale.
        gold = d["answer"].split("####")[-1].strip().replace(",", "")
        out.append({"id": f"gsm8k-{split}-{i}", "question": d["question"],
                    "answer": gold, "rationale": d["answer"]})
    return out


def hotpotqa(n: int, split: str = "validation", config: str = "distractor"):
    out, offset, page = [], 0, 100
    while len(out) < n:
        params = {"dataset": "hotpotqa/hotpot_qa", "config": config,
                  "split": split, "offset": offset,
                  "length": min(page, n - len(out))}
        url = f"{ROWS_API}?{urllib.parse.urlencode(params)}"
        print(f"[hotpotqa] offset={offset}")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        rows = resp.json().get("rows", [])
        if not rows:
            break
        for r in rows:
            d = r["row"]
            ctx = d["context"]
            paras = [f"{t}: {''.join(s)}"
                     for t, s in zip(ctx["title"], ctx["sentences"])]
            out.append({"id": d["id"], "question": d["question"],
                        "answer": d["answer"], "level": d.get("level"),
                        "context": paras})
        offset += len(rows)
    return out[:n]


if __name__ == "__main__":
    n_hotpot = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    _write("gsm8k_train.jsonl", gsm8k("train"))
    _write("gsm8k_test.jsonl", gsm8k("test"))
    _write("hotpotqa_dev.jsonl", hotpotqa(n_hotpot))
    print("done")
