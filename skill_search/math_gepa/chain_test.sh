#!/bin/bash
# Wait for an idle GPU (< 2 GB used), then: finish 14B hardmath2 GEPA (resumes), test both models, report.
cd ~/math_gepa
pick() { while true; do
  while IFS=, read -r i u; do [ "${u// /}" -le 2000 ] && { G=${i// /}; return; }; done < <(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits)
  echo "waiting for an idle GPU $(date +%H:%M)"; sleep 300; done; }
pick; echo "GPU $G $(date)"
[ -s gepa/qwen3-14b/hardmath2/skill.md ] || bash run_gepa.sh $G Qwen/Qwen3-14B 1200 8101 > run_14b_hm2.log 2>&1
pick; bash test_skills.sh $G Qwen/Qwen3-8B > test_8b.log 2>&1
pick; bash test_skills.sh $G Qwen/Qwen3-14B > test_14b.log 2>&1
~/rg_env/bin/python analyze.py > report_test.txt 2>&1
echo CHAIN_DONE
