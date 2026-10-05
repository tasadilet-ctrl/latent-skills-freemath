# The experimental record

Everything above this directory is the *runnable* kit. This directory is the
*archive*: the actual outputs of the runs the project reports, kept so the
published numbers can be traced back to the files that produced them.

Nothing here is needed to run anything. Nothing here is overwritten by running
anything — the kit writes to the top-level `results/` and `vectors/`, which are
gitignored.

```
results/            201 JSON files — every reported cell, one per shard
vectors/            36 .pt steering vectors
tables/             the generated tables and the PNG
slurm/              the cluster launchers the runs actually used
legacy_openhands/   the pre-Strands agent adapters
```

---

## ⚠ This directory must not be made public as-is

The repository is private. If it is ever flipped to public, **`results/` has to be
scrubbed first.**

OfficeQA result records carry the real answer values:

```json
{"id": "UID0001", "gold": "2,602", "pred": "...", "em": 0.0}
```

`databricks/officeqa` is a **gated** dataset. A public `UID → correct value` map
for 239 questions reconstructs a usable part of its answer key, which both
breaches the terms the data was obtained under and contaminates the benchmark.

LiveMath and SpreadsheetBench records are safer — LiveMath stores only a shuffled
option letter (meaningless without the per-question shuffle seed) and
SpreadsheetBench stores `"golden"` plus a grader note. Neither contains question
text. OfficeQA is the one that matters.

See `../DATA.md` for the same reasoning applied to the datasets themselves.

---

## results/

One file per **shard**, named
`<domain>_<model-tag>_<condition>[_<skill>]_s<i>of<k>.json`. Four shards per cell
is the norm; `src/report.py` and `src/matrix.py` merge them.

Each file is `{"summary": {...}, "records": [...]}`. The summary carries the model,
condition, skill, vector (if steering), shard, and — for agent runs — the harness
and SDK version. The records are per-item scores.

**Reading these is how you check a cell is real.** `n` must equal the full
benchmark size (608 / 400 / 239); anything less means a shard died and the cell is
incomplete. `src/matrix.py` flags those with `!`.

Runs tagged `pilot` or `fixpilot` are excluded by the reporting scripts — they used
a different protocol and are kept only as provenance.

## vectors/

`v_<model-tag>_<skill>[_placebo][_<pool>][_n<N>].pt` — one tensor per layer.

Names ending `_placebo` were extracted against the length-matched placebo (the
**controlled** arm). Names without it were extracted against no system message (the
**uncontrolled** arm). A vector whose *source skill* is itself a placebo is the
CONTROL.

Eleven files still carry `compare_claims_v3` in their names. That skill file was
renamed to `compare_claims.md` on 2026-10-05; the vector names were deliberately
left alone, since renaming them would break every result that references them. The
text is identical — `src/report.py` aliases the two so they land in one row.

These are reproducible: extraction is deterministic given model, pool and skill
(`05_make_embedding_skills/01`–`03`). They are archived anyway because regenerating
them costs GPU time on a contended cluster.

## slurm/

The launchers the reported runs actually used — cluster-specific, with this
project's account, partition and node exclusions baked in. The kit's own runners
(`lib/common.sh` plus the per-cell scripts) are a generic rewrite of these that also
works without SLURM. Kept for provenance: if a published number is questioned, this
is the script that produced it.

## legacy_openhands/

`run_sb_agent.py` and `run_oqa_agent.py` as they were before the move to the
Strands SDK on 2026-10-05, verbatim.

Every SpreadsheetBench and OfficeQA cell in `results/` predating that date was
produced by these. The two harnesses do not expose identical tools, names or error
text, so their cells are not comparable and the reports keep them in separate rows
(`[openhands]` vs `[strands]`). See `../HARNESS_SWAP.txt`.
