"""Re-score saved free-form replies with math_verify installed (the old envs lacked it, so only
string matches counted). Reads <in_dir>/*.json, writes the same files to <out_dir>; never overwrites inputs.
    python rescore_mv.py ~/budget/results ~/budget/results_mv"""
import importlib.util, json, glob, os, sys, collections
# import the kit evaluator under its real module name and put its folder on the path for child
# processes too: its process pool pickles functions by module name, and a module loaded under a
# made-up name cannot be found in the workers (every check then fails and counts as wrong)
_EVDIR = os.path.expanduser("~/skillopt_work/kit_v4/freemath/env")
sys.path.insert(0, _EVDIR); os.environ["PYTHONPATH"] = _EVDIR + os.pathsep + os.environ.get("PYTHONPATH", "")
import evaluator as ev
from concurrent.futures import ThreadPoolExecutor
_tp = ThreadPoolExecutor(1)
def score(text, gold):
    """Off the main thread, so the evaluator uses its process pool with a hard 20 s deadline
    (signal.alarm in the main thread cannot interrupt sympy stuck in C code)."""
    return _tp.submit(ev.evaluate, text, gold).result()
def main():
    src, dst = map(os.path.expanduser, sys.argv[1:3]); os.makedirs(dst, exist_ok=True)
    FM = ("beyondaime", "hardmath2", "realmath", "imoanswer", "arxivmath")
    pat = sys.argv[3] if len(sys.argv) > 3 else "*.json"
    for f in sorted(glob.glob(os.path.join(src, pat))):
        name = os.path.basename(f)
        if not name.startswith(FM): continue
        d = json.load(open(f)); old = d["summary"]["em"]; meth = collections.Counter()
        for r in d["records"]:
            e = score(r["raw"], r["gold"]); r["em_string_only"] = r["em"]
            r.update(em=e["em"], pred=e["predicted_answer"], method=e["method"]); meth[e["method"]] += 1
        n = len(d["records"]); d["summary"]["em"] = sum(r["em"] for r in d["records"]) / n
        d["summary"]["em_string_only"] = old; d["summary"]["scorer"] = "math_verify"
        json.dump(d, open(os.path.join(dst, name), "w"), indent=1)
        print(f"{name:60s} n={n:3d} {100*old:5.1f} -> {100*d['summary']['em']:5.1f}  {dict(meth)}", flush=True)


if __name__ == "__main__":   # pool workers re-import this file; they must not rescore
    main()
