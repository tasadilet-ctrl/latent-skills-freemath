#!/bin/bash
# Read each fidelity sweep, pick its operating point, and submit that embed cell.
#
# The point is chosen by FIDELITY -- how well steering reproduces the text
# skill's own token distribution -- not by benchmark accuracy, which on a 608
# item 5-way choice cannot separate "the vector works" from noise.
#
# Prints the top 5 configs per vector so the automatic pick can be overridden:
#   slurm/submit_embed.sh            # dry run, just show the table
#   slurm/submit_embed.sh --go       # actually sbatch
set -euo pipefail
source /shared/home/adil.taibassarov/latent-skills/env.sh
GO="${1:-}"

"$LS_PY" - "$GO" <<'PY'
import glob, json, os, subprocess, sys
ROOT = os.environ["LS_ROOT"]
go = sys.argv[1] == "--go"
MID = {"qwen3-8b": "Qwen/Qwen3-8B", "qwen3.6-27b": "Qwen/Qwen3.6-27B"}
BS  = {"qwen3-8b": "8", "qwen3.6-27b": "4"}

for path in sorted(glob.glob(f"{ROOT}/results/fidelity_v_*_livemath.json")):
    d = json.load(open(path))
    stem = os.path.basename(path)[len("fidelity_"):-len("_livemath.json")]
    tag = stem.split("_compare_claims_")[0][2:]          # v_<tag>_compare_claims_...
    rows = sorted(d["rows"], key=lambda r: -r["fidelity"])
    print(f"\n{stem}   floor KL(text||plain) = {d['floor_kl']:.4f}")
    for r in rows[:5]:
        print(f"    L{r['band']:<8} g{r['gamma']:<5} fidelity {r['fidelity']:+.3f}")
    best = rows[0]
    if best["fidelity"] <= 0:
        print(f"    !! best fidelity is {best['fidelity']:+.3f} <= 0 -- the vector "
              f"carries nothing. Submitting anyway would measure noise.")
        continue
    cmd = ["sbatch", "--parsable", f"{ROOT}/slurm/eval.sh", "livemath", "embed",
           f"vectors/{stem}.pt", best["band"], str(best["gamma"])]
    env = dict(os.environ, MODEL_ID=MID[tag], LIMIT="608", BS=BS[tag])
    print(f"    -> eval at L{best['band']} g{best['gamma']}"
          + ("" if go else "   (dry run; pass --go to submit)"))
    if go:
        jid = subprocess.run(cmd, env=env, capture_output=True, text=True,
                             check=True).stdout.strip()
        print(f"       submitted {jid}")
PY
