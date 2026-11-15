"""Bigger train/val split for MMLU-Pro math (Adil, 2026-11-15): train 100 / val 150 / test 255.

New train = old train 40 + 60 old-test questions; new val = old val 100 + 50 old-test questions; new test =
the other 255 old-test questions, so the new test is a subset of the old one. The 110 moved questions are the
old-test ids with the smallest sha256(id), fixed before any result on this split exists.
    python3 make_split_t2.py ~/skillopt_work/mq_split/mmlupro_math_tq_sb ~/skillopt_work/mq_split/mmlupro_math_t2
"""
import hashlib, json, os, sys
src, dst = sys.argv[1], sys.argv[2]
old = {s: json.load(open(os.path.join(src, s, "items.json"))) for s in ("train", "val", "test")}
h = lambda it: hashlib.sha256(str(it["id"]).encode()).hexdigest()
moved = sorted(old["test"], key=h)[:110]
mids = {it["id"] for it in moved}
new = {"train": old["train"] + moved[:60], "val": old["val"] + moved[60:],
       "test": [it for it in old["test"] if it["id"] not in mids]}
assert [len(new[s]) for s in ("train", "val", "test")] == [100, 150, 255]
ids = [it["id"] for s in new for it in new[s]]
assert len(ids) == len(set(ids)) == 505
for s, items in new.items():
    os.makedirs(os.path.join(dst, s), exist_ok=True)
    json.dump(items, open(os.path.join(dst, s, "items.json"), "w"), ensure_ascii=False)
json.dump({s: [it["id"] for it in new[s]] for s in new}, open(os.path.join(dst, "ids.json"), "w"), indent=1)
print({s: len(v) for s, v in new.items()}, "->", dst)
