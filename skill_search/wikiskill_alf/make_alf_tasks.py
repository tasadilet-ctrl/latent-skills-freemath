"""ALFWorld split -> WikiSkill tasks.json (2026-11-28).

    python make_alf_tasks.py <workspace dir> [--split <dir>] [--smoke N]

Split: SkillOpt's data/alfworld_path_split (train 39 / val 18 / test 134 = valid_unseen), the same split the
WikiSkill paper reports for ALFWorld. One task per game. The sandbox holds game.txt (the gamefile, relative to
$ALFWORLD_DATA); the inference agent (runner_alf.py) plays the game and writes result.txt = 1 if won, else 0.
Grader: exact match of result.txt against "1".
"""
import json
import os
import sys

ws = sys.argv[1]
split = os.path.expanduser(sys.argv[sys.argv.index("--split") + 1]) if "--split" in sys.argv else \
    os.path.expanduser("~/skillopt_work/SkillOpt/data/alfworld_path_split")
n = int(sys.argv[sys.argv.index("--smoke") + 1]) if "--smoke" in sys.argv else None
tasks = []
for s in ("train", "val", "test"):
    for it in json.load(open(os.path.join(split, s, "items.json")))[:n]:
        tasks.append({"id": f"alf-{it['id'].replace(':', '-')}", "split": s,
                      "title": f"ALFWorld {it['task_type']}",
                      "prompt": "Play the ALFWorld household game in game.txt to completion (up to 50 actions).",
                      "gamefile": it["gamefile"], "task_type": it["task_type"],
                      "sandbox": {"game.txt": it["gamefile"] + "\n"},
                      "grader": {"type": "exact", "file": "result.txt", "expected": "1"}})
os.makedirs(ws, exist_ok=True)
json.dump(tasks, open(os.path.join(ws, "tasks.json"), "w"), indent=1)
print(f"{len(tasks)} tasks -> {ws}/tasks.json", {s: sum(t["split"] == s for t in tasks) for s in ("train", "val", "test")})
