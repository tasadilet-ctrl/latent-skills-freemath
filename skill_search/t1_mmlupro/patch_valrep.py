"""Add an optional K-sample validation to the mcqkit env (SkillOpt checkout on the box).

With MCQKIT_VAL_REPEATS=K (default 1 = unchanged) every validation ("valid_seen") question is listed K times
with ids <id>#r0..#r<K-1>, so SkillOpt's acceptance score is the mean over K independent samples per question
(requests carry no seed, temperature 1.0). Train and test batches are untouched. Idempotent.
    python3 patch_valrep.py ~/skillopt_work/SkillOpt
"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / "skillopt/envs/mcqkit/dataloader.py"
s = p.read_text()
MARK = "# MCQKIT_VAL_REPEATS"
if MARK in s:
    print("already patched"); sys.exit(0)
old = """        items = self.get_split_items(split)
        if env_num and env_num < len(items):
            items = items[:env_num]
        items = self._materialize_batch(items, seed)
"""
new = """        items = self.get_split_items(split)
        if env_num and env_num < len(items):
            items = items[:env_num]
        items = self._materialize_batch(items, seed)
        # MCQKIT_VAL_REPEATS: K samples per validation question (acceptance score = mean over all K*n answers)
        import os as _os
        _k = int(_os.environ.get("MCQKIT_VAL_REPEATS", "1") or 1)
        if _k > 1 and split in ("valid_seen", "val", "valid", "selection"):
            items = [dict(it, id=f"{it['id']}#r{j}") for j in range(_k) for it in items]
            print(f"  [mcqkit] validation x{_k}: {len(items)} rollouts")
"""
assert s.count(old) == 1, "anchor not found"
p.write_text(s.replace(old, new))
print("patched", p)
