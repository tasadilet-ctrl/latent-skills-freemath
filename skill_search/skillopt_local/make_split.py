"""Materialize SkillOpt's published LiveMath split (35/17/125) from our raw month files.

    cd <SkillOpt checkout @343db22> && .venv/bin/python <this file> <work dir>

Reads <work>/lm_raw/<month>/qa_<month>_final.json (copies of data/lm_<month>.json)
and SkillOpt's ID lists in data/livemathematicianbench_id_split/, writes
<work>/lm_split/{train,val,test}/items.json in SkillOpt's own item format.
SkillOpt's ratio mode at this commit gives 35/18/124, not the published 35/17/125,
so the ID lists are used instead.
"""
import json
import os
import sys

from skillopt.envs.livemathematicianbench.dataloader import load_items

work = os.path.abspath(sys.argv[1])
items = {i["id"]: i for i in load_items(os.path.join(work, "lm_raw"))}
for split in ("train", "val", "test"):
    ids = [x["id"] for x in json.load(open(f"data/livemathematicianbench_id_split/{split}/items.json"))]
    out = os.path.join(work, "lm_split", split)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "items.json"), "w", encoding="utf-8") as f:
        json.dump([items[i] for i in ids], f, ensure_ascii=False, indent=2)
    print(split, len(ids))
