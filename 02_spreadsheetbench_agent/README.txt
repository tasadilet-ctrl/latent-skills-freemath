SpreadsheetBench -- the agent arm
================================================================================
400 real spreadsheet-editing tasks. The agent gets a shell, a file editor and
a workspace holding input.xlsx, and must leave output.xlsx behind. Grading
compares the task's answer range against the golden workbook.

Data and grader are validated: 394/394 golden-vs-golden, 0.3% init-vs-golden.

  run_baseline.sh              mechanics prompt only
  run_text_skill.sh            the same prompt with the skill appended
  run_embed_from_placebo.sh    B1, controlled   <vec> <layers> <gamma>
  run_embed_from_nothing.sh    B2, uncontrolled <vec> <layers> <gamma>
  run_control_placebo_only.sh  the null         <vec> <layers> <gamma>

NEEDS A SERVED MODEL
--------------------------------------------------------------------------------
Unlike the direct benchmarks, this one talks HTTP and loads no weights itself.
Start an endpoint first, in another terminal or another job:

    ../00_setup/05_serve_model.sh plain

and read the tool-call-parser warning in that file before trusting a number.
The wrong parser gives tool_calls: [] and a score of exactly 0% with no error.

THE EMBED CELLS ARE EXPENSIVE HERE
--------------------------------------------------------------------------------
The three embed arms need the residual stream, which vLLM does not expose, so
they run through the HOOKED server (../00_setup/05_serve_model.sh steered) --
plain HF transformers, serial, no batching. Measured: ~25 h for a 400-task
agent cell, against ~1 h for the same vector in
../03_spreadsheetbench_single_turn/.

If you want a SpreadsheetBench embedding number rather than specifically an
AGENTIC one, run the single-turn arm. It is a different row in the matrix, not
a worse version of this cell.

There is no --condition embed flag. The adapter asks the SERVER whether it is
steering and labels the cell from the answer, so an embed script is the
baseline command pointed at a steered server. The scripts call
require_steering, which refuses to run against a plain server -- otherwise the
cell would quietly come out as a second baseline.

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
