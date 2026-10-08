# Design notes for the skill files  (NOT model-visible)

These notes used to sit at the top of the .md skill files themselves, which meant
they were rendered into the system prompt and read by the model. That is a
contamination bug: it told the model about the experiment it was part of, and the
placebo went further and stated that it "carries no procedural content".
Everything in `skills/*.md` is model-visible text. Rationale lives here.

## decompose_verify.md
Written the way an automatic skill miner (EvoSkill / Trace2Skill style) would
produce it from successful GSM8K traces: the procedure is general, but the
wording and examples carry source-domain vocabulary. That baggage is what the
text arm drags into the out-of-domain evaluation, which is the effect under test.

## placebo_matched.md
A length- and register-matched control: same shape (headed sections, numbered
imperatives, similar token count) but no procedural content. Contrasting against
this rather than against no system message removes "a long system prompt is
present" from the extracted direction. Measured: at layer 0, ||v|| falls from
0.484 (vs nothing) to 0.142 (vs placebo) -- 71% of the shallow signal was
prompt-presence, not skill.

## compare_claims.md
The text skill for LiveMath (LiveMathematicianBench): 608 research-level maths
questions, each a 5-way choice over statements derived from a recent paper. The
distractor roles the source data encodes are weaker-but-true, plausible-but-false
and an off-topic trap, so the discriminating procedure is quantifier bookkeeping
and strength ordering, not arithmetic -- which is why `decompose_verify.md` is
the wrong skill here and a new one was written.

Kept to 7 numbered imperatives at ~260 words so it stays close to
`placebo_matched.md` (~228 words). The residual length gap is what the placebo
contrast cannot remove; it is smaller than the gap to no system message at all,
which is the comparison the two extraction arms make.

## compare_claims_v2.md
Revision after measuring v1 on the full 608. v1 scored 24.18% against a 25.99%
baseline (McNemar p=0.41 -- indistinguishable, not a real drop), but the error
profile showed it was not inert. Mapping every answer back to the distractor
role the source data labels (`weaker_true_label`, `wildcard_false_label`,
`template_used`):

                        baseline   v1
    correct               26.0%   24.2%
    wildcard (off-topic)  21.4%   21.5%
    weaker-but-true       18.3%   11.8%   <- v1's step 4 worked
    stronger-trap         14.3%   15.6%
    scope errors          12.8%   18.8%   <- and leaked to here

So v1 bought a real 6.5-point cut in the weaker-true trap and spent all of it
on over-claims and scope errors: it taught "prefer the stronger statement" with
no symmetric brake. v2 keeps the strength step but (a) puts a relevance screen
first, since a fifth of all answers go to an off-topic wildcard that v1 never
addressed, (b) makes scope auditing concrete rather than a clause inside
another step, and (c) states that over-claiming is false rather than strong.
The blanket "restate every candidate" step is gone: compliance with it was 100%
against a 10% baseline rate and it bought nothing.

NOTE on method: v2 was written after seeing v1's error profile on the same 608
items it is then scored on. That is test-set-informed, and the honest report
says so. Only the aggregate role histogram was used, never per-item labels, and
`report.py` also prints the late-month subset.

## compare_claims_v3.md
v2 scored 24.01% against v1's 24.18% and a 25.99% baseline -- no movement. The
role histogram shows why, and it is not that the skills are inert:

    role              base    v1     v2
    correct           26.0   24.2   24.0
    wildcard          21.4   21.5   17.4   <- v2's relevance screen worked
    weaker_true       18.3   11.8   20.7   <- and gave back v1's gain
    stronger_trap     14.3   15.6   14.5

Each version fixes one trap and reopens another while accuracy stays flat. The
mechanism is visible in v2's compliance: "reject over-claims" appears in 87% of
replies and competes with "prefer the strongest" for the same decision. Given
two preferences the model over-applies whichever is more salient, so v1
over-preferred strength and v2 under-preferred it.

v3 therefore replaces the competing pair with ONE criterion -- can the
candidate be derived from the hypotheses -- and makes strength ordering a
strictly downstream tiebreak among derivable candidates only. It keeps v2's
relevance screen, which is the one intervention that bought something without
costing something else.

If v3 also lands at ~24%, the honest reading is that on LiveMath this model has
a roughly fixed error budget that prompt-level procedure redistributes across
trap types without reducing. That is a reportable null, and it is measured
rather than asserted: three skills, three distinct compliance profiles, one
unchanged accuracy.

## compare_claims.md -- VERSION HISTORY AND A NAME COLLISION TO KNOW ABOUT

Consolidated to a single file on 2026-10-05. `compare_claims.md` now holds
what was previously `compare_claims_v3.md` -- "Derive First, Then Take the
Strongest That Survives". The two superseded drafts were deleted:

  v1  "Identify the Claim, Compare the Candidates, Eliminate"
      Scored ~24% on LiveMath against a 26.15% baseline -- i.e. it hurt.
      Its failure is informative: it ranked candidates by strength before
      checking derivability, so it reliably chose the strongest statement
      the hypotheses did not support.

  v2  "Screen for Relevance, Audit the Scope, Then Rank"
      Used as an ablation (the "text:v2" column in older matrices). Closer,
      but still mixed strength into the elimination step.

  v3  separates them: derive first (step 3), and let strength decide only
      among survivors (step 5). This is the final skill and the one every
      reported LiveMath text cell used.

** THE COLLISION. ** Before this consolidation the name `compare_claims.md`
meant v1 -- the draft that HURT. It now means v3. Result files written before
2026-10-05 that record `"skill": "compare_claims.md"` are v1 runs and must not
be merged with new ones. The kit ships an empty results/ so this cannot arise
here; it matters only if you copy old result files in. Results naming
`compare_claims_v3.md` are the same text as today's `compare_claims.md`, and
src/matrix.py maps both to the plain "text" column.

## strength_audit.md -- REPLACED compare_claims.md ON 2026-10-05

"Find the Sharpest Statement the Hypotheses Actually Give". Now the canonical
LiveMath skill (`SKILL_LIVEMATH` default). compare_claims v3 is archived as
`skills/archive/compare_claims_v3_SUPERSEDED.md`.

**Why it was written -- an error analysis, not tuning on the score.** The raw
release labels options by role (A = correct), so undoing the per-question
shuffle in `data/prepare_livemath.py` shows which kind of option the model
picks. In **263 of 608** questions one option reads "One of the remaining
options is correct, but a stronger result can be proven", and when present it
is **always** the correct answer. The no-skill 8B picks it 7/263 times; its
replies dismiss it as a "placeholder". On the other 345 questions the baseline
is ~44% and its errors are spread evenly over the four distractor roles, so
there is no single trap to target there.

strength_audit keeps compare_claims' derivability check (steps 2-3), then adds
an explicit "try to strengthen the winner" step (step 4) and tells the model
that meta-options are genuine claims (step 5). It never says which option is
right. Chosen over a shorter variant on questions 0-99 only (pilot: 34.0 vs
30.0, baseline 25.0); questions 100-607 are held out from that choice.

**Measured** (Blackwell box, transformers 5.17, greedy, 2 shards, BS=8,
MAXNEW=2048, n=608, parse 1.000 everywhere). McNemar exact, paired.

| model | baseline | placebo | compare_claims v3 | strength_audit | p vs base | p vs placebo |
|---|---|---|---|---|---|---|
| Qwen3-8B  | 26.15 | 25.66 | 26.97 | **29.44** | 0.13 | 0.08 |
| Qwen3-14B | 25.33 | 28.00 | (27.6, cluster) | **32.73** | 7e-4 | 0.035 |

Split by question type -- **report it this way; the total hides two opposite
effects**:

| | 263 with the meta-option | other 345 |
|---|---|---|
| 8B baseline -> strength_audit  | 2.7 -> 16.0 (39 gained / 4 lost, p=3e-8)  | 44.1 -> 39.7 (51/66, p=0.20) |
| 14B baseline -> strength_audit | 1.5 -> 27.4 (69 / 1, p=1e-19)             | 43.5 -> 36.8 (39/62, p=0.03) |
| 8B placebo / 14B placebo       | 1.1 / 4.6                                 | 44.3 / 45.8 |

Held-out (questions 100-607): 8B 26.4 -> 29.7, 14B 26.2 -> 32.9.

**Read this before citing the gain.** All of it comes from the 263
meta-option questions; on the other 345 the skill *hurts*, significantly on
14B (step 4 pushes the model toward stronger-sounding false candidates). Since
the meta-option is always correct when present, part of the gain is
test-taking on LiveMath's answer format, not better mathematics: "always pick
the meta-option when present" would score ~68% with the baseline's other-345
accuracy. The placebo nulls (8B -0.5, 14B +2.7, both n.s.) rule out "any
system prompt does this".
