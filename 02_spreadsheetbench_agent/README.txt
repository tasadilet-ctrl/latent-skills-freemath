SpreadsheetBench -- the agent arm
================================================================================
400 real spreadsheet-editing tasks. The agent gets a shell, a file editor and
a workspace holding input.xlsx, and must leave output.xlsx behind. Grading
compares the task's answer range against the golden workbook.

Data and grader are validated: 394/394 golden-vs-golden, 0.3% init-vs-golden.

  run_baseline.sh     mechanics prompt only
  run_text_skill.sh   the same prompt with the skill appended

NEEDS A SERVED MODEL
--------------------------------------------------------------------------------
Unlike the direct benchmarks, this one talks HTTP and loads no weights itself.
Start an endpoint first, in another terminal or another job:

    ../00_setup/05_serve_model.sh plain

and read the tool-call-parser warning in that file before trusting a number.
The wrong parser gives tool_calls: [] and a score of exactly 0% with no error.

WHY THERE IS NO EMBED CELL HERE
--------------------------------------------------------------------------------
The embedding arm needs the residual stream, which vLLM does not expose, so it
would have to run through the serial hooked server: ~25 h against ~1 h for the
single-turn arm next door. Use ../03_spreadsheetbench_single_turn/run_embed.sh
instead. It is a different row in the matrix, not a substitute cell.

WHY NO LOCATION HINT
--------------------------------------------------------------------------------
Official SpreadsheetBench does not tell the model the answer sheet and range --
that is grading metadata. Supplying it scored 85.9% on the first 85 tasks
against ~50% published SOTA: near-ceiling, where a 2-point skill effect cannot
register. Default is off. `--location-hint on` exists only to reproduce that
measurement.

HARNESS
--------------------------------------------------------------------------------
Strands SDK, since 2026-10-05 (was OpenHands). Not comparable across the swap
-- see ../HARNESS_SWAP.txt.
