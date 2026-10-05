OfficeQA -- the agent arm
================================================================================
239 scored questions over 285 US Treasury Bulletins (~146 MB of plain text).
The agent greps the files on disk and writes its answer to answer.txt.

  run_baseline.sh     mechanics prompt only
  run_text_skill.sh   the same prompt with the skill appended

NEEDS A SERVED MODEL:   ../00_setup/05_serve_model.sh plain

WHY IT MUST BE AN AGENT BENCHMARK
--------------------------------------------------------------------------------
The bulletins a single question references total ~215k tokens at the median,
534k at p90, 1.2M at worst. ZERO of the 246 questions fit an 8B or 14B context
and only 58% fit the 27B. Putting the documents in the prompt is not an option
that exists. Giving the agent the files and a shell is how the benchmark is
meant to be used, and it makes context length irrelevant.

TWO THINGS THAT KEEP IT HONEST
--------------------------------------------------------------------------------
* Only the files a question actually cites are linked into its workspace.
  Exposing all 285 would turn this into corpus search -- a different and much
  harder task than the benchmark scores.

* The answer is read off DISK, not parsed out of the conversation log. Parsing
  the event stream needed SDK internals and silently yielded nothing for
  239/239 questions on the first attempt. A file the agent writes is
  unambiguous.

DATA IS GATED
--------------------------------------------------------------------------------
databricks/officeqa is `gated: auto`. Someone must accept the terms on the
dataset page once, with the account whose HF_TOKEN is in the environment, or
the fetch 401s.

Four bulletins changed upstream after the manifest was written; the 7
questions grounded on them are excluded, leaving 239 of 246. `--include-tainted`
puts them back, for checking only.
