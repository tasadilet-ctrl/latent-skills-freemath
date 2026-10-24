#!/usr/bin/env bash
# Re-run run_ts_meta.sh until a pass has no failed cell (max 3). Finished cells are skipped by
# both runners (existing output file), so each pass only redoes cells that lost a GPU race.
L=$HOME/skillopt_work/logs/ts_meta.log
until grep -aq "^\[tsmeta\] ALL_DONE" $L; do sleep 120; done
for i in 1 2 3; do
  ~/mcq_math/run_ts_meta.sh > $HOME/skillopt_work/logs/ts_meta_retry$i.log 2>&1
  n=$(grep -ac "rc=[1-9]" $HOME/skillopt_work/logs/ts_meta_retry$i.log)
  echo "[retry] pass $i failed cells: $n"
  [ "$n" -eq 0 ] && break
done
echo "[retry] DONE"
