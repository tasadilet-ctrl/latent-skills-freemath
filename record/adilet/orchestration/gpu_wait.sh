# source me: wait up to 3 min for GPU1 to drop under 2 GB (a just-killed server releases memory slowly)
for i in $(seq 1 18); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 1); [ "$u" -le 2000 ] && break; sleep 10; done
echo "[gpuwait] GPU1 used=${u} MiB"
