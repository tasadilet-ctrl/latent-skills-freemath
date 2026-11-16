"""Install the rgym env (rgym_env/) into a SkillOpt checkout and register it in train.py / eval_only.py.
    python3 patch_rgym.py ~/skillopt_work/SkillOpt rgym_env      (idempotent)
"""
import os, shutil, sys
so, src = sys.argv[1], sys.argv[2]
env = os.path.join(so, "skillopt/envs/rgym")
os.makedirs(os.path.join(env, "skills"), exist_ok=True)
for f in ("dataloader.py", "rollout.py", "adapter.py"):
    shutil.copy(os.path.join(src, f), os.path.join(env, f))
open(os.path.join(env, "__init__.py"), "a").close()
shutil.copy(os.path.join(src, "initial.md"), os.path.join(env, "skills/initial.md"))
os.makedirs(os.path.join(so, "configs/rgym"), exist_ok=True)
shutil.copy(os.path.join(src, "default.yaml"), os.path.join(so, "configs/rgym/default.yaml"))
BLOCK = ("    try:\n        from skillopt.envs.rgym.adapter import RGymAdapter\n"
         "        _ENV_REGISTRY[\"rgym\"] = RGymAdapter\n    except ImportError:\n        pass\n")
ANCHOR = "    try:\n        from skillopt.envs.mcqkit"
for script in ("scripts/train.py", "scripts/eval_only.py"):
    p = os.path.join(so, script); s = open(p).read()
    if "envs.rgym" in s:
        continue
    assert s.count(ANCHOR) == 1, f"anchor not found in {script}"
    open(p, "w").write(s.replace(ANCHOR, BLOCK + ANCHOR))
print("rgym installed in", so)
