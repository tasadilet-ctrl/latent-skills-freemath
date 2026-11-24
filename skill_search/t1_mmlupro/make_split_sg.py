"""T2-style split for SuperGPQA math hard (2026-11-23): train 100 / val 150 / test 250.

Built from the pre-registered split (~/skillopt_work/mq_split/supergpqa_math_hard: train 40 / val 100 / test 360,
Oct 22) exactly as make_split_t2.py built MMLU-Pro T2: new train = old train + 60 old-test questions, new val = old
val + 50 old-test questions, the moved 110 = old-test ids with the smallest sha256(id). Fixed before any SkillOpt
result on this split. centroid_right stays on every item so the tables can report the centroid shortcut separately.
    python3 make_split_sg.py ~/skillopt_work/mq_split/supergpqa_math_hard ~/skillopt_work/mq_split/supergpqa_math_t2
"""
import hashlib, json, os, sys
src, dst = sys.argv[1], sys.argv[2]
old = {s: json.load(open(os.path.join(src, s, "items.json"))) for s in ("train", "val", "test")}
h = lambda it: hashlib.sha256(str(it["id"]).encode()).hexdigest()
moved = sorted(old["test"], key=h)[:110]
mids = {it["id"] for it in moved}
new = {"train": old["train"] + moved[:60], "val": old["val"] + moved[60:],
       "test": [it for it in old["test"] if it["id"] not in mids]}
assert [len(new[s]) for s in ("train", "val", "test")] == [100, 150, 250]
ids = [it["id"] for s in new for it in new[s]]
assert len(ids) == len(set(ids)) == 500
for s, items in new.items():
    os.makedirs(os.path.join(dst, s), exist_ok=True)
    json.dump(items, open(os.path.join(dst, s, "items.json"), "w"), ensure_ascii=False)
json.dump({s: [it["id"] for it in new[s]] for s in new}, open(os.path.join(dst, "ids.json"), "w"), indent=1)
print({s: len(v) for s, v in new.items()}, {s: sum(bool(it.get("centroid_right")) for it in v) for s, v in new.items()}, "->", dst)
