#!/usr/bin/env bash
# Copy the freemath env into a SkillOpt checkout (@343db22) and register it.
#   ./install_env.sh [SkillOpt dir]      default: $SKILLOPT_WORK/SkillOpt
# Idempotent: re-running overwrites the env files and registers only once.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
S=${1:-${SKILLOPT_WORK:-$HOME/skillopt_work}/SkillOpt}
rm -rf "$S/skillopt/envs/freemath" && cp -r "$HERE/env" "$S/skillopt/envs/freemath"
mkdir -p "$S/configs/freemath" && cp "$HERE/configs/default.yaml" "$S/configs/freemath/default.yaml"
for f in scripts/train.py scripts/eval_only.py; do
  grep -q "envs.freemath.adapter" "$S/$f" && continue
  python3 - "$S/$f" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
anchor = "        from skillopt.envs.livemathematicianbench.adapter import LiveMathematicianBenchAdapter\n"
i = s.index(anchor)
# insert a sibling try/except block before the LiveMath one
j = s.rindex("    try:\n", 0, i)
block = ("    try:\n"
         "        from skillopt.envs.freemath.adapter import FreeMathAdapter\n"
         "        _ENV_REGISTRY[\"freemath\"] = FreeMathAdapter\n"
         "    except ImportError:\n"
         "        pass\n")
open(p, "w").write(s[:j] + block + s[j:])
PY
done
echo "freemath installed into $S"
