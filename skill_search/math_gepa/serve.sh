#!/bin/bash
# serve.sh <hf_model> <gpu> <port>: start a vLLM server on a GPU only if nobody else is using it
M=$1; G=$2; P=${3:-8100}
U=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $G)
if [ "$U" -gt 2048 ]; then echo "GPU $G busy ($U MiB), not starting"; exit 1; fi
export PATH=$HOME/skillopt_work/vllm_env/bin:$PATH CUDA_VISIBLE_DEVICES=$G
exec vllm serve $M --port $P --dtype bfloat16 --max-model-len 8192 --gpu-memory-utilization 0.85 --seed 0 --served-model-name target
