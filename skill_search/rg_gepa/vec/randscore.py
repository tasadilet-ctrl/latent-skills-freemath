import json, re, os, reasoning_gym as rg
os.chdir(os.path.expanduser("~/rg_gepa/vec"))
CLEAN = [i for i in range(200) if not 1 <= i <= 70]
for b, t in (("decimal_arithmetic","qwen3-14b"),("products","qwen3-8b")):
    ds = rg.create_dataset(b, size=200, seed=0)
    for d in ("out","rand1","rand2"):
        ok = {}
        for r in json.load(open(f"{d}/results/{b}_{t}_B1_test.json"))["records"]:
            i = int(r["id"].rsplit("-",1)[1]); m = re.findall(r"<answer>(.*?)</answer>", r["raw"], re.S)
            try: ok[i] = bool(m) and ds.score_answer(m[-1].strip(), ds[i]) >= 1.0
            except Exception: ok[i] = False
        lab = "B1" if d == "out" else "random"
        print(f"{b:20s} {t} {d:6s} {lab:6s} all={100*sum(ok.values())/200:5.1f} clean={100*sum(ok[i] for i in CLEAN)/len(CLEAN):5.1f}")
