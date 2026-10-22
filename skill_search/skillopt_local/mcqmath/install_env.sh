#!/usr/bin/env bash
# Copy the mcqmath env into a SkillOpt checkout (@343db22) and register it.
#   ./install_env.sh [SkillOpt dir]      default: $SKILLOPT_WORK/SkillOpt
# Idempotent: re-running overwrites the env files and registers only once.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
S=${1:-${SKILLOPT_WORK:-$HOME/skillopt_work}/SkillOpt}
rm -rf "$S/skillopt/envs/mcqmath" && cp -r "$HERE/env" "$S/skillopt/envs/mcqmath"
mkdir -p "$S/configs/mcqmath" && cp "$HERE/configs/default.yaml" "$S/configs/mcqmath/default.yaml"
for f in scripts/train.py scripts/eval_only.py; do
  grep -q "envs.mcqmath.adapter" "$S/$f" && continue
  python3 - "$S/$f" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
anchor = "        from skillopt.envs.livemathematicianbench.adapter import LiveMathematicianBenchAdapter\n"
i = s.index(anchor)
# insert a sibling try/except block before the LiveMath one
j = s.rindex("    try:\n", 0, i)
block = ("    try:\n"
         "        from skillopt.envs.mcqmath.adapter import McqMathAdapter\n"
         "        _ENV_REGISTRY[\"mcqmath\"] = McqMathAdapter\n"
         "    except ImportError:\n"
         "        pass\n")
open(p, "w").write(s[:j] + block + s[j:])
PY
done
echo "mcqmath installed into $S"
