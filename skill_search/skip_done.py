"""Drop task lines whose output already exists:  python skip_done.py tasks.txt > todo.txt

evaluate.py / evaluate_spreadsheet.py lines -> results/<name>_s{i}of{k}.json (their naming);
extract_vectors.py / anything with --out -> that path.
"""
import os
import re
import shlex
import sys

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
stem = lambda p: os.path.basename(p).rsplit(".", 1)[0]


def output(line):
    a = shlex.split(line)
    env = dict(x.split("=", 1) for x in a if re.match(r"^[A-Z_]+=", x))
    opt = {a[i][2:]: a[i + 1] for i in range(len(a) - 1) if a[i].startswith("--")}
    if "out" in opt:
        return opt["out"]
    script = next((x for x in a if x.endswith(".py")), "")
    if not script.endswith(("evaluate.py", "evaluate_spreadsheet.py")):
        return None
    m = env["MODEL_ID"].split("/")[-1].lower()
    dom = opt.get("domain", "spreadsheet")
    c = opt["condition"]
    name = opt.get("tag") or f"{dom}_{m}_{c}"
    if c == "text":
        name += "_" + stem(opt["skill"])
    if c == "embed":
        name += f"_{stem(opt['vectors'])}_L{opt['layers']}_g{float(opt['gamma'])}"
    if c == "step":
        name += f"_{stem(opt['vectors'])}_L{opt['layers']}_m{float(opt.get('strength', 1.5))}"
    i, k = opt.get("shard", "0/1").split("/")
    return os.path.join(K, "results", f"{name}_s{i}of{k}.json")


done = 0
for line in open(sys.argv[1]):
    o = output(line)
    if o and os.path.exists(o):
        done += 1
        continue
    sys.stdout.write(line)
print(f"[skip_done] {done} already done", file=sys.stderr)
