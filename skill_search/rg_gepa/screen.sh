#!/bin/bash
# screen.sh <gpu>: baseline screen of candidate tasks on Qwen3-8B then Qwen3-14B
G=${1:-0}; cd ~/rg_gepa; mkdir -p screen
TASKS=base_conversion,binary_alternation,bitwise_arithmetic,calendar_arithmetic,count_bits,count_primes,cryptarithm,decimal_arithmetic,game_of_life,gcd,lcm,manipulate_matrix,number_sorting,polynomial_multiplication,pool_matrix,power_function,prime_factorization,products,rotate_matrix,spiral_matrix,shortest_path,spell_backward,string_insertion,string_manipulation,time_intervals,tower_of_hanoi,word_sorting,largest_island,rotten_oranges,isomorphic_strings,ransom_note,binary_matrix,caesar_cipher,family_relationships,letter_jumble,word_sequence_reversal
for M in Qwen/Qwen3-8B Qwen/Qwen3-14B; do
  tag=$(basename $M | tr A-Z a-z)
  bash serve.sh $M $G 8100 > screen/server_$tag.log 2>&1 & SP=$!
  until curl -sf localhost:8100/v1/models >/dev/null; do sleep 10; kill -0 $SP 2>/dev/null || { echo "server died"; exit 1; }; done
  ~/rg_env/bin/python rg_eval.py --tasks $TASKS --n 60 --seed 1 --out screen/$tag.jsonl > screen/$tag.txt 2>&1
  kill $SP; wait $SP 2>/dev/null; sleep 5
done
echo SCREEN_DONE
