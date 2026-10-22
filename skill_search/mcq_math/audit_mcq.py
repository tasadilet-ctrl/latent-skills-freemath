"""No-model audit of MCQ math benchmarks for answer-format shortcuts (PROTOCOL.md's two crutches)."""
import json, re, ast, difflib, urllib.request, urllib.parse, random
from collections import Counter

def filt(ds, where, split, cfg="default"):
    out, off = [], 0
    while True:
        u = ("https://datasets-server.huggingface.co/filter?" + urllib.parse.urlencode(
            {"dataset": ds, "config": cfg, "split": split, "where": where, "offset": off, "length": 100}))
        r = json.load(urllib.request.urlopen(u))["rows"]
        out += [x["row"] for x in r]
        if len(r) < 100: return out
        off += 100

META = re.compile(r"\b(all|none|both|neither) of (the )?(above|these|the (above|other|remaining) (options|answers|choices))|"
                  r"cannot be determined|not enough information|remaining options|stronger result", re.I)

def audit(name, items):
    n = len(items); k = Counter(len(it["opts"]) for it in items).most_common(1)[0][0]
    meta_q = [it for it in items if any(META.search(o) for o in it["opts"])]
    meta_right = sum(1 for it in meta_q if META.search(it["opts"][it["gold"]]))
    cen = lng = 0
    for it in items:
        o = it["opts"]
        sims = [sum(difflib.SequenceMatcher(None, a, b).ratio() for j, b in enumerate(o) if j != i) for i, a in enumerate(o)]
        cen += max(range(len(o)), key=sims.__getitem__) == it["gold"]
        lng += max(range(len(o)), key=lambda i: len(o[i])) == it["gold"]
    print(f"{name:28s} n={n:5d}  options={k}  chance={100/k:4.1f}%  "
          f"meta-option in {len(meta_q)} q (correct {meta_right}/{len(meta_q)})  "
          f"centroid={100*cen/n:4.1f}%  longest={100*lng/n:4.1f}%")
    return items

L = "ABCDEFGHIJ"
import pyarrow.parquet as pq
sg = [x for x in pq.read_table("sg.parquet").to_pylist() if x["field"] == "Mathematics"]
sgi = [{"opts": list(x["options"]), "gold": L.index(x["answer_letter"]), "diff": x["difficulty"], "sub": x["subfield"]} for x in sg]
audit("SuperGPQA math (all)", sgi)
for d in ("easy", "middle", "hard"):
    audit(f"  SuperGPQA math {d}", [i for i in sgi if i["diff"] == d])
mp = [x for x in pq.read_table("mp.parquet").to_pylist() if x["category"] == "math"]
mpi = [{"opts": list(x["options"]), "gold": x["answer_index"], "src": x["src"]} for x in mp]
audit("MMLU-Pro math (all)", mpi)
for s_, c in Counter(i["src"].split("-")[0] for i in mpi).most_common(5):
    audit(f"  MMLU-Pro math src={s_}", [i for i in mpi if i["src"].split("-")[0] == s_])
