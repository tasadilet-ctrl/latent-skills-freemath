"""Check: baseline on val via the server path == saved runner dev cells (per item)."""
import json, sys, os, collections
sys.argv += []
import gepa_math as g
from transformers import AutoTokenizer
model, port = sys.argv[1], int(sys.argv[2])
tok = AutoTokenizer.from_pretrained(model); tag = model.split("/")[-1].lower()
for bench in ["mmlupro_math_tq_sb", "realmath"]:
    _, val = g.load(bench)
    ad = g.MathAdapter(bench, tok, port)
    res = ad.evaluate(val, {"skill": ""}, capture_traces=False)
    saved = json.load(open(os.path.expanduser(f"~/budget/results/{bench}_{tag}_baseline_dev.json")))
    em = {r["id"]: (r["em"] if bench in g.MCQ else g.ev.evaluate(r["raw"], r["gold"])["em"]) for r in saved["records"]}
    saved["summary"]["em"] = sum(em.values()) / len(em)
    agree = sum(em[r["id"]] == s for r, s in zip(val, res.scores))
    print(bench, "server", sum(res.scores)/len(val), "saved", saved["summary"]["em"], f"agree {agree}/{len(val)}", flush=True)
