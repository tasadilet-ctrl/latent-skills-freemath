"""Re-score saved replies with the current env/evaluator.py, without re-running any model.

    python rescore_freemath.py [work dir] [model tag]

For every outputs/fm_<bench>_<tag>/{final_eval,final_eval_forced}/<condition>/results.jsonl,
re-applies evaluate(response, correct_answer) and writes results_rescored.jsonl beside it.
analyze_freemath.py reads the rescored file when it exists.

Why this exists: the first scorer did not strip \\( \\) / \\[ \\] delimiters (RealMath writes
gold answers that way) and did not compare right-hand sides of equations, so some
correct replies were scored 0. Scoring is a pure function of the saved reply and the
gold answer, so fixing it never needs new generations.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fm_evaluator", os.path.join(HERE, "env", "evaluator.py"))
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

W = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/skillopt_work")
TAG = sys.argv[2] if len(sys.argv) > 2 else "qwen3-8b"

for path in sorted(glob.glob(os.path.join(W, "outputs", f"fm_*_{TAG}", "final_eval*", "*", "results.jsonl"))):
    rows = [json.loads(line) for line in open(path)]
    changed = 0
    with open(path.replace("results.jsonl", "results_rescored.jsonl"), "w") as f:
        for r in rows:
            e = ev.evaluate(r.get("response", ""), r["correct_answer"])
            new = int(e["em"])
            changed += new != int(r.get("hard", 0))
            r.update(hard=new, soft=float(new), predicted_answer=e["predicted_answer"],
                     match_method=e["method"], hard_original=r.get("hard", 0))
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rel = os.path.relpath(path, os.path.join(W, "outputs"))
    print(f"{rel:70s} n={len(rows):3d}  changed={changed}")
