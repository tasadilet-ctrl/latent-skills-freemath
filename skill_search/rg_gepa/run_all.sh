#!/bin/bash
# GEPA on every task that passed the screen (10-60% baseline), 8B then 14B, GPU 0
cd ~/rg_gepa
T8=binary_alternation,cryptarithm,decimal_arithmetic,game_of_life,manipulate_matrix,polynomial_multiplication,pool_matrix,power_function,products,rotate_matrix,spiral_matrix,shortest_path,spell_backward,string_manipulation,time_intervals,tower_of_hanoi,word_sorting,largest_island,family_relationships
T14=binary_alternation,cryptarithm,decimal_arithmetic,manipulate_matrix,polynomial_multiplication,pool_matrix,power_function,products,rotate_matrix,spiral_matrix,shortest_path,spell_backward,string_manipulation,tower_of_hanoi,word_sorting,largest_island,family_relationships
bash run_gepa.sh 0 Qwen/Qwen3-8B 1200 $T8
bash run_gepa.sh 0 Qwen/Qwen3-14B 1200 $T14
echo ALL_DONE
