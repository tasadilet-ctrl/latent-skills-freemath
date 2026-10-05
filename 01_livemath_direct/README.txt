LiveMath -- the direct benchmark
================================================================================
608 research-level maths questions, 5-way multiple choice. Chance is 20%.
No agent, no tools: the model gets text, returns text, and the answer is
exact-matched. This is the cleanest of the three benchmarks and the one every
method decision was made on.

THE FIVE CELLS, and what each one is for
--------------------------------------------------------------------------------
  run_baseline.sh              no skill. The reference.
  run_text_skill.sh            the skill as system prompt. The thing to beat.
  run_embed_from_placebo.sh    B1: vector from [placebo+skill] - [placebo]
  run_embed_from_nothing.sh    B2: vector from [skill] - [nothing]
  run_control_placebo_only.sh  the null: a vector built FROM the placebo

Order: baseline and text first (they need no vectors). Then build vectors in
05_make_embedding_skills/, then the three embed cells.

WHAT THE COMPARISON IS ACTUALLY FOR
--------------------------------------------------------------------------------
B2 minus B1 is the study's point. B2's contrast contains the procedure AND the
bare fact that instructional text sits in the system slot; B1 cancels the
second by putting a length-matched placebo on both sides. If B2 moves the
score and B1 does not, then what activation steering transported was the
presence of instructions, not the procedure.

The CONTROL closes it: a vector built from placebo text alone has no procedure
in it at all. If that moves the score too, the case is settled.

Reporting B2 on its own as "the embedding skill works" is the single easiest
way to publish something untrue from this pipeline.

RUNNING THEM
--------------------------------------------------------------------------------
    source ../env.sh                 # optional; the scripts do it themselves
    ./run_baseline.sh
    ./run_text_skill.sh

Each writes one JSON per shard into ../results/. 06_reports/ merges them.

  MODEL_ID=Qwen/Qwen3-14B ./run_baseline.sh    switch model (tag follows)
  LIMIT=50 ./run_baseline.sh                   quick check
  RUNNER=local GPU=0,1 ./run_baseline.sh       no SLURM, two GPUs
  BS=4 ./run_baseline.sh                       lower if you run out of VRAM

CHECK BEFORE BELIEVING A NUMBER
--------------------------------------------------------------------------------
  n == 608          four shards x 152. If you see 456, a shard died.
  parse_rate 1.000  replies that committed to an answer.
  score > 20%       below chance means broken, not bad.

All three are explained in ../START_HERE.txt under "the three traps".
