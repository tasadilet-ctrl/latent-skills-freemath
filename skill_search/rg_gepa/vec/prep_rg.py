"""Dump Reasoning Gym items for the vector arm (run in ~/rg_env). Train/dev seeds are new; test = GEPA test (seed 0, n=200)."""
import json, os, reasoning_gym as rg
SPLITS = {"train": (21, 40), "dev": (22, 16), "test": (0, 200)}
os.makedirs("items", exist_ok=True)
for t in ("products", "polynomial_multiplication", "word_sorting", "decimal_arithmetic"):
    for s, (seed, n) in SPLITS.items():
        d = rg.create_dataset(t, size=n, seed=seed)
        json.dump([{"id": f"{t}-{s}-{i}", "question": d[i]["question"], "answer": str(d[i]["answer"]), "options": []}
                   for i in range(n)], open(f"items/{t}_{s}.json", "w"))
print("ok")
