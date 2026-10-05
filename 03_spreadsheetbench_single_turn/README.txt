SpreadsheetBench -- the single-turn arm
================================================================================
The same 400 tasks, but the model sees a rendering of the workbook and emits
the edit in ONE turn. No tools, no iteration, runs in-process with batching.

  run_baseline.sh     no skill
  run_text_skill.sh   skill as system prompt
  run_embed.sh        steering vector

NO SERVED MODEL NEEDED -- this arm loads weights itself.

WHY IT EXISTS
--------------------------------------------------------------------------------
To make the embedding arm affordable. Steering needs the residual stream, so
through the agent harness it would run on the serial hooked server at roughly
25 h per cell. Here it is batched in-process: about 1 h.

IT IS A SEPARATE ROW, NOT A CHEAPER VERSION
--------------------------------------------------------------------------------
Single-turn is a strictly weaker task than the agent arm -- no shell, no
chance to look at the file and correct itself. Its scores are lower and they
are NOT comparable to the agent rows. The reports keep them apart
("single-turn" vs the harness name). Compare conditions within a row.
