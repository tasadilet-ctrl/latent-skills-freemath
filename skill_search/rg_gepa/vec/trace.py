import json, re
pats = {"products": r"distributive", "decimal_arithmetic": r"significant digit|12 digits|full precision",
        "polynomial_multiplication": r"distribut|like terms", "word_sorting": r"ASCII|Unicode"}
for b, t in (("products","qwen3-8b"),("products","qwen3-14b"),("decimal_arithmetic","qwen3-14b"),("polynomial_multiplication","qwen3-8b"),("word_sorting","qwen3-8b")):
    row = []
    for c in ("baseline","placebo","text","B1","B2","CONTROL"):
        d = json.load(open(f"out/results/{b}_{t}_{c}_test.json"))["records"]
        row.append(f"{c}={sum(bool(re.search(pats[b], r['raw'], re.I)) for r in d)}")
    print(f"{b:26s} {t:9s} " + " ".join(row))
