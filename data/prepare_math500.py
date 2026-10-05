"""MATH-500 -> flat jsonl. Fetched as JSON so no pyarrow/datasets needed."""
from __future__ import annotations
import json, os, urllib.parse, requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = "https://datasets-server.huggingface.co/rows"


def main():
    out, offset = [], 0
    while True:
        q = {"dataset": "HuggingFaceH4/MATH-500", "config": "default",
             "split": "test", "offset": offset, "length": 100}
        r = requests.get(f"{ROWS}?{urllib.parse.urlencode(q)}", timeout=120)
        r.raise_for_status()
        rows = r.json().get("rows", [])
        if not rows:
            break
        for x in rows:
            d = x["row"]
            out.append({"id": d["unique_id"], "question": d["problem"],
                        "answer": d["answer"], "subject": d.get("subject"),
                        "level": d.get("level")})
        offset += len(rows)
        print(f"  {offset}...", flush=True)
    p = os.path.join(HERE, "math500.jsonl")
    with open(p, "w") as f:
        for r_ in out:
            f.write(json.dumps(r_, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"wrote {len(out)} -> {p}")
    print("levels  :", dict(sorted(Counter(r['level'] for r in out).items())))
    print("subjects:", dict(Counter(r['subject'] for r in out).most_common(8)))


if __name__ == "__main__":
    main()
